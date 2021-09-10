"""
Download audio files:
  * download_youtube_audio
  * download_podcast_audio
"""

import os
from glob import glob
import json
import shutil
import requests
from tqdm.auto import tqdm
import youtube_dl


with open('../docs/data.json') as f:
    data = json.load(f)

feed_archive_path = os.path.join(os.path.dirname(__file__), 'feed-archive')
most_recent_parsed_nerdist_feed = glob(os.path.join(feed_archive_path, 'nerdist/parsed/*.json'))[-1]
most_recent_parsed_criticalrole_feed = glob(os.path.join(feed_archive_path, 'critical-role/parsed/*.json'))[-1]
feed = []
with open(most_recent_parsed_nerdist_feed) as f:
    feed += json.load(f)
with open(most_recent_parsed_criticalrole_feed) as f:
    feed += json.load(f)


def get_episode_data_from_id(episode_id):
    c, e = map(int, episode_id.strip('C').split('E'))
    try:
        return next(filter(lambda ep: ep['id'] == episode_id, data[c-1]['episodes']))
    except StopIteration:
        raise ValueError(f'episode with id "{episode_id}" not found')

def get_episode_feed_from_title(episode_title):
    try:
        return next(filter(lambda ep: ep['Title'].startswith(episode_title), feed))
    except StopIteration:
        raise ValueError(f'episode with title starting with "{episode_title}" not found')


def download_youtube_audio(episode_id, output_file=None):

    # get the YouTube video ID
    ep = get_episode_data_from_id(episode_id)
    youtube_id = ep['youtube_id']

    # determine where to permanently save the file after download
    if output_file is None:
        output_file = f'{episode_id} YouTube.%(ext)s'

    ydl_opts = {'outtmpl': output_file, 'format': 'bestaudio/best', 'postprocessors': [{'key': 'FFmpegExtractAudio'}]}
    with youtube_dl.YoutubeDL(ydl_opts) as ydl:
        ydl.download([f'https://www.youtube.com/watch?v={youtube_id}'])

def download_podcast_audio(episode_title, output_file=None):

    # get the podcast audio file URL from the feed archive
    ep = get_episode_feed_from_title(episode_title)
    url = ep['URL']

    # determine where to permanently save the file after download
    if output_file is None:
        ext = ep['File'].split('.')[-1]
        output_file = f'{episode_title} Podcast.{ext}'

    download_file(url, output_file)

def download_file(url, output_file, bytes_per_chunk=1024*32):

    # determine where to temporarily save the file during download
    temp_file = output_file + '.part'

    # create the containing directory if necessary
    output_dir = os.path.dirname(output_file)
    if output_dir and not os.path.exists(output_dir):
        os.makedirs(output_dir)

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
        if os.path.exists(temp_file):
            os.remove(temp_file)

        # raise the exception so that it can be handled elsewhere
        raise

    else:
        # download completed, so move the temp file to the final location
        shutil.move(temp_file, output_file)
