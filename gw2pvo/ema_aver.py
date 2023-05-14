class MovingAverage:
    '''calculate exponential moving average. Add method to calculate using a specified alpha value.
    Alpha = 0.67 is best suited'''

    def __init__(self, alpha):
        self.alpha = alpha
        self.previous_average = None

    def add(self, x):
        if self.previous_average is None:
            self.previous_average = x
        else:
            self.previous_average = self.alpha * x + \
                (1 - self.alpha) * self.previous_average

        return self.previous_average
