"""
This Python script is not used by the web app. It was created first as a
prototype and performs some of the same basic functions.
"""

import json
import numpy as np


with open('../data.json') as f:
    data = json.load(f)
    data = {d['id']:d for d in data}

def str2sec(string):
    if len(string.split(':')) == 3:
        hours, mins, secs = map(int, string.split(':'))
    elif len(string.split(':')) == 2:
        mins, secs = map(int, string.split(':'))
        hours = 0
    else:
        raise ValueError('string must have the form [hh:]mm:ss : ' + str(string))
    seconds = 3600*hours + 60*mins + secs
    return seconds

def sec2str(seconds, format=None):
    if seconds < 0:
        raise ValueError('seconds must be nonnegative: ' + str(seconds))
    mins, secs = divmod(seconds, 60)
    hours, mins = divmod(mins, 60)
    if format == 'youtube':
        string = '%dh%02dm%02ds' % (hours, mins, secs)
    else:
        string = '%d:%02d:%02d' % (hours, mins, secs)
    return string

def convert_time(time, episode, source, dest):

    timestamps = {k:d for k,d in zip(data[episode]['timestamps_columns'], np.array(data[episode]['timestamps']).T)}

    seconds = np.interp(str2sec(time), list(map(str2sec, timestamps[source])), list(map(str2sec, timestamps[dest])))

    if dest == 'youtube':
        youtube_id = data[episode]['youtube_id']
        youtube_playlist = data[episode].get('youtube_playlist', None)
        time_string = sec2str(seconds, format='youtube')
        if youtube_playlist is not None:
            return f"https://www.youtube.com/watch?v={youtube_id}&list={youtube_playlist}&t={time_string}"
        else:
            return f"https://www.youtube.com/watch?v={youtube_id}&t={time_string}"
    else:
        time_string = sec2str(seconds)
        return time_string

def podcast2youtube(time, episode='C2E22'):
    print(data[episode]['title'])
    print(convert_time(time, episode, source='podcast', dest='youtube'))

def youtube2podcast(time, episode='C2E22'):
    print(data[episode]['title'])
    print(convert_time(time, episode, source='youtube', dest='podcast'))
