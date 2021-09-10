"""
Run a diff command on each successive pair of parsed feed JSON files.
"""

import os
import re
import difflib


for input_dir in ['critical-role', 'nerdist']:
    input_dir = os.path.join(input_dir, 'parsed')
    output_dir = os.path.join(input_dir, 'diffs')
    if not os.path.isdir(output_dir):
        os.mkdir(output_dir)

    file_list = {}
    for filename in os.listdir(input_dir):
        match = re.fullmatch('feed-parsed-(.*)\.json', filename)
        if match:
            date = match.group(1)
            file_list[date] = filename

    dates = list(file_list.keys())
    for i in range(1, len(dates)):
        old_date, new_date = dates[i - 1], dates[i]
        old_feed_path = os.path.join(input_dir, file_list[old_date])
        new_feed_path = os.path.join(input_dir, file_list[new_date])
        output_file = os.path.join(output_dir, f'feed-diff-{new_date}.diff')
        with open(old_feed_path, 'r') as f:
            old_feed = f.readlines()
        with open(new_feed_path, 'r') as f:
            new_feed = f.readlines()
        diff = difflib.unified_diff(old_feed, new_feed, fromfile=old_feed_path, tofile=new_feed_path, n=10)
        with open(output_file, 'w') as f:
            f.write(''.join(diff))
