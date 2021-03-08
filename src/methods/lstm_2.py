import os
import datetime

from tensorflow.python.keras.layers.core import Dense, Dropout
from src.env import Env
from src.fs.operation import Read
from src.methods.base import LearningBase
from src.methods.utils import vocab, to_boc

import numpy as np
from pandas.core.frame import DataFrame
from pandas.util import hash_pandas_object

import tensorflow as tf
from tensorflow.keras.layers import Input, Lambda, LSTM, Dense, Concatenate, Embedding, Dropout
from tensorflow.keras import Model
from tensorflow.keras.models import load_model
from tensorflow.keras.optimizers import Adam
from tensorflow.keras.utils import plot_model, to_categorical

logname = "lstm2" + datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
logdir = os.path.join("tb_logs", logname)

callbacks = [
    tf.keras.callbacks.TensorBoard(logdir, histogram_freq=1),
    tf.keras.callbacks.EarlyStopping(
        monitor='val_loss',
        patience=20,
        min_delta=1e-3,
    )
]

sequence_length = 16
sequence_step = 3
learning_rate = 0.001
learning_decay = 2
drop_ratio = 0.25
batch_size = 512
epochs = 200


def build_model(in_files: int, out_files: int, out_offsets: int) -> Model:
    # file_boc_input = Input(shape=(sequence_length,), name="file_boc")
    # file_boc_emb = Embedding(len(vocab), 50)(file_boc_input)

    file_input = Input(shape=(sequence_length,), name="file")
    file_emb = Embedding(in_files, 100, name="file_embedding")(file_input)

    # file_emb = Concatenate()([file_boc_emb, file_emb])

    file_lstm = LSTM(1024, name="file_lstm")(file_emb)

    offs_input = Input(shape=(sequence_length,), name="offset")
    offs_emb = Embedding(2048, 512, name="offset_embedding")(offs_input)
    offs_lstm = LSTM(1024, name="offset_lstm")(offs_emb)

    x = Concatenate()([offs_lstm, file_lstm])
    x = Dropout(drop_ratio)(x)
    x = Dense(8192, activation="sigmoid")(x)
    x = Dropout(drop_ratio)(x)

    file_output = Dense(out_files, name="out_file", activation="softmax")(x)
    offs_output = Dense(out_offsets, name="out_offset", activation="softmax")(x)

    return Model(
        # inputs=[file_boc_input, file_input, offs_input],
        inputs=[file_input, offs_input],
        outputs=[file_output, offs_output]
    )


def plot_nn(model: Model, to_file: str):
    plot_model(model, to_file=to_file, show_shapes=True, show_layer_names=True)


def df_hash(df: DataFrame):
    return hex(abs(hash_pandas_object(df).sum()))[2:]


class Lstm2(LearningBase):
    last_read: Read
    last_offsets: 'list[int]' = []
    bs: float = 16 * 1024
    last_fns: 'list[int]' = []
    i_train: int
    i_test: int

    def push(self, read: Read):
        self.last_read = read
        self.last_offsets.append(int(read.offset / self.bs))
        self.last_fns.append(self.file_idx_map[read.filename])
        if len(self.last_offsets) > 16:
            self.last_offsets.pop(0)
            self.last_fns.pop(0)

    def __init__(self):
        pass

    def try_restore(self, df: DataFrame, env: Env):
        target = df_hash(df) + ".h5"
        cached = os.listdir('./model_cache')
        if target in cached:
            loaded = load_model(f"./model_cache/{target}")
            if isinstance(loaded, Model):
                self.model = loaded
                self._setup(df, env)
                return True
        return False

    def persist_by_hash(self, df: DataFrame):
        target = "./model_cache/" + df_hash(df) + ".h5"
        self.model.save(target)

    def train(self, df: DataFrame, env: Env, worker_name: str = '', split: float = 0.2):
        print(df)
        files_count = len(set(df.filename))
        offsets_count = int(max(df.offset) / env.block_size) + 1
        self.files_count = files_count
        self.offsets_count = offsets_count

        self.model: Model = build_model(files_count, files_count, offsets_count)
        if self.try_restore(df, env):
            return

        self.model.compile(
            loss="binary_crossentropy",
            optimizer=Adam(
                learning_rate=learning_rate,
            ),
            metrics=['accuracy'],
        )
        self.model.summary()

        # self.i_train, self.i_test = self.split(len(df), split)

        (  # boc,
            file,
            offsets,
            out_file,
            out_offset
        ) = self.transform_data(df, env)

        model_x = [
            # "file_boc": boc,
            file,
            offsets,
        ]
        model_y = [
            out_file,
            out_offset,
        ]

        self.model.fit(
            model_x,
            model_y,
            epochs=epochs,
            validation_split=split,
            batch_size=batch_size,
            callbacks=callbacks,
        )

        self.persist_by_hash(df)

    def _setup(self, df: DataFrame, env: Env):
        self.bs = env.block_size
        filenames = list(set(df.filename))
        self.file_idx_map = {
            filename: idx for idx, filename in enumerate(set(filenames))
        }
        self.idx_file_map = {
            v: k for k, v in self.file_idx_map.items()
        }

    def transform_data(self, df: DataFrame, env: Env):
        bs = env.block_size
        self._setup(df, env)

        file_sequences = []
        offs_sequences = []
        file_expected = []
        offs_expected = []
        for i in range(0, len(df) - sequence_length, sequence_step):
            file_sequences.append(df.filename[i: i + sequence_length].to_numpy())
            offs_sequences.append(df.offset[i: i + sequence_length].to_numpy())

            file_expected.append(df.filename[i + sequence_length])
            offs_expected.append(df.offset[i + sequence_length])

        file_sequences = np.array(file_sequences)
        offs_sequences = np.array(offs_sequences)
        file_expected = np.array(file_expected)
        offs_expected = np.array(offs_expected)

        def fns_to_ints(files):
            q = lambda fn: self.file_idx_map[fn]
            return np.array(list(map(q, files)))

        def arr_fns_to_ints(arr: np.ndarray):
            for i, x in enumerate(arr):
                arr[i] = fns_to_ints(x)
            return arr

        # boc = np.asarray(to_boc(file_sequences)).astype('float32')
        file = np.asarray(arr_fns_to_ints(file_sequences)).astype('float32')
        off = np.asarray(offs_sequences).astype('float32')

        out_f = np.asarray(
            to_categorical(fns_to_ints(file_expected))
        ).astype('float32')
        out_o = np.asarray(
            to_categorical(offs_expected / bs, num_classes=self.offsets_count)
        ).astype('float32')

        print(out_o.shape)

        # return boc, file, off, out_f, out_o
        return file, off, out_f, out_o

    def _predict(self) -> 'Read | None':
        if len(self.last_offsets) < 16:
             return None

        got = self.model([
            np.array([self.last_fns]),
            np.array([self.last_offsets]),
        ], training=False)

        idx = np.argmax(got[0], axis=None, out=None)
        file = self.idx_file_map[idx]
        offset = np.argmax(got[1], axis=None, out=None)

        return self.last_read.replace(
            filename=file,
            offset=offset * self.bs,
            length=self.bs,
        )

    def memory(self) -> float:
        # TODO
        return 0.0
