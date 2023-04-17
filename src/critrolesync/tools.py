from pathlib import Path
import json
import numpy as np
import ffmpeg

from . import data
from .jsonencoder import CompactJSONEncoder
from .time import Time


latest_parsed_podcast_feed = []
# for feed_dir in ['geekandsundry', 'critical-role']:
for feed_dir in ['nerdist', 'critical-role']:
    _latest_parsed_feed = list(Path(__file__).parent.joinpath(f'../../feed-archive/{feed_dir}/parsed').glob('*.json'))[-1]
    with _latest_parsed_feed.open() as _fd:
        latest_parsed_podcast_feed += reversed(json.load(_fd))

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

def get_podcast_feed_from_id(episode_id):
    try:
        # we try it this way first because there is at least one example (C1E78)
        # where the title is spelled differently in the feed
        c, e = episode_id.strip('C').split('E')
        if c == '1':
            episode_title = f'Vox Machina Ep. {e} '  # include trailing space to distinguish 1, 10, 100, etc.
        elif c in ['2', '3']:
            episode_title = f'{episode_id} '         # include trailing space to distinguish 1, 10, 100, etc.
        else:
            raise NotImplementedError
    except:
        # we fall back on the title stored in data.json if the episode is not
        # part of the main campaigns
        episode_title = get_episode_data_from_id(episode_id)['title']

    # use title substring to locate the podcast feed entry
    ep = None
    for episode in latest_parsed_podcast_feed:
        if episode_title.lower() in episode['Title'].lower():
            if ep is None:
                ep = episode
            else:
                print(f'WARNING: podcast episode title substring "{episode_title}" ({episode_id}) is not unique, using first instance')
    if ep:
        return ep
    else:
        raise ValueError(f'podcast episode with title containing "{episode_title}" ({episode_id}) not found')

def convert_time(time, episode_id, source, dest):
    ep = get_episode_data_from_id(episode_id)
    timestamps = {k:d for k,d in zip(ep['timestamps_columns'], np.array(ep['timestamps']).T)}
    seconds = np.interp(Time(time), Time(timestamps[source]), Time(timestamps[dest]))
    return Time(seconds).text

def podcast2youtube(time, episode_id):
    return convert_time(time, episode_id, source='podcast', dest='youtube')

def youtube2podcast(time, episode_id):
    return convert_time(time, episode_id, source='youtube', dest='podcast')

def youtube_url(episode_id, seconds=None):
    ep = get_episode_data_from_id(episode_id)
    if seconds:
        time_string = Time(seconds).text
        time_string = time_string.replace(':', 'h', 1).replace(':', 'm', 1) + 's'
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

def slice_audio_file(input_file, output_file, start=None, end=None, mono=False, rate=44100):
    input_kwargs = {}
    output_kwargs = {}

    if start: input_kwargs['ss'] = start
    if end: input_kwargs['to'] = end

    if mono:
        # one audio channel
        output_kwargs['ac'] = 1
    else:
        # skip re-encoding, very fast but incompatible with mono
        output_kwargs['c'] = 'copy'

    if rate:
        # explicitly set the sampling rate
        output_kwargs['ar'] = rate

    # create the containing directory if necessary
    Path(output_file).parent.mkdir(parents=True, exist_ok=True)

    try:
        (ffmpeg
        .input(str(input_file), **input_kwargs)
        .output(str(output_file), **output_kwargs)
        .overwrite_output()
        .run(quiet=True))

    except:
        # the new file is likely incomplete, so delete it
        Path(output_file).unlink(missing_ok=True)

        # raise the exception so that it can be handled elsewhere
        raise
