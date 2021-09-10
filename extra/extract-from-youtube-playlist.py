"""
I extracted the first 100 titles and IDs from the Campaign 2 YouTube playlist
by viewing the page source, copying the contents of the variable ytInitialData
into a file called playlist.json, then running this Python script. Only the
first 100 videos can be extracted this way since the playlist is loaded
dynamically.

The playlist:
https://www.youtube.com/playlist?list=PL1tiwbzkOjQxD0jjAE7PsWoaCrs0EkBH2
"""

import json

with open('playlist.json') as f:
    x = json.load(f)
x1 = x['contents']['twoColumnBrowseResultsRenderer']['tabs'][0]['tabRenderer']['content']['sectionListRenderer']['contents'][0]['itemSectionRenderer']['contents'][0]['playlistVideoListRenderer']['contents']
for i, x2 in enumerate(x1):
    try:
        x3 = x2['playlistVideoRenderer']
    except:
        print(x2)
        raise
    videoId = x3['videoId']
    title = x3['title']['runs'][0]['text'].split('|')[0].strip()
    print('    {')
    print(f'        "id": "C2E{i+1}",')
    print(f'        "title": "{title}",')
    print(f'        "youtube_id": "{videoId}",')
    print('        "youtube_playlist": "PL1tiwbzkOjQxD0jjAE7PsWoaCrs0EkBH2",')
    print('        "timestamps_columns":')
    print('            ["youtube", "podcast", "comment"],')
    print('        "timestamps": [')
    print('        ]')
    print('    },')
