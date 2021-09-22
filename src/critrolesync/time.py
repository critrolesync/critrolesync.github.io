"""

"""


def str2sec(string):
    if string[0] == '-':
        sign = -1
        string = string[1:]
    else:
        sign = 1
    if len(string.split(':')) == 3:
        hours, mins, secs = map(int, string.split(':'))
    elif len(string.split(':')) == 2:
        mins, secs = map(int, string.split(':'))
        hours = 0
    else:
        raise ValueError('string must have the form [hh:]mm:ss : ' + str(string))
    seconds = sign * (3600*hours + 60*mins + secs)
    return seconds

def sec2str(seconds, format=None):
    seconds = round(seconds)
    sign = '-' if seconds < 0 else ''
    seconds = abs(seconds)
    mins, secs = divmod(seconds, 60)
    hours, mins = divmod(mins, 60)
    if format == 'youtube':
        string = '%s%dh%02dm%02ds' % (sign, hours, mins, secs)
    else:
        string = '%s%d:%02d:%02d' % (sign, hours, mins, secs)
    return string
