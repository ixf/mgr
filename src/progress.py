class Progress:
    # class for reporting on estimated remaining time,
    # some metrics of running applications

    def __init__(self, max_iter):
        self.max_iter = max_iter
        self.max_steps = 25
        self.step = 0

    def next_step(self):
        return self.step / self.max_steps

    def test(self, index):
        now = index / self.max_iter
        if now > self.next_step():
            self.step += 1
            return True
        return False

    def print(self, s):
        print("\r", s, end='')

    def end(self):
        print("")

