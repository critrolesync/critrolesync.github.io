"""
Retrieve podcast RSS feeds for archival in XML format
"""

from datetime import date
from pathlib import Path
from string import ascii_lowercase
import urllib.request


feeds = {
    'critical-role': 'https://anchor.fm/s/91c7948/podcast/rss',
    'nerdist':       'http://critrole.nerdistind.libsynpro.com/rss',
    # 'geek-and-sundry': 'https://criticalrole.podbean.com/feed.xml',  # taken down as of 2020-07-08
}

# download each feed and save it as an XML file with today's date
for name, url in feeds.items():
    for letter in [''] + list(ascii_lowercase):
        filename = Path(__file__).parent / name / f'feed-{date.today()}{letter}.xml'
        if not filename.exists(): break
    try:
        urllib.request.urlretrieve(url, filename)
    except Exception as e:
        raise ValueError(f'failed to retrieve {name} feed at {url} with the following error: {e}')
