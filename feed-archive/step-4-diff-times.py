"""
Print changes in episode durations
"""

import json
from pathlib import Path
import re


for input_dir in ['critical-role']:#, 'nerdist']:
    print(f'## Podcast Feed: {input_dir}')
    print()

    feed_has_changes = False

    input_dir = Path(__file__).parent / input_dir / 'parsed'
    file_list = {}
    for file in input_dir.glob('feed-parsed-*.json'):
        match = re.fullmatch('feed-parsed-(.*)\.json', file.name)
        if match:
            date = match.group(1)
            file_list[date] = file

    dates = sorted(file_list.keys())
    old_date, new_date = dates[-2], dates[-1]
    old_feed_path = file_list[old_date]
    new_feed_path = file_list[new_date]
    with open(old_feed_path, 'r') as f:
        old_feed = json.load(f)
    with open(new_feed_path, 'r') as f:
        new_feed = json.load(f)

    for new_ep in new_feed[::-1]:
        matched = False
        title = new_ep['Title']
        for old_ep in old_feed:
            if title.strip() == old_ep['Title'].strip():
                diff_seconds = new_ep['Seconds'] - old_ep['Seconds']
                guid_changed = (new_ep['GUID'] != old_ep['GUID'])
                if diff_seconds != 0 or guid_changed:
                    print(f'* **{title.strip()}**')
                    if diff_seconds != 0:
                        print(f"  {diff_seconds:+} seconds, {old_ep['HH:MM:SS']} -> {new_ep['HH:MM:SS']}")
                    if guid_changed:
                        print('  Spotify / Google Podcast IDs may need to be updated (GUID changed)')
                    print()
                    feed_has_changes = True
                matched = True
                break
        if not matched:
            print(f'* **{title.strip()}**')
            print(f'  New episode')
            print()
            feed_has_changes = True

    if not feed_has_changes:
        print('No episode changes')
        print()
