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


def slice_audio_file(input_file, output_file, start=None, end=None, mono=False):
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


test_dir = Path('testdata')
test_dir.mkdir(parents=True, exist_ok=True)

# episode_ids = ['C2E20']
episode_ids = [f'C2E{i}' for i in range(100, 105)]



# download all YouTube and podcast audio files

for episode_id in episode_ids:

    youtube_file = test_dir / 'original' / f'{episode_id} YouTube.m4a'
    podcast_file = test_dir / 'original' / f'{episode_id} Podcast.m4a'

    if not youtube_file.exists():
        logger.info(f'downloading YouTube audio for {episode_id}')
        download_youtube_audio(episode_id, youtube_file)
    if not podcast_file.exists():
        logger.info(f'downloading podcast audio for {episode_id}')
        download_podcast_audio(episode_id, podcast_file)


# slice beginning and ending for all YouTube audio files

youtube_beginning_duration = 6 * 60  # sec
youtube_ending_duration = 2 * 60  # sec
podcast_beginning_duration = 10  # sec
podcast_ending_duration = 10  # sec

overwrite_slices = False

for episode_id in episode_ids:

    d = get_episode_data_from_id(episode_id)
    ts = np.rec.fromrecords(d['timestamps'], names=d['timestamps_columns'])

    youtube_file = test_dir / 'original' / f'{episode_id} YouTube.m4a'
    podcast_file = test_dir / 'original' / f'{episode_id} Podcast.m4a'



    youtube_beginning_file = test_dir / 'youtube-slices' / f'{episode_id} YouTube - Beginning.m4a'
    podcast_beginning_file = test_dir / 'podcast-slices' / f'{episode_id} Podcast - Beginning.m4a'

    youtube_beginning_start = ts.youtube[0]
    youtube_beginning_stop = sec2str(str2sec(youtube_beginning_start) + youtube_beginning_duration)

    podcast_beginning_start = '00:05:00'
    podcast_beginning_stop = sec2str(str2sec(podcast_beginning_start) + podcast_beginning_duration)

    if not youtube_beginning_file.exists() or overwrite_slices:
        logger.info(f'slicing YouTube beginning for {episode_id}')
        slice_audio_file(youtube_file, youtube_beginning_file, youtube_beginning_start, youtube_beginning_stop, mono=True)
    if not podcast_beginning_file.exists() or overwrite_slices:
        logger.info(f'slicing podcast beginning for {episode_id}')
        slice_audio_file(podcast_file, podcast_beginning_file, podcast_beginning_start, podcast_beginning_stop, mono=True)


    youtube_ending_file = test_dir / 'youtube-slices' / f'{episode_id} YouTube - Ending.m4a'
    podcast_ending_file = test_dir / 'podcast-slices' / f'{episode_id} Podcast - Ending.m4a'

    youtube_ending_stop = ts.youtube[-1]
    youtube_ending_start = sec2str(str2sec(youtube_ending_stop) - youtube_ending_duration)

    podcast_ending_start = sec2str(get_duration(filename=podcast_file) - 120)
    podcast_ending_stop = sec2str(str2sec(podcast_ending_start) + podcast_ending_duration)

    if not youtube_ending_file.exists() or overwrite_slices:
        logger.info(f'slicing YouTube ending for {episode_id}')
        slice_audio_file(youtube_file, youtube_ending_file, youtube_ending_start, youtube_ending_stop, mono=True)
    if not podcast_ending_file.exists() or overwrite_slices:
        logger.info(f'slicing podcast ending for {episode_id}')
        slice_audio_file(podcast_file, podcast_ending_file, podcast_ending_start, podcast_ending_stop, mono=True)



# fingerprint all YouTube audio slices

database_backup = test_dir / 'db.tar'

extend_fingerprint_database = True

if not database_backup.exists() or extend_fingerprint_database:
    with Matcher() as m:
        if database_backup.exists():
            m.load_fingerprints(database_backup)
        m.generate_fingerprints(test_dir / 'youtube-slices')
        m.store_fingerprints(database_backup)



# match each podcast slice to a YouTube slice and determine timestamps

with Matcher() as m:
    m.load_fingerprints(database_backup)

    for episode_id in episode_ids:
        print(episode_id)

        d = get_episode_data_from_id(episode_id)
        ts = np.rec.fromrecords(d['timestamps'], names=d['timestamps_columns'])

        if len(ts) != 4:
            print(f'Skipping {episode_id}, which does not have the typical number of pairs of timestamps (expected 4, found {len(ts)}).')
            print('This may mean the episode contains more than one discontinuity (normally just the intermission).')
            print('It will need to be synced manually.')
            print()
            continue

        podcast_timestamps = np.empty(4, dtype='object')



        youtube_file = test_dir / 'original' / f'{episode_id} YouTube.m4a'
        podcast_file = test_dir / 'original' / f'{episode_id} Podcast.m4a'

        youtube_beginning_file = test_dir / 'youtube-slices' / f'{episode_id} YouTube - Beginning.m4a'
        podcast_beginning_file = test_dir / 'podcast-slices' / f'{episode_id} Podcast - Beginning.m4a'

        youtube_ending_file = test_dir / 'youtube-slices' / f'{episode_id} YouTube - Ending.m4a'
        podcast_ending_file = test_dir / 'podcast-slices' / f'{episode_id} Podcast - Ending.m4a'



        youtube_beginning_start = ts.youtube[0]
        youtube_beginning_stop = sec2str(str2sec(youtube_beginning_start) + youtube_beginning_duration)

        podcast_beginning_start = '00:05:00'
        podcast_beginning_stop = sec2str(str2sec(podcast_beginning_start) + podcast_beginning_duration)

        matches = m.match(podcast_beginning_file)
        assert matches[0].name == youtube_beginning_file.stem, f'{episode_id}: first match ({matches[0].name}) is not the expected file ({youtube_beginning_file.stem})'
        podcast_beginning_timestamp = sec2str(str2sec(podcast_beginning_start) - (str2sec(youtube_beginning_start) + matches[0].offset))
        podcast_beginning_confidence = matches[0].confidence
        logger.info(f'    Podcast "{ts.comment[0]}" at {podcast_beginning_timestamp}')
        logger.info('        All matches:')
        for mm in matches:
            logger.info(f'            {mm}')



        youtube_ending_stop = ts.youtube[-1]
        youtube_ending_start = sec2str(str2sec(youtube_ending_stop) - youtube_ending_duration)

        podcast_ending_start = sec2str(get_duration(filename=podcast_file) - 120)
        podcast_ending_stop = sec2str(str2sec(podcast_ending_start) + podcast_ending_duration)

        matches = m.match(podcast_ending_file)
        assert matches[0].name == youtube_ending_file.stem, f'{episode_id}: first match ({matches[0].name}) is not the expected file ({youtube_ending_file.stem})'
        podcast_ending_timestamp = sec2str(str2sec(podcast_ending_start) + youtube_ending_duration - matches[0].offset)
        podcast_ending_confidence = matches[0].confidence
        logger.info(f'    Podcast "{ts.comment[-1]}" at {podcast_ending_timestamp}')
        logger.info('        All matches:')
        for mm in matches:
            logger.info(f'            {mm}')



        segment_1_duration, break_duration, segment_2_duration = np.diff(list(map(str2sec, ts.youtube)))
        podcast_timestamps[0] = podcast_beginning_timestamp
        podcast_timestamps[1] = sec2str(str2sec(podcast_beginning_timestamp) + segment_1_duration)
        podcast_timestamps[2] = sec2str(str2sec(podcast_ending_timestamp) - segment_2_duration)
        podcast_timestamps[3] = podcast_ending_timestamp

        ts_new = ts.copy()
        ts_new.podcast = podcast_timestamps
        diff = np.array(list(map(str2sec, ts_new.podcast))) - np.array(list(map(str2sec, ts.podcast)))
        print(d['timestamps_columns'], '\t', 'diff', '\t', 'confidence')
        print(ts_new[0], '\t', f'{diff[0]:+4g}', '\t', podcast_beginning_confidence)
        print(ts_new[1], '\t', f'{diff[1]:+4g}')
        print(ts_new[2], '\t', f'{diff[2]:+4g}')
        print(ts_new[3], '\t', f'{diff[3]:+4g}', '\t', podcast_ending_confidence)
        print()

        # update data
        c, e = episode_id.strip('C').split('E')
        assert data[int(c)-1]['episodes'][int(e)-1]['id'] == episode_id
        data[int(c)-1]['episodes'][int(e)-1]['timestamps'] = ts_new.tolist()
        data[int(c)-1]['episodes'][int(e)-1]['date_verified'] = ''  # clear date_verified

    # write changes to data.json
    write_data(data)
