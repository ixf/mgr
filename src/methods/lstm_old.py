# a copy before refactoring
import numpy as np
import json
import pickle
from collections import defaultdict
from tensorflow.keras import Model
from tensorflow.keras.layers import Input, LSTM, Dense
from tensorflow.keras.models import load_model
from keras.utils import to_categorical


EPOCH_COUNT = 10
WINDOW_SIZES = (16, 3)
LOOKAHEAD = 1
TRAIN_TEST_SPLIT = 0.8

KB = 1024
MB = KB*KB
LONG_JUMP_THRESHOLD = 256 * KB
SEQ_LENGTH = 15



class Lstm1:
    def __init__(self):
        self.d = {}
        self.model = None
        self.invd = {}
        self.last_reads = np.array([])
        self.last_prediction = 0


    def push(self, read):
        pass


    def predict_nu(self):
        pass


    def valdecode(self, v):
        if type(v) is int or type(v) is float:
            return v
        return v.decode('utf')


    def decode(self, m):
        return {k.decode('utf'): self.valdecode(v) for k, v in m.items()}


    def pretrain(self, train_file):
        train_file = self.valdecode(train_file)

        params = {
            'activation': 'softmax',
            'batch_size': 100,
            'epochs': 10,
            'lr': 0.01,
            'momentum': 0.95,
            'hidden_neurons': 400,
            'loss': 'categorical_crossentropy'
        }

        self.model = load_model(train_file.rstrip(".json") + '.h5')
        with open(train_file + '.pickle', 'rb') as f:
            self.d = pickle.load(f)
            self.invd = {v: k for k, v in self.d.items()}


    def OLD_prepare_data(self, source):
        # Input loading and preprocessing:
        # - load data and get the read locations
        # - convert into samples by sliding a window
        # - prepare decoder input
        # - split into input and output
        #2 this will all be removed soon
        #2 replaced with processing in stats/post

        with open(source) as f:
            data = json.loads(f.read())

        filereads = defaultdict(list)

        for op in data["operations"]:
            if op["type"] != "read":
                continue

            path, loc, size = op["path"], op["offset"], op["size"]
            filereads[path].append((loc, size))

        some_file = list(filereads.keys())[0]
        x = np.array(filereads[some_file])
        ins, outs = [], []

        # Split reads into samples:
        for i in range(len(x) - WINDOW_SIZES[0] - WINDOW_SIZES[1] + 1):
            # NOTE: just offset, not size
            ins.append(x[i:(i+WINDOW_SIZES[0]), :1].tolist())
            outs.append(
                x[(i+WINDOW_SIZES[0]):(i+WINDOW_SIZES[0]+WINDOW_SIZES[1]), :1].tolist())

        # shuffle
        io = [np.array(ins), np.array(outs)]
        io = np.concatenate(io, axis=1)
        # shuffles along the first axis
        np.random.shuffle(io)
        # recover
        ins = io[:, :WINDOW_SIZES[0], 0]
        outs = io[:, WINDOW_SIZES[0]:, 0]

        # convert ins to ins and outs to jumps
        def make_rel(w):
            rels = w[:, 1:] - w[:, :-1]
            return rels

        ins = make_rel(ins)
        outs = make_rel(outs)

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
        d = ic
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

        # Train/test split
        j = int(len(ins)*TRAIN_TEST_SPLIT)
        X_train = {'enc': in_enc[:j], 'dec': in_dec[:j]}
        Y_train = out_dec[:j]
        X_test = {'enc': in_enc[j:], 'dec': in_dec[j:]}
        Y_test = out_dec[j:]

        return (X_train, Y_train, X_test, Y_test)



    def predict(self, op):
        global model, last_reads, last_prediction
        # - collect last SEQ_LENGTH operations
        # - make rel
        # - convert using `d` dict
        # - predict

        op = self.decode(op)
        optype = op['type']
        if optype != 'read':
            return None

        path = op['path']
        offset = op['offset']
        size = op['size']

        last_reads = np.insert(self.last_reads, self.last_reads.size, offset)
        if last_reads.size > SEQ_LENGTH:
            last_reads = np.delete(last_reads, 0)
        elif last_reads.size < SEQ_LENGTH:
            return None

        def make_rel(w):
            rels = w[1:] - w[:-1]
            return rels

        rel = make_rel(last_reads)
        seq = np.zeros(rel.shape)

        for v, i in self.d.items():
            seq[rel == v] = i

        seq = to_categorical(seq, num_classes=len(self.d))
        # leftovers:
        seq = seq.reshape((1, seq.shape[0], seq.shape[-1]))

        q = self.model.predict({'enc': seq, 'dec': seq[:, -1:, :]})
        # prediction returns array of probabilities
        # convert to integer from `d` keys:
        q = int(np.argmax(q[0, :, :], axis=-1)[0])

        # convert to predicted offset
        relative_prediction = self.invd[q]
        absolute_prediction = offset + relative_prediction
        return (path, int(absolute_prediction), 64*KB)


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

        model = Model({'enc': enc_input, 'dec': dec_input}, decoder_outputs)

        model.compile(optimizer='rmsprop', loss=params['loss'], metrics=['accuracy'])
        return model


    def seq2seq_model(self, X_train, Y_train, X_test, Y_test, params, verbose=0):

        model = self.create_model(X_train, Y_train, params)

        if verbose != 0:
            model.summary()

        out = model.fit(X_train, Y_train,
                        validation_data=(X_test, Y_test),
                        epochs=params['epochs'],
                        verbose=verbose,
                        batch_size=params['batch_size'])
        return out, model


    def fake_op(self, offset):
        kv = {"type": "read", "offset": int(offset), "path": "q", "size": 4096}

        def enc(i):
            if type(i) is int:
                return i
            return i.encode('utf')
        return {k.encode('utf'): enc(v) for k, v in kv.items()}
