"""
Generate a diff report for each successive pair of parsed feed JSON files
"""

import difflib
from pathlib import Path
import re


for input_dir in ['critical-role', 'nerdist']:
    input_dir = Path(input_dir) / 'parsed'
    output_dir = input_dir / 'diffs'
    output_dir.mkdir(parents=True, exist_ok=True)

    file_list = {}
    for file in input_dir.glob('feed-parsed-*.json'):
        match = re.fullmatch('feed-parsed-(.*)\.json', file.name)
        if match:
            date = match.group(1)
            file_list[date] = file

    dates = sorted(file_list.keys())
    for old_date, new_date in zip(dates[:-1], dates[1:]):
        old_feed_path = file_list[old_date]
        new_feed_path = file_list[new_date]
        output_file = output_dir / f'feed-diff-{new_date}.diff'
        with open(old_feed_path, 'r') as f:
            old_feed = f.readlines()
        with open(new_feed_path, 'r') as f:
            new_feed = f.readlines()
        diff = difflib.unified_diff(old_feed, new_feed, fromfile=str(old_feed_path), tofile=str(new_feed_path), n=10)
        with open(output_file, 'w') as f:
            f.write(''.join(diff))
