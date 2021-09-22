"""
Download audio files:
  * download_youtube_audio
  * download_podcast_audio
"""

from pathlib import Path
import shutil
import json
import requests
from tqdm.auto import tqdm
import youtube_dl

from . import data
from .tools import get_episode_data_from_id


_latest_parsed_nerdist_feed = list(Path(__file__).parent.joinpath('../../feed-archive/nerdist/parsed').glob('*.json'))[-1]
_latest_parsed_criticalrole_feed = list(Path(__file__).parent.joinpath('../../feed-archive/critical-role/parsed').glob('*.json'))[-1]
latest_parsed_podcast_feed = []
with open(_latest_parsed_nerdist_feed) as _fd:
    latest_parsed_podcast_feed += json.load(_fd)
with open(_latest_parsed_criticalrole_feed) as _fd:
    latest_parsed_podcast_feed += json.load(_fd)

def get_podcast_feed_from_title(episode_title):
    ep = None
    for episode in latest_parsed_podcast_feed:
        if episode_title.lower() in episode['Title'].lower():
            if ep is None:
                ep = episode
            else:
                raise ValueError(f'episode title substring "{episode_title}" is not unique')
    if ep:
        return ep
    else:
        raise ValueError(f'episode with title containing "{episode_title}" not found')

def download_youtube_audio(episode_id, output_file=None):

    # get the YouTube video ID
    ep = get_episode_data_from_id(episode_id)
    youtube_id = ep['youtube_id']

    # determine where to permanently save the file after download
    if output_file is None:
        output_file = f'{episode_id} YouTube.%(ext)s'
    else:
        output_file = str(output_file)

    ydl_opts = {'outtmpl': output_file, 'format': 'bestaudio/best', 'postprocessors': [{'key': 'FFmpegExtractAudio'}]}
    with youtube_dl.YoutubeDL(ydl_opts) as ydl:
        url = f'https://www.youtube.com/watch?v={youtube_id}'
        info_dict = ydl.extract_info(url, download=True)
        actual_output_file = Path(ydl.prepare_filename(info_dict))

        # return the output file path
        return actual_output_file

def download_podcast_audio(episode_title, output_file=None):

    # get the podcast audio file URL from the feed archive
    try:
        # we try it this way first because there is at least one example (C1E78)
        # where the title is spelled differently in the feed
        c, e = episode_id.strip('C').split('E')
        if c == '1':
            episode_title = f'Vox Machina Ep. {e} '  # include trailing space to distinguish 1, 10, 100, etc.
        elif c == '2':
            episode_title = f'{episode_id} '         # include trailing space to distinguish 1, 10, 100, etc.
        else:
            raise NotImplementedError
    except:
        # we fall back on the actual title if the episode is not part of the
        # main campaigns
        episode_title = get_episode_data_from_id(episode_id)['title']
    ep = get_podcast_feed_from_title(episode_title)
    url = ep['URL']

    # determine where to permanently save the file after download
    if output_file is None:
        ext = ep['File'].split('.')[-1]
        output_file = f'{episode_title} Podcast.{ext}'

    _download_file(url, output_file)

    # return the output file path
    return Path(output_file)

def _download_file(url, output_file, bytes_per_chunk=1024*32):

    # determine where to temporarily save the file during download
    temp_file = str(output_file) + '.part'

    # create the containing directory if necessary
    Path(output_file).parent.mkdir(parents=True, exist_ok=True)

    try:
        response = requests.get(url, stream=True)
        file_size_in_bytes = int(response.headers.get('content-length', 0))
        with tqdm(total=file_size_in_bytes, unit='B', unit_scale=True) as pbar:
            with open(temp_file, 'wb') as f:
                for chunk in response.iter_content(bytes_per_chunk):
                    f.write(chunk)
                    pbar.update(len(chunk))

    except:
        # the download is likely incomplete, so delete the temporary file
        Path(temp_file).unlink(missing_ok=True)

        # raise the exception so that it can be handled elsewhere
        raise

    else:
        # download completed, so move the temp file to the final location
        shutil.move(temp_file, output_file)
