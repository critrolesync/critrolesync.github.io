"""
Retrieve RSS feeds for archival
"""

import os
import datetime
import urllib.request


feeds = {
    'critical-role': 'https://anchor.fm/s/91c7948/podcast/rss',
    'nerdist': 'http://critrole.nerdistind.libsynpro.com/rss',
    # 'geek-and-sundry': 'https://criticalrole.podbean.com/feed.xml',  # taken down as of 2020-07-08
}

# download each feed and save it as an XML file with today's date
for name, url in feeds.items():
    filename = os.path.join(name, f'feed-{datetime.date.today()}.xml')
    if not os.path.exists(filename):
        urllib.request.urlretrieve(url, filename)
