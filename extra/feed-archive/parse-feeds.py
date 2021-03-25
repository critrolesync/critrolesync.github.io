"""
This Python script reads the archived podcast feeds in XML format, extracts
relevant details, and writes them to a JSON file for easier analysis.
"""

import os
import sys
import re
import json
import urllib.parse
from datetime import datetime
import xml.etree.ElementTree as ET


def str2sec(string):
    if len(string.split(':')) == 3:
        hours, mins, secs = map(int, string.split(':'))
    elif len(string.split(':')) == 2:
        mins, secs = map(int, string.split(':'))
        hours = 0
    else:
        raise ValueError(f'string must have the form [hh:]mm:ss : {string}')
    seconds = 3600*hours + 60*mins + secs
    return seconds

def sec2str(seconds):
    if seconds < 0:
        raise ValueError(f'seconds must be nonnegative: {seconds}')
    mins, secs = divmod(seconds, 60)
    hours, mins = divmod(mins, 60)
    string = f'{hours:02d}:{mins:02d}:{secs:02d}'
    return string

def parse_feed(input_xml, output_txt=None):
    tree = ET.parse(input_xml)
    root = tree.getroot()
    namespaces = dict([node for _, node in ET.iterparse(input_xml, events=['start-ns'])])

    episodes = []
    for item in root[0].findall('item'):
        title = item.find('title').text
        match = re.match('C2E|Vox Machina Ep', title)
        if match:
            pubdate = item.find('pubDate').text
            for format in ['%a, %d %b %Y %H:%M:%S %Z', '%a, %d %b %Y %H:%M:%S %z']:
                try:
                    pubdate = datetime.strptime(pubdate, format).date()
                    break
                except:
                    pass

            duration = item.find('itunes:duration', namespaces).text
            hms = ''
            secs = ''
            try:
                # duration is the number of seconds
                hms = sec2str(int(duration))
                secs = duration
            except:
                try:
                    # duration is in HH:MM:SS form
                    secs = str2sec(duration)
                    hms = duration
                except:
                    pass

            guid = item.find('guid').text
            size = item.find('enclosure').get('length')
            filetype = item.find('enclosure').get('type')
            url = item.find('enclosure').get('url')

            urlparts = urllib.parse.unquote(url).split('/')
            file = urlparts[-1].split('?')[0]
            sponsor = None
            staging = None
            for i, part in enumerate(urlparts):
                if part == 'sponsor':
                    sponsor = urlparts[i + 1]
                if part == 'staging':
                    staging = urlparts[i + 1]

            d = {
                'Title': title,
                'GUID': guid,
                'Publication Date': str(pubdate),
                'Staging Date': staging,
                'Sponsor': sponsor,
                'HH:MM:SS': hms,
                'Seconds': int(secs),
                'Bytes': int(size),
                'File': file,
                'Type': filetype,
                # 'URL': url,
            }
            episodes.append(d)

    f = open(output_txt, 'w') if output_txt is not None else sys.stdout
    f.write(json.dumps(episodes, indent=4))
    if f is not sys.stdout:
        f.close()


if __name__ == '__main__':
    for input_dir in ['critical-role', 'nerdist']:
        output_dir = os.path.join(input_dir, 'parsed')
        if not os.path.isdir(output_dir):
            os.mkdir(output_dir)

        for filename in os.listdir(input_dir):
            match = re.fullmatch('feed-(.*)\.xml', filename)
            if match:
                date = match.group(1)
                output = f'feed-parsed-{date}.json'
                parse_feed(os.path.join(input_dir, filename), os.path.join(output_dir, output))
