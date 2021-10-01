"""
Parse details from archived podcast feeds and write them to JSON files
"""

from datetime import datetime
import json
from operator import mul
from pathlib import Path
import re
import sys
import urllib.parse
import xml.etree.ElementTree as ET


def str2sec(string):
    if string[0] == '-':
        sign = -1
        string = string[1:]
    else:
        sign = 1
    numbers = tuple(map(float, string.split(':')[::-1]))
    return sign * sum(map(mul, numbers, [1, 60, 3600]))

def sec2str(seconds):
    seconds = round(seconds)
    sign = '-' if seconds < 0 else ''
    seconds = abs(seconds)
    mins, secs = divmod(seconds, 60)
    hours, mins = divmod(mins, 60)
    return f'{sign}{int(round(hours)):02d}:{int(round(mins)):02d}:{int(round(secs)):02d}'

def parse_feed(input_xml, output_json=None):
    tree = ET.parse(input_xml)
    root = tree.getroot()
    namespaces = dict([node for _, node in ET.iterparse(input_xml, events=['start-ns'])])

    episodes = []
    for item in root[0].findall('item'):
        title = item.find('title').text
        smellsLikeCabbage = re.match('Talks Machina|Talking', title)
        if not smellsLikeCabbage:
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
                # duration is in HH:MM:SS form
                secs = str2sec(duration)
                hms = duration

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
                'URL': url,
            }
            episodes.append(d)

    f = open(output_json, 'w') if output_json is not None else sys.stdout
    f.write(json.dumps(episodes, indent=4))
    if f is not sys.stdout:
        f.close()


if __name__ == '__main__':
    for input_dir in ['critical-role', 'nerdist']:
        output_dir = Path(input_dir) / 'parsed'
        output_dir.mkdir(parents=True, exist_ok=True)

        for input_file in Path(input_dir).glob('feed-*.xml'):
            match = re.fullmatch('feed-(.*)\.xml', input_file.name)
            if match:
                date = match.group(1)
                output_file = f'feed-parsed-{date}.json'
                parse_feed(input_file, Path(output_dir) / output_file)
