"""
This Python script is not used by the web app. It was created first as a
prototype and performs some of the same basic functions.
"""

import json
import numpy as np


with open('../docs/data.json') as f:
    data = json.load(f)

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
    c, e = map(int, episode_id.strip('C').split('E'))
    ep = data[c-1]['episodes'][e-1]
    if ep['id'] != episode_id:
        raise ValueError(f'episode id mismatch for {episode_id}: {ep}')
    else:
        return ep

def convert_time(time, episode_id, source, dest):

    ep = get_episode_data_from_id(episode_id)
    timestamps = {k:d for k,d in zip(ep['timestamps_columns'], np.array(ep['timestamps']).T)}

    seconds = np.interp(str2sec(time), list(map(str2sec, timestamps[source])), list(map(str2sec, timestamps[dest])))

    if dest == 'youtube':
        youtube_id = ep['youtube_id']
        youtube_playlist = ep.get('youtube_playlist', None)
        time_string = sec2str(seconds, format='youtube')
        if youtube_playlist is not None:
            return f'https://www.youtube.com/watch?v={youtube_id}&list={youtube_playlist}&t={time_string}'
        else:
            return f'https://www.youtube.com/watch?v={youtube_id}&t={time_string}'
    else:
        time_string = sec2str(seconds)
        return time_string

def podcast2youtube(time, episode_id='C2E22'):
    ep = get_episode_data_from_id(episode_id)
    print(ep['title'])
    print(convert_time(time, episode_id, source='podcast', dest='youtube'))

def youtube2podcast(time, episode_id='C2E22'):
    ep = get_episode_data_from_id(episode_id)
    print(ep['title'])
    print(convert_time(time, episode_id, source='youtube', dest='podcast'))



def fixAnchorMidroll(newAdDuration=61, oldAdDuration=0):
    '''For fixing issue #8: https://github.com/critrolesync/critrolesync.github.io/issues/8'''

    anchor_podcast_episodes = data[1]['episodes'][19:]
    for ep in anchor_podcast_episodes:
        if 'timestampsBitrate' in ep:
            # need to adjust for new bitrate
            bitrateRatio = 128/127.7
        else:
            # do need to adjust for bitrate
            bitrateRatio = 1

        print(ep['id'])
        print()
        print('                "timestamps": [')

        for i, (youtube, podcast, comment) in enumerate(ep['timestamps']):
            if i<2: # before break
                podcast_new = sec2str(str2sec(podcast)*bitrateRatio)
            else: # after break
                podcast_new = sec2str((str2sec(podcast)-oldAdDuration+newAdDuration)*bitrateRatio)
            if i<len(ep['timestamps'])-1: # include final comma
                print(f'                    ["{youtube}", "{podcast_new}", "{comment}"],')
            else: # no final comma
                print(f'                    ["{youtube}", "{podcast_new}", "{comment}"]')

        print('                ]')
        print()
        print()
