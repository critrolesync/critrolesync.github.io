"""
Fetch Spotify episode IDs using the Spotify API

SpotifyClientCredentials requires these enviroment variables, obtained from
https://developer.spotify.com/dashboard
    - SPOTIPY_CLIENT_ID
    - SPOTIPY_CLIENT_SECRET
"""

import re
import spotipy
from spotipy.oauth2 import SpotifyClientCredentials


show_ids = {
    'critical-role': '7e8zPFBpW0DtgyrrPnt0xT',
    'nerdist': '17hv7QBlDgyil26UTIHHs6',
    # 'geek-and-sundry': '6WgOSFjdvoDOvDN37gzEdT',
}

spotify = spotipy.Spotify(auth_manager=SpotifyClientCredentials())

spotify_episodes = []
limit=50

for name, show_id in show_ids.items():
    offset=0

    while offset==0 or results['next']:
        results = spotify.show_episodes(
            show_id=show_id,
            market='US',
            limit=limit,
            offset=offset,
        )

        offset += limit

        spotify_episodes += [{'title': ep['name'], 'id': ep['id']} for ep in results['items'] if not re.match('Talks Machina|Talking|.* 4-Sided Dive', ep['name'])]

# for ep in spotify_episodes:
#     print(ep['title'])
# exit()

################################################################################

import json
from typing import Union


class CompactJSONEncoder(json.JSONEncoder):
    """A JSON Encoder that puts small containers on single lines."""

    CONTAINER_TYPES = (list, tuple, dict)
    """Container datatypes include primitives or other containers."""

    MAX_WIDTH = 70
    """Maximum width of a container that might be put on a single line."""

    MAX_ITEMS = 3 #2
    """Maximum number of items in container that might be put on single line."""

    INDENTATION_CHAR = " "

    def __init__(self, *args, **kwargs):
        # using this class without indentation is pointless
        if kwargs.get("indent") is None:
            kwargs.update({"indent": 4})
        super().__init__(*args, **kwargs)
        self.indentation_level = 0

    def encode(self, o):
        """Encode JSON object *o* with respect to single line lists."""
        if isinstance(o, (list, tuple)):
            if self._put_on_single_line(o):
                return "[" + ", ".join(self.encode(el) for el in o) + "]"
            else:
                self.indentation_level += 1
                output = [self.indent_str + self.encode(el) for el in o]
                self.indentation_level -= 1
                return "[\n" + ",\n".join(output) + "\n" + self.indent_str + "]"
        elif isinstance(o, dict):
            if o:
                if self._put_on_single_line(o):
                    return "{ " + ", ".join(f"{self.encode(k)}: {self.encode(el)}" for k, el in o.items()) + " }"
                else:
                    self.indentation_level += 1
                    output = [self.indent_str + f"{json.dumps(k)}: {self.encode(v)}" for k, v in o.items()]
                    self.indentation_level -= 1
                    return "{\n" + ",\n".join(output) + "\n" + self.indent_str + "}"
            else:
                return "{}"
        elif isinstance(o, float):  # Use scientific notation for floats, where appropiate
            return format(o, "g")
        elif isinstance(o, str):  # escape newlines
            o = o.replace("\n", "\\n")
            return f'"{o}"'
        else:
            return json.dumps(o)

    def iterencode(self, o, **kwargs):
        """Required to also work with `json.dump`."""
        return self.encode(o)

    def _put_on_single_line(self, o):
        return self._primitives_only(o) and len(o) <= self.MAX_ITEMS and len(str(o)) - 2 <= self.MAX_WIDTH

    def _primitives_only(self, o: Union[list, tuple, dict]):
        if isinstance(o, (list, tuple)):
            return not any(isinstance(el, self.CONTAINER_TYPES) for el in o)
        elif isinstance(o, dict):
            return not any(isinstance(el, self.CONTAINER_TYPES) for el in o.values())

    @property
    def indent_str(self) -> str:
        return self.INDENTATION_CHAR*(self.indentation_level*self.indent)

################################################################################

from pathlib import Path
import json
# from jsonencoder import CompactJSONEncoder


def write_data(new_data):
    with Path(__file__).parent.joinpath('../docs/data.json').open('w') as _fd:
        json.dump(new_data, _fd, indent=4, cls=CompactJSONEncoder)
        _fd.write('\n')

with Path(__file__).parent.joinpath('../docs/data.json').open() as _fd:
    data = json.load(_fd)

def get_episode_data_from_id(episode_id):
    ep = None
    for series in data:
        for episode in series['episodes']:
            if episode['id'] == episode_id:
                if ep is None:
                    ep = episode
                else:
                    raise ValueError(f'episode id "{episode_id}" is not unique')
    if ep:
        return ep
    else:
        raise ValueError(f'episode with id "{episode_id}" not found')

all_episode_ids = []
for series in data:
    for episode in series['episodes']:
        all_episode_ids += [episode['id']]

for episode_id in all_episode_ids:
    d = get_episode_data_from_id(episode_id)
    old_spotify_id = d['spotify_id']

    try:
        # we try it this way first because there is at least one example (C1E78)
        # where the title is spelled differently in the feed
        c, e = episode_id.split(' ')[0].strip('C').split('E')
        if c == '1':
            episode_title = f'Vox Machina Ep. {e} '  # include trailing space to distinguish 1, 10, 100, etc.
        elif c in ['2', '3']:
            episode_title = f'{episode_id} '         # include trailing space to distinguish 1, 10, 100, etc.
        else:
            raise NotImplementedError
    except:
        # we fall back on the title stored in data.json if the episode is not
        # part of the main campaigns
        episode_title = d['title']

    # use title substring to locate the Spotify feed entry
    spotify_ep = None
    for episode in spotify_episodes:
        if episode_title.lower() in episode['title'].lower():
            if spotify_ep is None:
                spotify_ep = episode
            else:
                print(f'WARNING: Spotify episode title substring "{episode_title}" ({episode_id}) is not unique, using first instance')
    if spotify_ep is None:
        raise ValueError(f'Spotify episode with title containing "{episode_title}" ({episode_id}) not found')

    new_spotify_id = spotify_ep['id']

    if old_spotify_id != new_spotify_id:
        print(f'Updating Spotify ID for "{episode_id}" from "{old_spotify_id}" to "{new_spotify_id}"')
        d['spotify_id'] = new_spotify_id
        d['date_verified'] = ''
    else:
        print(f'No change for "{episode_id}"')

write_data(data)
