"""
Print changes in episode durations
"""

import json
from pathlib import Path
import re


for input_dir in ['critical-role']:#, 'nerdist']:
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
        print(title)
        for old_ep in old_feed:
            if title == old_ep['Title']:
                diff_seconds = new_ep['Seconds'] - old_ep['Seconds']
                print(f"  {diff_seconds:+} seconds, {old_ep['HH:MM:SS']} -> {new_ep['HH:MM:SS']}")
                matched = True
                break
        if not matched:
            print(f'  Could not find old episode')
        print()
