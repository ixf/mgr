import numpy as np
import pandas
import pickle
from collections import defaultdict
from tensorflow.keras import Model
from tensorflow.keras.layers import Input, LSTM, Dense
from tensorflow.keras.models import load_model
from tensorflow.keras.utils import to_categorical
import tensorflow as tf
import datetime
from ..fs.operation import Read


EPOCH_COUNT = 10
WINDOW_SIZES = (16, 3)
LOOKAHEAD = 1
TRAIN_TEST_SPLIT = 0.8

KB = 1024
MB = KB*KB
LONG_JUMP_THRESHOLD = 256 * KB
SEQ_LENGTH = 15


default_params = {
    'activation': 'relu',
    'batch_size': 100,
    'epochs': 10,
    'lr': 0.02,
    'momentum': 0.95,
    'hidden_neurons': 200,
    'loss': 'mean_squared_logarithmic_error',
}

log_dir = "tb_logs/" + datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
tensorboard_callback = tf.keras.callbacks.TensorBoard(log_dir=log_dir, histogram_freq=1)

class Lstm1:
    def __init__(self):
        self.d = {}
        self.model = None
        self.invd = {}
        self.last_reads = []


    def soft_reset(self):
        self.last_reads = []


    def push(self, read):
        self.last_reads.append(read)
        if len(self.last_reads) > SEQ_LENGTH:
            self.last_reads.pop(0)


    def predict(self):
        if len(self.last_reads) < SEQ_LENGTH:
            return
        op = self.last_reads[-1]

        rel = [o.offset for o in self.last_reads]
        rel = np.array(rel)
        rel = rel[1:] - rel[:-1]
        seq = np.zeros(rel.shape)

        for v, i in self.d.items():
            seq[rel == v * KB] = i

        seq = to_categorical(seq, num_classes=len(self.d))
        # leftovers:
        seq = seq.reshape((1, seq.shape[0], seq.shape[-1]))

        q = self.model.predict({'enc': seq, 'dec': seq[:, -1:, :]})
        # prediction returns array of probabilities
        # convert to integer from `d` keys:
        q = int(np.argmax(q[0, :, :], axis=-1)[0])

        # convert to predicted offset
        relative_prediction = self.invd[q] * KB
        absolute_prediction = op.offset + relative_prediction
        # print("last read:", op.offset, "prediction:", int(absolute_prediction))
        return Read(op.filename, int(absolute_prediction), op.length) 


    def valdecode(self, v):
        if type(v) is int or type(v) is float:
            return v
        return v.decode('utf')


    def decode(self, m):
        return {k.decode('utf'): self.valdecode(v) for k, v in m.items()}


    def transform_data(self, pd: pandas.DataFrame):
        # Input loading and preprocessing:
        # - load data and get the read locations
        # - convert into samples by sliding a window
        # - prepare decoder input
        # - split into input and output
        #2 this will all be removed soon
        #2 replaced with processing in stats/post

        ins, outs = [], []

        # Split reads into samples:
        for i in range(len(pd) - WINDOW_SIZES[0] - WINDOW_SIZES[1] + 1):
            pivot = i + WINDOW_SIZES[0]
            ins.append(pd[i:pivot].offset.tolist())
            outs.append(pd[pivot:(pivot + WINDOW_SIZES[1])].offset.tolist())

        # io is a list of offset sequences
        # shuffle
        # first - concatenate to preserve the shuffle ins-outs pairs
        io = [np.array(ins), np.array(outs)]
        io = np.concatenate(io, axis=1)
        # shuffles along the first axis (random order of real sequences)
        np.random.shuffle(io)
        def make_rel(w):
            rels = w[:, 1:] - w[:, :-1]
            return rels
        io = make_rel(io)
        # recover
        ins = io[:, :WINDOW_SIZES[0]]
        outs = io[:, WINDOW_SIZES[0]:]

        # ins = make_rel(ins)
        # outs = make_rel(outs)

        # remove uncommon jumps
        from collections import Counter
        ic = Counter(ins.reshape((-1)))
        ic = ic.most_common(96)
        ins2 = np.zeros(ins.shape)
        ins2[:, :] = 0.2
        outs2 = np.zeros(outs.shape)
        outs2[:, :] = 0.2

        # restore common jumps to ins2 and outs2:
        ic = [v for v, _ in ic]
        ic = {v: i for i, v in enumerate(ic)}
        self.d = ic
        for v, i in ic.items():
            ins2[ins == v] = i
            outs2[outs == v] = i
        ins = ins2
        outs = outs2

        # prepare decoder target
        out_dec = np.roll(outs, -LOOKAHEAD, axis=1)
        out_dec = out_dec[:, :-1]  # = WINDOW_SIZES[0]+1
        in_dec = outs[:, :-1]

        in_enc = to_categorical(ins)
        in_dec = to_categorical(in_dec)
        out_dec = to_categorical(out_dec)

        tkns = in_enc.shape[-1]
        in_dec = in_dec.reshape((in_dec.shape[0], 1, in_dec.shape[-1]))
        out_dec = out_dec.reshape((out_dec.shape[0], 1, out_dec.shape[-1]))

        self.invd = {v: k for k, v in self.d.items()}

        X = { 'enc': in_enc, 'dec': in_dec }
        Y = out_dec
        return (X, Y)


    def create_model(self, X_train, Y_train, params):
        token_count = X_train['enc'].shape[-1]
        latent_dim = params['hidden_neurons']

        enc_input = Input(shape=(None, token_count), name='enc')
        _, state_h, state_c = LSTM(latent_dim, return_state=True)(enc_input)
        encoder_states = [state_h, state_c]

        dec_input = Input(shape=(None, token_count), name='dec')
        decoder_outputs, _, _ = LSTM(latent_dim, return_sequences=True, return_state=True)(dec_input,
                                                                                           initial_state=encoder_states)

        decoder_dense = Dense(token_count, activation='softmax')
        decoder_outputs = decoder_dense(decoder_outputs)

        self.model = Model({'enc': enc_input, 'dec': dec_input}, decoder_outputs)
        self.model.compile(optimizer='rmsprop', loss=params['loss'], metrics=['accuracy'])


    def run(self, X_train, Y_train, X_test, Y_test, params={}, verbose=1):
        params = {**default_params, **params}
        self.create_model(X_train, Y_train, params)

        if verbose:
            self.model.summary()

        out = self.model.fit(X_train, Y_train,
                        validation_data=(X_test, Y_test),
                        epochs=params['epochs'],
                        verbose=verbose,
                        callbacks=[tensorboard_callback],
                        batch_size=params['batch_size'])
        return out
