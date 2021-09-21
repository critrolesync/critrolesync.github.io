from pathlib import Path
import json
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

with open('custom-podcast-slice-times.json') as _fd:
    custom_podcast_slice_times = json.load(_fd)

def get_absolute_slice_times(episode_id, podcast_file, bitrate_conversion_factor=None):
    d = get_episode_data_from_id(episode_id)
    ts = np.rec.fromrecords(list(map(tuple, d['timestamps'])), names=d['timestamps_columns'], formats=['O']*len(d['timestamps_columns']))
    podcast_duration = get_duration(filename=podcast_file) # * 128/127.7  # get_duration returns CBR duration and would need to be replaced with an ABR method if stored timestamps are converted to ABR

    podcast_slice_times = default_podcast_slice_times.copy()
    podcast_slice_times.update(custom_podcast_slice_times.get(episode_id, {}))

    youtube_beginning_start = sec2str(str2sec(ts.youtube[0])  + str2sec(youtube_slice_times['beginning'][0]))
    youtube_ending_start    = sec2str(str2sec(ts.youtube[-1]) + str2sec(youtube_slice_times['ending'][0]))
    podcast_beginning_start = sec2str(0                       + str2sec(podcast_slice_times['beginning'][0]))
    podcast_ending_start    = sec2str(podcast_duration        + str2sec(podcast_slice_times['ending'][0]))

    youtube_beginning_stop  = sec2str(str2sec(ts.youtube[0])  + str2sec(youtube_slice_times['beginning'][1]))
    youtube_ending_stop     = sec2str(str2sec(ts.youtube[-1]) + str2sec(youtube_slice_times['ending'][1]))
    podcast_beginning_stop  = sec2str(0                       + str2sec(podcast_slice_times['beginning'][1]))
    podcast_ending_stop     = sec2str(podcast_duration        + str2sec(podcast_slice_times['ending'][1]))

    if bitrate_conversion_factor:
        podcast_beginning_start = sec2str(str2sec(podcast_beginning_start) / bitrate_conversion_factor)
        podcast_ending_start    = sec2str(str2sec(podcast_ending_start)    / bitrate_conversion_factor)
        podcast_beginning_stop  = sec2str(str2sec(podcast_beginning_stop)  / bitrate_conversion_factor)
        podcast_ending_stop     = sec2str(str2sec(podcast_ending_stop)     / bitrate_conversion_factor)

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
episode_ids = [f'C2E{i}' for i in range(1, 20)]


for episode_id in episode_ids:
    print(episode_id)

    youtube_file = next(iter([p for p in (test_dir / 'original').glob(f'{episode_id} YouTube.*') if not str(p).endswith('.part')]), None)
    podcast_file = next(iter([p for p in (test_dir / 'original').glob(f'{episode_id} Podcast.*') if not str(p).endswith('.part')]), None)

    youtube_beginning_file = test_dir / 'youtube-slices' / f'{episode_id} YouTube - Beginning.m4a'
    podcast_beginning_file = test_dir / 'podcast-slices' / f'{episode_id} Podcast - Beginning.m4a'

    youtube_ending_file = test_dir / 'youtube-slices' / f'{episode_id} YouTube - Ending.m4a'
    podcast_ending_file = test_dir / 'podcast-slices' / f'{episode_id} Podcast - Ending.m4a'

    fingerprints_file = test_dir / 'fingerprints' / f'{episode_id} Fingerprints.tar'

    d = get_episode_data_from_id(episode_id)
    ts = np.rec.fromrecords(list(map(tuple, d['timestamps'])), names=d['timestamps_columns'], formats=['O']*len(d['timestamps_columns']))


    # download YouTube and podcast audio files
    if youtube_file is None or overwrite_youtube_download:
        logger.info(f'downloading YouTube audio for {episode_id}')
        youtube_file = download_youtube_audio(episode_id, test_dir / 'original')
    if podcast_file is None or overwrite_podcast_download:
        logger.info(f'downloading podcast audio for {episode_id}')
        podcast_file = download_podcast_audio(episode_id, test_dir / 'original')


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
    absolute_slice_times = get_absolute_slice_times(episode_id, podcast_file, bitrate_conversion_factor)
    youtube_beginning_start, youtube_beginning_stop = absolute_slice_times['youtube']['beginning']
    podcast_beginning_start, podcast_beginning_stop = absolute_slice_times['podcast']['beginning']
    youtube_ending_start,    youtube_ending_stop    = absolute_slice_times['youtube']['ending']
    podcast_ending_start,    podcast_ending_stop    = absolute_slice_times['podcast']['ending']
    logger.info(f'absolute slice times for {episode_id}: {absolute_slice_times}')
    if not youtube_beginning_file.exists() or overwrite_slices:
        logger.info(f'slicing YouTube beginning for {episode_id}')
        slice_audio_file(youtube_file, youtube_beginning_file, *absolute_slice_times['youtube']['beginning'], mono=True)
    if not podcast_beginning_file.exists() or overwrite_slices:
        logger.info(f'slicing podcast beginning for {episode_id}')
        slice_audio_file(podcast_file, podcast_beginning_file, *absolute_slice_times['podcast']['beginning'], mono=True)
    if not youtube_ending_file.exists() or overwrite_slices:
        logger.info(f'slicing YouTube ending for {episode_id}')
        slice_audio_file(youtube_file, youtube_ending_file, *absolute_slice_times['youtube']['ending'], mono=True)
    if not podcast_ending_file.exists() or overwrite_slices:
        logger.info(f'slicing podcast ending for {episode_id}')
        slice_audio_file(podcast_file, podcast_ending_file, *absolute_slice_times['podcast']['ending'], mono=True)


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
        podcast_beginning_timestamp = sec2str(str2sec(podcast_beginning_start) * bitrate_conversion_factor - beginning_matches[0].offset)
        if podcast_beginning_timestamp[0] == '-':
            print(f'Skipping {episode_id}, which was determined to have a negative podcast beginning timestamp ({podcast_beginning_timestamp}).')
            print('This indicates a problem with matching that may need to be addressed by slicing the audio differently.')
            print()

            # clear date_verified
            d['date_verified'] = ''

            continue

        # calculate the last podcast timestamp
        youtube_ending_slice_duration = str2sec(youtube_ending_stop) - str2sec(youtube_ending_start)
        podcast_ending_timestamp = sec2str(str2sec(podcast_ending_start) * bitrate_conversion_factor + (youtube_ending_slice_duration - ending_matches[0].offset))
        if podcast_ending_timestamp[0] == '-':
            print(f'Skipping {episode_id}, which was determined to have a negative podcast beginning timestamp ({podcast_ending_timestamp}).')
            print('This indicates a problem with matching that may need to be addressed by slicing the audio differently.')
            print()

            # clear date_verified
            d['date_verified'] = ''

            continue

        # calculate other podcast timestamps
        prebreak_duration, break_duration, postbreak_duration = np.diff(list(map(str2sec, ts.youtube)))
        prebreak_duration = prebreak_duration * bitrate_conversion_factor
        postbreak_duration = postbreak_duration * bitrate_conversion_factor
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


        # update data object with new timestamps and clear date_verified
        d['timestamps'] = ts_new.tolist()
        d['date_verified'] = ''


# write changes to data.json
write_data(data)
