"""
Run a diff command on each successive pair of parsed feed JSON files.
"""

import os
import re
import sys


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
        old_feed = os.path.join(input_dir, file_list[old_date])
        new_feed = os.path.join(input_dir, file_list[new_date])
        output_file = os.path.join(output_dir, f'feed-diff-{new_date}.diff')
        command = f'diff -u10 {old_feed} {new_feed} > {output_file}'
        os.popen(command)
