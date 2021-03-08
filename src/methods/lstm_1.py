def create_model(with_files):
    if files:
        file_input = keras.Input(shape=(seq_length,), name="file")
        file_emb = Embedding(50, 4)(file_input)
        file_ft = LSTM(64)(file_emb)

    offs_input = keras.Input(shape=(seq_length,), name="offset")
    offs_emb = Embedding(1024, 16)(offs_input)
    offs_ft = LSTM(64)(offs_emb)

    if files:
        concat = Concatenate()([offs_ft, file_ft])
        x = concat
    else:
        x = offs_ft

    x = Dropout(0.2)(x)

    x = Dense(2048, activation="relu")(x)
    x = Dense(1024, activation="relu")(x)

    if files:
        file_output = Dense(50, name="out_file", activation="softmax")(x)
    offs_output = Dense(970, name="out_offset", activation="softmax")(x)

    if files:
        return keras.Model(inputs=[file_input, offs_input], outputs=[concat, file_output, offs_output])
    return keras.Model(inputs=[offs_input], outputs=[offs_ft, offs_output])


class Lstm1:
    def __init__(self, with_files=False, name="", tb=False):
        self.model = create_model(with_files)
        self.model.compile(
                loss='categorical_crossentropy',
                optimizer='adam',
                metrics=[tf.keras.metrics.CategoricalAccuracy()]
            )
        #self.model.summary()

        self.callbacks = []

        if tb:
            logdir = os.path.join("logs", name + datetime.datetime.now().strftime("%Y%m%d-%H%M%S"))
            tensorboard_callback = tf.keras.callbacks.TensorBoard(logdir, histogram_freq=1)
            self.callbacks.append
history = model.fit(
    # {"file": x_f, "offset": x_o},
    # {"out_file": y_f, "out_offset": y_o},
    {"offset": x_o},
    {"out_offset": y_o},
    epochs=100,
    batch_size=512,
    validation_split=0.1,
    verbose=0,
    callbacks=[tensorboard_callback],
)
o = model.predict({"offset": x_o})[-1]
sum(np.argmax(o, axis=1) == np.argmax(y_o, axis=1)) / y_o.shape[0]

