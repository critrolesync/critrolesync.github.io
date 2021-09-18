from pathlib import Path
import numpy as np
import ffmpeg
from librosa import get_duration
import logging
from critrolesync import data, write_data, sec2str, str2sec, get_episode_data_from_id, \
                         download_youtube_audio, download_podcast_audio
from critrolesync.autosync import Matcher

logger = logging.getLogger(__name__)

# logging.basicConfig(level=logging.INFO)


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


youtube_beginning_slice_duration = 6 * 60  # sec
youtube_ending_slice_duration = 2 * 60  # sec
youtube_beginning_slice_offset_from_first_timestamp = 0  # sec
youtube_ending_slice_offset_from_last_timestamp = -youtube_ending_slice_duration  # sec

podcast_beginning_slice_duration = 10  # sec
podcast_ending_slice_duration = 10  # sec
podcast_beginning_slice_offset_from_start = 5 * 60  # sec
podcast_ending_slice_offset_from_end = -120  # sec


def get_slice_times(episode_id, podcast_file):
    d = get_episode_data_from_id(episode_id)
    ts = np.rec.fromrecords(list(map(tuple, d['timestamps'])), names=d['timestamps_columns'], formats=['O']*len(d['timestamps_columns']))
    podcast_duration = get_duration(filename=podcast_file)

    youtube_beginning_start = sec2str(str2sec(ts.youtube[0])  + youtube_beginning_slice_offset_from_first_timestamp)
    youtube_ending_start    = sec2str(str2sec(ts.youtube[-1]) + youtube_ending_slice_offset_from_last_timestamp)
    podcast_beginning_start = sec2str(0                       + podcast_beginning_slice_offset_from_start)
    podcast_ending_start    = sec2str(podcast_duration        + podcast_ending_slice_offset_from_end)

    youtube_beginning_stop = sec2str(str2sec(youtube_beginning_start) + youtube_beginning_slice_duration)
    youtube_ending_stop    = sec2str(str2sec(youtube_ending_start)    + youtube_ending_slice_duration)
    podcast_beginning_stop = sec2str(str2sec(podcast_beginning_start) + podcast_beginning_slice_duration)
    podcast_ending_stop    = sec2str(str2sec(podcast_ending_start)    + podcast_ending_slice_duration)

    return {
        'youtube': {
            'beginning': (youtube_beginning_start, youtube_beginning_stop),
            'ending':    (youtube_ending_start,    youtube_ending_stop),
        },
        'podcast': {
            'beginning': (podcast_beginning_start, podcast_beginning_stop),
            'ending':    (podcast_ending_start,    podcast_ending_stop),
        },
    }


overwrite_youtube_download = False
overwrite_podcast_download = False
overwrite_slices = False
overwrite_fingerprints = False

test_dir = Path('testdata')
test_dir.mkdir(parents=True, exist_ok=True)

# episode_ids = [f'C2E{i}' for i in range(20, 141)]
episode_ids = [f'C2E{i}' for i in range(100, 105)]


for episode_id in episode_ids:
    print(episode_id)

    youtube_file = test_dir / 'original' / f'{episode_id} YouTube.m4a'
    podcast_file = test_dir / 'original' / f'{episode_id} Podcast.m4a'

    youtube_beginning_file = test_dir / 'youtube-slices' / f'{episode_id} YouTube - Beginning.m4a'
    podcast_beginning_file = test_dir / 'podcast-slices' / f'{episode_id} Podcast - Beginning.m4a'

    youtube_ending_file = test_dir / 'youtube-slices' / f'{episode_id} YouTube - Ending.m4a'
    podcast_ending_file = test_dir / 'podcast-slices' / f'{episode_id} Podcast - Ending.m4a'

    fingerprints_file = test_dir / 'fingerprints' / f'{episode_id} Fingerprints.tar'

    d = get_episode_data_from_id(episode_id)
    ts = np.rec.fromrecords(list(map(tuple, d['timestamps'])), names=d['timestamps_columns'], formats=['O']*len(d['timestamps_columns']))


    # download YouTube and podcast audio files
    if not youtube_file.exists() or overwrite_youtube_download:
        logger.info(f'downloading YouTube audio for {episode_id}')
        download_youtube_audio(episode_id, youtube_file)
    if not podcast_file.exists() or overwrite_podcast_download:
        logger.info(f'downloading podcast audio for {episode_id}')
        download_podcast_audio(episode_id, podcast_file)


    # slice beginning and ending of YouTube and podcast audio files
    slice_times = get_slice_times(episode_id, podcast_file)
    youtube_beginning_start, youtube_beginning_stop = slice_times['youtube']['beginning']
    podcast_beginning_start, podcast_beginning_stop = slice_times['podcast']['beginning']
    youtube_ending_start,    youtube_ending_stop    = slice_times['youtube']['ending']
    podcast_ending_start,    podcast_ending_stop    = slice_times['podcast']['ending']
    logger.info(f'slice times for {episode_id}: {slice_times}')
    if not youtube_beginning_file.exists() or overwrite_slices:
        logger.info(f'slicing YouTube beginning for {episode_id}')
        slice_audio_file(youtube_file, youtube_beginning_file, *slice_times['youtube']['beginning'], mono=True)
    if not podcast_beginning_file.exists() or overwrite_slices:
        logger.info(f'slicing podcast beginning for {episode_id}')
        slice_audio_file(podcast_file, podcast_beginning_file, *slice_times['podcast']['beginning'], mono=True)
    if not youtube_ending_file.exists() or overwrite_slices:
        logger.info(f'slicing YouTube ending for {episode_id}')
        slice_audio_file(youtube_file, youtube_ending_file, *slice_times['youtube']['ending'], mono=True)
    if not podcast_ending_file.exists() or overwrite_slices:
        logger.info(f'slicing podcast ending for {episode_id}')
        slice_audio_file(podcast_file, podcast_ending_file, *slice_times['podcast']['ending'], mono=True)


    with Matcher() as m:

        if not fingerprints_file.exists() or overwrite_fingerprints:
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
            continue


        # match podcast beginning slice to YouTube beginning slice
        beginning_matches = m.match(podcast_beginning_file)
        assert beginning_matches[0].name == youtube_beginning_file.stem, f'{episode_id}: first match ({beginning_matches[0].name}) is not the expected file ({youtube_beginning_file.stem}): {beginning_matches}'

        # match podcast ending slice to YouTube ending slice
        ending_matches = m.match(podcast_ending_file)
        assert ending_matches[0].name == youtube_ending_file.stem, f'{episode_id}: first match ({ending_matches[0].name}) is not the expected file ({youtube_ending_file.stem}): {ending_matches}'


        # calculate the first podcast timestamp
        podcast_beginning_timestamp = round(str2sec(podcast_beginning_start) - (str2sec(youtube_beginning_start) + beginning_matches[0].offset))
        if podcast_beginning_timestamp >= 0:
            podcast_beginning_timestamp = sec2str(podcast_beginning_timestamp)
        else:
            print(f'Skipping {episode_id}, which was determined to have a negative podcast beginning timestamp (-{sec2str(-podcast_beginning_timestamp)}).')
            print('This indicates a problem with matching that may need to be addressed by slicing the audio differently.')
            print()
            continue

        # calculate the last podcast timestamp
        podcast_ending_timestamp = round(str2sec(podcast_ending_start) + (youtube_ending_slice_duration - ending_matches[0].offset))
        if podcast_ending_timestamp >= 0:
            podcast_ending_timestamp = sec2str(podcast_ending_timestamp)
        else:
            print(f'Skipping {episode_id}, which was determined to have a negative podcast beginning timestamp (-{sec2str(-podcast_ending_timestamp)}).')
            print('This indicates a problem with matching that may need to be addressed by slicing the audio differently.')
            print()
            continue

        # calculate other podcast timestamps
        prebreak_duration, break_duration, postbreak_duration = np.diff(list(map(str2sec, ts.youtube)))
        podcast_timestamps = np.empty(4, dtype='object')
        podcast_timestamps[0] = podcast_beginning_timestamp
        podcast_timestamps[1] = sec2str(str2sec(podcast_beginning_timestamp) + prebreak_duration)
        podcast_timestamps[2] = sec2str(str2sec(podcast_ending_timestamp) - postbreak_duration)
        podcast_timestamps[3] = podcast_ending_timestamp
        ts_new = ts.copy()
        ts_new.podcast = podcast_timestamps


        # report new timestamps, differences from old timestamps, and match confidence
        diff = np.full(4, np.nan)
        for i, (new, old) in enumerate(zip(ts_new.podcast, ts.podcast)):
            if old:
                diff[i] = str2sec(new) - str2sec(old)
        print(d['timestamps_columns'], '\t', 'diff', '\t', 'confidence')
        print(ts_new[0], '\t', f'{diff[0]:+4g}', '\t', beginning_matches[0].confidence)
        print(ts_new[1], '\t', f'{diff[1]:+4g}')
        print(ts_new[2], '\t', f'{diff[2]:+4g}')
        print(ts_new[3], '\t', f'{diff[3]:+4g}', '\t', ending_matches[0].confidence)
        print()


        # update data object with new timestamps
        c, e = episode_id.strip('C').split('E')
        assert data[int(c)-1]['episodes'][int(e)-1]['id'] == episode_id
        data[int(c)-1]['episodes'][int(e)-1]['timestamps'] = ts_new.tolist()
        data[int(c)-1]['episodes'][int(e)-1]['date_verified'] = ''  # clear date_verified


# write changes to data.json
write_data(data)
