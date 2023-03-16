"""
Download audio files:
  * download_youtube_audio
  * download_podcast_audio
"""

from pathlib import Path
import shutil
import requests
from tqdm.auto import tqdm
import yt_dlp

from . import data
from .tools import get_episode_data_from_id, get_podcast_feed_from_id


def download_youtube_audio(episode_id, output_dir=None):

    # get the YouTube video ID
    ep = get_episode_data_from_id(episode_id)
    youtube_id = ep['youtube_id']

    # build a filename template for saving after download
    output_file = f'{episode_id} YouTube.%(ext)s'
    if output_dir is not None:
        output_file = str(Path(output_dir) / output_file)

    # prepare a list of files now so that the actual output file can be found
    # after ffmpeg post-processing (its file extension may change without
    # yt-dlp knowing about it, e.g., from .webm to .opus)
    similar_files_before_download = set(Path(output_file).parent.glob(str(Path(output_file).stem) + '.*'))

    # download the audio
    ydl_opts = {'outtmpl': output_file, 'format': 'bestaudio/best', 'postprocessors': [{'key': 'FFmpegExtractAudio'}]}
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        url = f'https://www.youtube.com/watch?v={youtube_id}'
        ydl.download([url])

    # determine the actual name of the new file
    similar_files_after_download = set(Path(output_file).parent.glob(str(Path(output_file).stem) + '.*'))
    actual_output_file = next(iter(similar_files_after_download - similar_files_before_download), None)
    if actual_output_file is None:
        # if the file existed before (re-)downloading, the set difference will
        # be empty
        if len(similar_files_after_download) == 1:
            # if there is only one file with a matching name, it must be the
            # right one
            actual_output_file = list(similar_files_after_download)[0]
        else:
            # otherwise, we don't know which file to use
            raise ValueError('Cannot determine the name of the downloaded '
                             'YouTube audio file because multiple similarly '
                             'named files with different extensions exist, '
                             'delete them and try again: '
                             f'{[str(p) for p in similar_files_after_download]}')

    # return the output file path
    return Path(actual_output_file)

def download_podcast_audio(episode_id, output_dir=None):

    # get the podcast audio file URL from the feed archive
    ep = get_podcast_feed_from_id(episode_id)
    url = ep['URL']

    # determine where to permanently save the file after download
    ext = ep['File'].split('.')[-1]
    output_file = f'{episode_id} Podcast.{ext}'
    if output_dir is not None:
        output_file = Path(output_dir) / output_file

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
