from pathlib import Path
import json
import numpy as np

from . import data
from .jsonencoder import CompactJSONEncoder
from .time import sec2str, str2sec


def write_data(new_data):
    with Path(__file__).parent.joinpath('../../docs/data.json').open('w') as _fd:
        json.dump(new_data, _fd, indent=4, cls=CompactJSONEncoder)
        _fd.write('\n')

def get_episode_data_from_id(episode_id):
    ep = None
    for series in data:
        for episode in series['episodes']:
            if episode['id'] == episode_id:
                if ep is None:
                    ep = episode
                else:
                    raise ValueError(f'episode id "{episode_id}" is not unique')
    if ep:
        return ep
    else:
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
