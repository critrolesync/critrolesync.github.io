from pathlib import Path
import ffmpeg
from pydub import AudioSegment
import logging
from critrolesync import sec2str, str2sec, download_youtube_audio, download_podcast_audio
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

youtube_sample_start = '00:00:00'
youtube_sample_duration = 6 * 60  # sec
youtube_sample_stop = sec2str(str2sec(youtube_sample_start) + youtube_sample_duration)

podcast_sample_start = '00:05:00'
podcast_sample_duration = 20  # sec
podcast_sample_stop = sec2str(str2sec(podcast_sample_start) + podcast_sample_duration)

offset_by_design = str2sec(podcast_sample_start) - str2sec(youtube_sample_start)


# episode_ids = ['C2E20']
episode_ids = [f'C2E{i}' for i in range(100, 105)]

for episode_id in episode_ids:


    youtube_file = test_dir / 'original' / f'{episode_id} YouTube.m4a'
    podcast_file = test_dir / 'original' / f'{episode_id} Podcast.m4a'

    if not youtube_file.exists():
        logger.info(f'downloading YouTube audio for {episode_id}')
        download_youtube_audio(episode_id, youtube_file)
    if not podcast_file.exists():
        logger.info(f'downloading podcast audio for {episode_id}')
        download_podcast_audio(episode_id, podcast_file)


    youtube_file_beginning = test_dir / 'youtube-slices' / f'{episode_id} YouTube - Beginning.m4a'
    podcast_file_beginning = test_dir / 'podcast-slices' / f'{episode_id} Podcast - Beginning.m4a'

    overwrite_slices = False
    if not youtube_file_beginning.exists() or overwrite_slices:
        logger.info(f'slicing YouTube sample for {episode_id}')
        slice_audio_file(youtube_file, youtube_file_beginning, youtube_sample_start, youtube_sample_stop, mono=True)
    if not podcast_file_beginning.exists() or overwrite_slices:
        logger.info(f'slicing podcast sample for {episode_id}')
        slice_audio_file(podcast_file, podcast_file_beginning, podcast_sample_start, podcast_sample_stop, mono=True)



database_backup = test_dir / 'db.tar'

rebuild_fingerprint_database = False
with Matcher() as m:
    if database_backup.exists() and not rebuild_fingerprint_database:
        m.load_fingerprints(database_backup)

    m.generate_fingerprints(test_dir / 'youtube-slices')
    m.store_fingerprints(database_backup)
    print()

    for episode_id in episode_ids:
        podcast_file_beginning = test_dir / 'podcast-slices' / f'{episode_id} Podcast - Beginning.m4a'
        results = m.match(podcast_file_beginning)
        print(f'{episode_id}: Podcast opening ads end at {sec2str(offset_by_design - results[0].offset)}')
        print('    All matches:')
        for r in results:
            print('        ', r)
        print()
