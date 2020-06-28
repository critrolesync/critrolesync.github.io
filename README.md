# CritRoleSync

This is a simple, unofficial web app that helps you switch back and forth
between the [Critical Role](https://critrole.com) podcast and YouTube videos.

Listening to the podcast but want to see the map Matt just pulled out? Need to
switch to audio for your daily commute? This app exists to make these tasks
easier.

Given your current playback position in one medium, it will calculate the
corresponding time in the other, accounting for differences caused by the
mid-session break, altered introductions, and variable playback rate.

Click here to start using the app: https://critrolesync.github.io

## Help Needed!

This project [needs
volunteers](https://github.com/critrolesync/critrolesync.github.io/issues/1) to
catalogue timestamps from the podcast and YouTube videos. Timestamps are stored
in [data.json](data.json) and take a form like this:

```json

"timestamps_columns":
    ["youtube", "podcast", "comment"],
"timestamps": [
    ["0:00:00", "0:00:24", "hello"],
    ["1:32:09", "1:32:21", "break start"],
    ["1:49:07", "1:32:28", "break end"],
    ["3:17:16", "3:00:25", "IITY?"]
]
```

This code says

1. The Dungeon Master greeted the audience at 0:00:00 in the video and at
   0:00:24 in the podcast.
2. The mid-session break began at 1:32:09 in the video and at 1:32:21 in the
   podcast.
3. The mid-session break ended at 1:49:07 (after 17 minutes) in the video and
   at 1:32:28 (after only 7 seconds) in the podcast.
4. The Dungeon Master signed off with "Is It Thursday Yet?" at 3:17:16 in the
   video and 3:00:25 in the podcast.

We need patient and dedicated people to review each episode and identify these
timestamps! Inspiration will be awarded for cataloging them in valid JSON
format, as in [data.json](data.json).

Presently this project is focused on game sessions from Campaign 2, but if
there's interest it could be expanded to include Campaign 1, one-shots, and
Talks Machina.

If you're interested in helping, [click
here](https://github.com/critrolesync/critrolesync.github.io/issues/1)!
