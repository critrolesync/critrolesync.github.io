import numpy as np

from . import data


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

def get_episode_data_from_id(episode_id):
    c, e = episode_id.strip('C').split('E')
    try:
        return next(filter(lambda ep: ep['id'] == episode_id, data[int(c)-1]['episodes']))
    except StopIteration:
        raise ValueError(f'episode with id "{episode_id}" not found')

def convert_time(time, episode_id, source, dest):

    ep = get_episode_data_from_id(episode_id)
    timestamps = {k:d for k,d in zip(ep['timestamps_columns'], np.array(ep['timestamps']).T)}

    seconds = np.interp(str2sec(time), list(map(str2sec, timestamps[source])), list(map(str2sec, timestamps[dest])))

    if dest == 'youtube':
        time_string = sec2str(seconds)
        return time_string
    else:
        time_string = sec2str(seconds)
        return time_string

def podcast2youtube(time, episode_id):
    return convert_time(time, episode_id, source='podcast', dest='youtube')

def youtube2podcast(time, episode_id):
    return convert_time(time, episode_id, source='youtube', dest='podcast')

def youtube_url(episode_id, seconds=None):
    ep = get_episode_data_from_id(episode_id)
    if seconds:
        time_string = sec2str(seconds, format='youtube')
    else:
        time_string = None
    youtube_id = ep['youtube_id']
    youtube_playlist = ep.get('youtube_playlist', None)
    url = f'https://www.youtube.com/watch?v={youtube_id}'
    if youtube_playlist is not None:
        url += f'&list={youtube_playlist}'
    if time_string is not None:
        url += f'&t={time_string}'
    return url
