"""
Run the autosync algorithm:
  1. Download the original YouTube and podcast audio files, if necessary
  2. Slice audio files to isolate their beginnings and endings, if necessary
  3. Fingerprint the YouTube audio slices, if necessary
  4. Find timestamps by matching the podcast audio slices to fingerprints
  5. Write timestamps to data.json
"""

from pathlib import Path
import sys
import argparse
import re
from pathlib import Path
import json
import numpy as np
# from librosa import get_duration
import logging
from .. import data, write_data, get_episode_data_from_id, \
               get_podcast_feed_from_id, Time, download_youtube_audio, \
               download_podcast_audio, slice_audio_file
from . import Database, Matcher

logger = logging.getLogger(__name__)


youtube_slice_times = {
    # these times are relative to the first ("beginning")
    # or last ("ending") YouTube timestamp
    # >>> NOTE: if these change, fingerprints must be regenerated! <<<
    'beginning': ('0:00:00', '0:06:00'),
    'ending': ('-0:02:00', '-0:00:00'),
}

default_podcast_slice_times = {
    # these times are relative to the start ("beginning")
    # or end ("ending") of the podcast audio file
    'beginning': ('0:05:00', '0:05:10'),
    'ending': ('-0:02:00', '-0:01:50'),
}

with open(Path(__file__).parent / 'custom-podcast-slice-times.json') as _fd:
    custom_podcast_slice_times = json.load(_fd)

def get_absolute_slice_times(episode_id, podcast_file, bitrate_conversion_factor=None):
    d = get_episode_data_from_id(episode_id)
    ts = np.rec.fromrecords(list(map(tuple, d['timestamps'])), names=d['timestamps_columns'], formats=['U8', 'U8', 'U30'])

    # verify there are at least two events in the timestamps list
    if len(ts) == 0:
        raise ValueError(f'timestamps are empty for "{episode_id}"')
    if len(ts) == 1:
        raise ValueError(f'at least two timestamp events are needed, but "{episode_id}" has only one: {ts}')

    # verify that no YouTube timestamps are empty
    if np.any(ts.youtube == ''):
        raise ValueError(f'one or more YouTube timestamps is missing for "{episode_id}": {ts.youtube}')

    # if not podcast_file or not podcast_file.exists():
    #     raise ValueError(f'podcast file for "{episode_id}" is missing, cannot get its duration using librosa: {podcast_file}')
    # podcast_duration = get_duration(filename=podcast_file)
    if Time(get_podcast_feed_from_id(episode_id)["HH:MM:SS"]) != Time(get_podcast_feed_from_id(episode_id)["Seconds"]):
        raise ValueError(f'discrepancy in podcast durations from feed for "{episode_id}": {Time(get_podcast_feed_from_id(episode_id)["HH:MM:SS"]).text} (HH:MM:SS) vs {Time(get_podcast_feed_from_id(episode_id)["Seconds"]).text} (Seconds)')
    podcast_duration = Time(get_podcast_feed_from_id(episode_id)["HH:MM:SS"])
    # logger.debug(f'podcast duration for {episode_id} according to podcast feed:         {Time(get_podcast_feed_from_id(episode_id)["HH:MM:SS"]).text}')
    # logger.debug(f'podcast duration for {episode_id} according to librosa.get_duration: {Time(get_duration(filename=podcast_file)).text}')
    logger.info(f'podcast duration for {episode_id}: {Time(podcast_duration).text}')

    podcast_slice_times = default_podcast_slice_times.copy()
    podcast_slice_times.update(custom_podcast_slice_times.get(episode_id, {}))

    youtube_beginning_start = Time(ts.youtube[0])  + Time(youtube_slice_times['beginning'][0])
    youtube_ending_start    = Time(ts.youtube[-1]) + Time(youtube_slice_times['ending'][0])
    podcast_beginning_start = 0                    + Time(podcast_slice_times['beginning'][0])
    podcast_ending_start    = podcast_duration     + Time(podcast_slice_times['ending'][0])

    youtube_beginning_stop  = Time(ts.youtube[0])  + Time(youtube_slice_times['beginning'][1])
    youtube_ending_stop     = Time(ts.youtube[-1]) + Time(youtube_slice_times['ending'][1])
    podcast_beginning_stop  = 0                    + Time(podcast_slice_times['beginning'][1])
    podcast_ending_stop     = podcast_duration     + Time(podcast_slice_times['ending'][1])

    if bitrate_conversion_factor:
        podcast_beginning_start = podcast_beginning_start / bitrate_conversion_factor
        podcast_ending_start    = podcast_ending_start    / bitrate_conversion_factor
        podcast_beginning_stop  = podcast_beginning_stop  / bitrate_conversion_factor
        podcast_ending_stop     = podcast_ending_stop     / bitrate_conversion_factor

    return {
        'youtube': {
            'beginning': Time([youtube_beginning_start, youtube_beginning_stop]),
            'ending':    Time([youtube_ending_start,    youtube_ending_stop]),
        },
        'podcast': {
            'beginning': Time([podcast_beginning_start, podcast_beginning_stop]),
            'ending':    Time([podcast_ending_start,    podcast_ending_stop]),
        },
    }


def parse_args(argv):
    parser = argparse.ArgumentParser(prog='autosync')

    parser.add_argument('episode_ids', nargs='+',
                        help='the ids of episodes to sync, separated by spaces ' \
                             '(e.g., C1E1 C1E2) or given as a range (e.g., C2E1-141)')
    parser.add_argument('-v', '--verbose', action='count', default=0,
                        help='display detailed information during execution')
    parser.add_argument('-d', '--download', choices=['both', 'youtube', 'podcast'],
                        help='download audio (even if downloads already exist)')
    parser.add_argument('-s', '--slice', choices=['both', 'youtube', 'podcast'],
                        help='slice audio (even if slices already exist)')
    parser.add_argument('-f', '--fingerprint', action='store_true',
                        help='generate fingerprints (even if fingerprints already exist)')

    args = parser.parse_args(argv[1:])

    episode_ids = []
    for ep in args.episode_ids:
        if '-' in ep:
            try:
                first, last = ep.split('-')

                match = re.fullmatch('(.*\D+)(\d+)', first)
                assert match is not None, 'first part has wrong form'
                first_prefix, first_number = match.groups()

                match = re.fullmatch('(\d+)', last)
                if match is not None:
                    last_number, = match.groups()
                else:
                    match = re.fullmatch('(.*\D+)(\d+)', last)
                    assert match is not None, 'second part has wrong form'
                    last_prefix, last_number = match.groups()
                    assert first_prefix == last_prefix, 'prefixes do not match'

                first_number = int(first_number)
                last_number = int(last_number)
                assert first_number < last_number, 'not in ascending order'

                episode_ids += [f'{first_prefix}{i}' for i in range(first_number, last_number + 1)]

            except Exception as e:
                raise ValueError(f'could not parse episode ids "{ep}": {e}')

        else:
            episode_ids.append(ep)

    args.episode_ids = episode_ids

    return args


args = parse_args(sys.argv)

if args.verbose == 1:
    logging.basicConfig(level=logging.INFO)
elif args.verbose > 1:
    logging.basicConfig(level=logging.DEBUG)

logger.debug(args)

import yt_dlp
logger.debug(f'yt_dlp version {yt_dlp.version.__version__}')

episode_ids = args.episode_ids
overwrite_youtube_download = args.download in ['both', 'youtube']
overwrite_podcast_download = args.download in ['both', 'podcast']
overwrite_youtube_slices = args.slice in ['both', 'youtube']
overwrite_podcast_slices = args.slice in ['both', 'podcast']
overwrite_fingerprints = args.fingerprint

print(f'Preparing to autosync the following episodes: {episode_ids}')


data_dir = Path('/data')
data_dir.mkdir(parents=True, exist_ok=True)

with Database(database_name='dejavu_db', container_name='dejavu_db') as db:

    for episode_id in episode_ids:
        print(episode_id)

        youtube_file = [p for p in (data_dir / 'original').glob(f'{episode_id} YouTube.*') if not str(p).endswith('.part')]
        podcast_file = [p for p in (data_dir / 'original').glob(f'{episode_id.split(" ")[0]} Podcast.*') if not str(p).endswith('.part')]

        if len(youtube_file) == 0:
            youtube_file = None
        elif len(youtube_file) == 1:
            youtube_file = youtube_file[0]
        else:
            raise ValueError(f'multiple YouTube audio files with different file extensions found in downloads cache for "{episode_id}" when at most one was expected (try deleting and redownloading): {youtube_file}')

        if len(podcast_file) == 0:
            podcast_file = None
        elif len(podcast_file) == 1:
            podcast_file = podcast_file[0]
        else:
            raise ValueError(f'multiple podcast audio files with different file extensions found in downloads cache for "{episode_id}" when at most one was expected (extension may have changed in the podcast feed, try deleting and redownloading): {podcast_file}')

        youtube_beginning_file = data_dir / 'youtube-slices' / f'{episode_id} YouTube - Beginning.m4a'
        podcast_beginning_file = data_dir / 'podcast-slices' / f'{episode_id} Podcast - Beginning.m4a'

        youtube_ending_file = data_dir / 'youtube-slices' / f'{episode_id} YouTube - Ending.m4a'
        podcast_ending_file = data_dir / 'podcast-slices' / f'{episode_id} Podcast - Ending.m4a'

        fingerprints_file = data_dir / 'fingerprints' / f'{episode_id} Fingerprints.tar'

        do_fingerprint = overwrite_fingerprints or not fingerprints_file.exists()

        do_youtube_beginning_slice = overwrite_youtube_slices or (do_fingerprint and not youtube_beginning_file.exists())
        do_youtube_ending_slice = overwrite_youtube_slices or (do_fingerprint and not youtube_ending_file.exists())

        do_podcast_beginning_slice = overwrite_podcast_slices or not podcast_beginning_file.exists()
        do_podcast_ending_slice = overwrite_podcast_slices or not podcast_ending_file.exists()

        do_youtube_download = overwrite_youtube_download or (youtube_file is None and (do_youtube_beginning_slice or do_youtube_ending_slice))
        do_podcast_download = overwrite_podcast_download or (podcast_file is None and (do_podcast_beginning_slice or do_podcast_ending_slice))

        d = get_episode_data_from_id(episode_id)
        ts = np.rec.fromrecords(list(map(tuple, d['timestamps'])), names=d['timestamps_columns'], formats=['U8', 'U8', 'U30'])


        # download YouTube and podcast audio files
        if do_youtube_download:
            logger.info(f'downloading YouTube audio for {episode_id}')
            youtube_file = download_youtube_audio(episode_id, data_dir / 'original')
        if do_podcast_download:
            logger.info(f'downloading podcast audio for {episode_id}')
            podcast_file = download_podcast_audio(episode_id, data_dir / 'original')


        # Campaign 1 podcast timestamps may be stored in CBR format, but ffmpeg
        # slices according to ABR times, so timestamps must be coverted back and
        # forth throughout this process
        timestampsBitrate = d.get('timestampsBitrate', None)
        ABR = d.get('ABR', None)
        if not ABR or not timestampsBitrate:
            bitrate_conversion_factor = 1
        else:
            bitrate_conversion_factor = ABR/timestampsBitrate
            # # for converting stored timestamps to ABR...
            # bitrate_conversion_factor = 1
            # d['timestampsBitrate'] = ABR


        # slice beginning and ending of YouTube and podcast audio files
        try:
            absolute_slice_times = get_absolute_slice_times(episode_id, podcast_file, bitrate_conversion_factor)
        except Exception as e:
            print(f'Skipping {episode_id} because slice times cannot be determined:', e)
            print()
            continue
        youtube_beginning_start, youtube_beginning_stop = absolute_slice_times['youtube']['beginning']
        podcast_beginning_start, podcast_beginning_stop = absolute_slice_times['podcast']['beginning']
        youtube_ending_start,    youtube_ending_stop    = absolute_slice_times['youtube']['ending']
        podcast_ending_start,    podcast_ending_stop    = absolute_slice_times['podcast']['ending']
        logger.info(f'absolute slice times for {episode_id}: {absolute_slice_times}')
        if do_youtube_beginning_slice:
            logger.info(f'slicing YouTube beginning for {episode_id} from {youtube_file}')
            slice_audio_file(youtube_file, youtube_beginning_file, *absolute_slice_times['youtube']['beginning'], mono=True)
        if do_podcast_beginning_slice:
            logger.info(f'slicing podcast beginning for {episode_id} from {podcast_file}')
            slice_audio_file(podcast_file, podcast_beginning_file, *absolute_slice_times['podcast']['beginning'], mono=True)
        if do_youtube_ending_slice:
            logger.info(f'slicing YouTube ending for {episode_id} from {youtube_file}')
            slice_audio_file(youtube_file, youtube_ending_file, *absolute_slice_times['youtube']['ending'], mono=True)
        if do_podcast_ending_slice:
            logger.info(f'slicing podcast ending for {episode_id} from {podcast_file}')
            slice_audio_file(podcast_file, podcast_ending_file, *absolute_slice_times['podcast']['ending'], mono=True)


        with Matcher(db) as m:

            # remove existing fingerprints left over from the previous episode
            # or prior runs of the script
            m.empty_fingerprints()

            if do_fingerprint:
                # create and store fingerprints for the YouTube audio slices
                Path(fingerprints_file).parent.mkdir(parents=True, exist_ok=True)
                m.fingerprint_file(youtube_beginning_file)
                m.fingerprint_file(youtube_ending_file)
                m.store_fingerprints(fingerprints_file)
            else:
                # load fingerprints previously saved for the YouTube audio slices
                m.load_fingerprints(fingerprints_file)


            if len(ts) != 4:
                print(f'Skipping {episode_id}, which does not have the typical number of pairs of timestamps (expected 4, found {len(ts)}).')
                print('This may mean the episode contains more than one discontinuity (normally just the intermission).')
                print('It will need to be synced manually.')
                print()

                # clear date_verified
                d['date_verified'] = ''

                continue


            # match podcast beginning slice to YouTube beginning slice
            beginning_matches = m.match(podcast_beginning_file)
            assert beginning_matches[0].name == youtube_beginning_file.stem, f'{episode_id}: first match ({beginning_matches[0].name}) is not the expected file ({youtube_beginning_file.stem}): {beginning_matches}'

            # match podcast ending slice to YouTube ending slice
            ending_matches = m.match(podcast_ending_file)
            assert ending_matches[0].name == youtube_ending_file.stem, f'{episode_id}: first match ({ending_matches[0].name}) is not the expected file ({youtube_ending_file.stem}): {ending_matches}'


            # calculate the first podcast timestamp
            podcast_beginning_timestamp = podcast_beginning_start * bitrate_conversion_factor - beginning_matches[0].offset
            if podcast_beginning_timestamp.round() < 0:
                print(f'Skipping {episode_id}, which was determined to have a negative podcast beginning timestamp ({podcast_beginning_timestamp.text}).')
                print('This indicates a problem with matching that may need to be addressed by slicing the audio differently.')
                print()

                # clear date_verified
                d['date_verified'] = ''

                continue

            # calculate the last podcast timestamp
            youtube_ending_slice_duration = youtube_ending_stop - youtube_ending_start
            podcast_ending_timestamp = podcast_ending_start * bitrate_conversion_factor + (youtube_ending_slice_duration - ending_matches[0].offset)
            if podcast_ending_timestamp.round() < 0:
                print(f'Skipping {episode_id}, which was determined to have a negative podcast beginning timestamp ({podcast_ending_timestamp.text}).')
                print('This indicates a problem with matching that may need to be addressed by slicing the audio differently.')
                print()

                # clear date_verified
                d['date_verified'] = ''

                continue

            # calculate other podcast timestamps
            prebreak_duration, break_duration, postbreak_duration = np.diff(Time(ts.youtube))
            prebreak_duration = prebreak_duration * bitrate_conversion_factor
            postbreak_duration = postbreak_duration * bitrate_conversion_factor
            podcast_timestamps = Time([
                podcast_beginning_timestamp,
                podcast_beginning_timestamp + prebreak_duration,
                podcast_ending_timestamp - postbreak_duration,
                podcast_ending_timestamp
            ]).text
            ts_new = ts.copy()
            ts_new.podcast = podcast_timestamps


            # report new timestamps, differences from old timestamps, and match confidence
            diff = np.full(4, np.nan)
            for i, (new, old) in enumerate(zip(ts_new.podcast, ts.podcast)):
                if old:
                    diff[i] = Time(new) - Time(old)
            table = np.column_stack([ts_new.tolist(), [f'{dd:+4g}' for dd in diff], [beginning_matches[0].confidence, '', '', ending_matches[0].confidence]])
            table = np.row_stack([d['timestamps_columns'] + ['diff', 'confidence'], table])
            column_widths = np.vectorize(len)(table).max(axis=0)
            w1, w2, w3, w4, w5 = column_widths
            fmt = f'{{:{w1}}}  {{:{w2}}}  {{:{w3}}}\t{{:{w4}}}  {{:{w5}}}'
            table = [fmt.format(*row) for row in table]
            table = '\n'.join(table)
            print(table)
            print()


            # update data object with new timestamps and clear date_verified
            d['timestamps'] = ts_new.tolist()
            d['date_verified'] = ''

            # write changes to data.json
            write_data(data)
