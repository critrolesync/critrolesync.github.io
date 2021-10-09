"""
This module implements a subclass of numpy.ndarray for working with time
strings.
"""

import numpy as np

class Time(np.ndarray):
    def __new__(cls, data):
        data = np.asarray(data)
        if data.dtype.type is np.str_:
            data = cls.str2sec(data)
        obj = data.view(cls)
        return obj

    def __str__(self):
        return str(self.text)

    def __repr__(self):
        return f'{self.__class__.__name__}({self.text})'

    def __getitem__(self, *args):
        return self.__class__(super().__getitem__(*args))

    @property
    def text(self):
        return self.sec2str(self).tolist()

    @property
    def secs(self):
        return self.tolist()

    @staticmethod
    @np.vectorize
    def str2sec(string):
        original_string = string
        try:
            if string[0] == '-':
                sign = -1
                string = string[1:]
            else:
                sign = 1
            numbers = np.asarray(string.split(':')[::-1], dtype='float')
            seconds = sign * np.dot(numbers, [1, 60, 3600][:len(numbers)])
            return seconds
        except:
            raise ValueError(f'failed to convert time string "{original_string}" to number of seconds')

    @staticmethod
    @np.vectorize
    def sec2str(seconds):
        original_seconds = seconds
        try:
            seconds = round(seconds)
            sign = '-' if seconds < 0 else ''
            seconds = abs(seconds)
            mins, secs = divmod(seconds, 60)
            hours, mins = divmod(mins, 60)
            string = f'{sign}{int(round(hours)):d}:{int(round(mins)):02d}:{int(round(secs)):02d}'
            return string
        except:
            raise ValueError(f'failed to convert number of seconds "{original_seconds}" to a string')


def str2sec(string):
    return Time.str2sec(string).tolist()

def sec2str(seconds):
    return Time.sec2str(seconds).tolist()
