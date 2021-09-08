import tempfile, logging, re
from pydub import AudioSegment
from typing import List, Tuple
from os import path, remove
from .matcher import Matcher

logger = logging.getLogger(__name__)

MILLISECONDS = 1000

def _slice(segment: AudioSegment, slice_length:int, slice_offset:int) -> List[AudioSegment]:
    """Slice the given audio segment in certain length (in seconds) with certain overlap / offset (in seconds)."""

    slices = []
    second = 0
    while second < segment.duration_seconds:
        end = min(
            len(segment) - 1,
            (second + slice_length) * MILLISECONDS
        )
        slices.append(segment[second * MILLISECONDS : end])
        second += slice_length + slice_offset

    return slice

def _save_slices(slices: List[AudioSegment], directory:str, fileprefix:str, segment_offset:int, fingerprint_slice_length: int, slice_overlap_length:int):
    for i in range(len(slices)):
        slice = slices[i]
        slice_offset_seconds = i * ((fingerprint_slice_length * 60) - slice_overlap_length)
        total_offset_seconds = slice_offset_seconds + segment_offset

        filename = path.join(directory, '{}{}.mp3'.format(fileprefix, total_offset_seconds))
        logger.debug('saving slice {} at second {} ({})'.format(i, total_offset_seconds, filename))
        slice.export(filename, format='mp3')

def fingerprint(file:str, prebreak_start:int, postbreak_start:int, fingerprint_length:int=60, fingerprint_slice_length:int=10, slice_overlap_length:int=60):
    """
    Generate fingerprints for the given file with respective start times before and after the break.
    The given audio file needs to be sliced for performance reasons.

    Parameters
    ----------
    file : str
        Audio file to generate fingerprints for.
    prebreak_start : int
        Timestamp where the content before the break beginns in seconds.
    postbreak : int
        Timestamp where the content after the break beginns in seconds.
    fingerprint_length : int
        Length of the fingerprint after the content starts in minutes (default: 60).
    fingerprint_slice_length : int
        Length of the slices in minutes (default: 10).
    slice_overlap_length : int
        Overlap between two slices in seconds (default: 60).
    """
    if fingerprint_slice_length * 60 <= slice_overlap_length:
        raise Exception('overlap must exceed slice')

    logger.info('fingerprinting {}'.format(file))

    audio = AudioSegment.from_file(file)
    if prebreak_start + fingerprint_length * 60 > audio.duration_seconds:
        raise Exception('prebreak position and fingerprint length exceeds total audio length')
    if postbreak_start + fingerprint_length * 60 > audio.duration_seconds:
        raise Exception('postbreak position and fingerprint length exceeds total audio length')

    with tempfile.TemporaryDirectory() as temp_dir_object:
        temp_dir = temp_dir_object.name

        logger.debug('handling pre break segment')
        logger.debug('preparing slices')
        slices = _slice(
            audio[prebreak_start * MILLISECONDS : fingerprint_length * 60 * MILLISECONDS],
            fingerprint_slice_length * 60,
            -slice_overlap_length,
        )
        logger.debug('saving slices')
        _save_slices(slices, temp_dir, 'pre', prebreak_start, fingerprint_slice_length, slice_overlap_length)

        logger.debug('handling post break segment')
        logger.debug('preparing slices')
        slices = _slice(
            audio[postbreak_start * MILLISECONDS : fingerprint_length * 60 * MILLISECONDS],
            fingerprint_slice_length * 60,
            -slice_overlap_length,
        )
        logger.debug('saving slices')
        _save_slices(slices, temp_dir, 'post', postbreak_start, fingerprint_slice_length, slice_overlap_length)

        logger.debug('fingerprinting')
        root, _ = path.splitext(file)
        with Matcher() as m:
            m.generate_fingerprints(temp_dir)
            m.store_fingerprints(root + '.tar')

    logger.info('fingerprints saved at {}'.format(root + '.tar'))

reFingerprintFile = re.compile(r'(pre|post)(\d+)(.mp3)?')
def _getPrefixAndTimestamp(name:str) -> Tuple[str, int]:
    m = reFingerprintFile.match(name)
    if m is None:
        raise Exception('could not match filename {}'.format(name))

    return m.group(0), int(m.group(1))

def realign(file:str, fingerprint_path:str, prebreak_start:int, postbreak_start:int, sample_length:int=20, sample_offset:int=55) -> Tuple[int, int]:
    """
    Realign the given audio to the given fingerprints.
    The given audio file needs to be sliced for performance reasons.

    Parameters
    ----------
    file : str
        Audio file to realign.
    fingerprint_path : str
        Fingerprint file.
    prebreak_start : int
        Timestamp where the content before the break beginns in seconds.
    postbreak : int
        Timestamp where the content after the break beginns in seconds.
    sample_length : int
        Length of each sample used for realignment in seconds (default: 20).
        Keep in mind that this should be smaller than the "slice overlap" used during fingerprint generation.
    sample_offset : int
        Offset between samples in minutes (default: 55).
        Keep in mind that this should be smaller than the "fingerprint length" used during fingerprint generation.

    Returns
    -------
    Tuple of pre- and post-break offset of the podcast.
    """
    logger.info('realigning {}'.format(file))

    audio = AudioSegment.from_file(file)
    logger.debug('preparing slices')
    slices = _slice(
        audio,
        sample_length,
        sample_offset * 60 - sample_length,
    )

    with tempfile.TemporaryDirectory() as temp_dir_object, Matcher() as m:
        temp_file = path.join(temp_dir_object.name, 'tmp.mp3')
        m.load_fingerprints(fingerprint_path)

        total_offsets:List[int] = []

        for i in range(len(slices)):
            slice = slices[i]
            if path.exists(temp_file):
                remove(temp_file)
            slice.export(temp_file, format='mp3')

            logger.debug('trying slice {} for realignment'.format(i))
            results = m.match(temp_file)
            if len(results) == 0:
                logger.debug('matching failed')
                continue

            logger.debug('match succeeded')
            results.sort(key=lambda x: x.confidence, reverse=True)
            prefix, ts_yt_base = _getPrefixAndTimestamp(results[0].name)
            ts_yt_offset = results[0].offset

            ts_yt = ts_yt_base + ts_yt_offset
            logger.debug('youtube total offset: {}+{}={}'.format(ts_yt_base, ts_yt_offset, ts_yt))
            slice_offset = sample_offset * 60 * i
            logger.debug('sample offset: {}'.format(slice_offset))


            if prefix == 'pre' and len(total_offsets) != 0:
                continue # We already have a match.
            elif prefix == 'post' and len(total_offsets) != 1:
                continue # We already have a match.

            if prefix == 'pre':
                off = slice_offset - (ts_yt - prebreak_start)
                logger.debug('pre offset of podcast is {}'.format(off))
                total_offsets.append(
                    off,
                )
            elif prefix == 'post':
                off = slice_offset - (ts_yt - postbreak_start)
                logger.debug('post offset of podcast is {}'.format(off))
                total_offsets.append(
                    off,
                )
            else:
                raise Exception('invalid prefix {}'.format(prefix))

        if len(total_offsets) != 2:
            raise Exception('could not detect offsets properly {}'.format(total_offsets))

        return total_offsets[0], total_offsets[1]
