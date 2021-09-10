def str2sec(string):
    if len(string.split(':')) == 3:
        hours, mins, secs = map(int, string.split(':'))
    elif len(string.split(':')) == 2:
        mins, secs = map(int, string.split(':'))
        hours = 0
    else:
        raise ValueError('string must have the form [hh:]mm:ss : ' + str(string))
    seconds = 3600*hours + 60*mins + secs
    return seconds

def sec2str(seconds, format=None):
    if seconds < 0:
        raise ValueError('seconds must be nonnegative: ' + str(seconds))
    mins, secs = divmod(seconds, 60)
    hours, mins = divmod(mins, 60)
    if format == 'youtube':
        string = '%dh%02dm%02ds' % (hours, mins, secs)
    else:
        string = '%d:%02d:%02d' % (hours, mins, secs)
    return string

def fixAnchorMidroll(newAdDuration=61, oldAdDuration=0):
    '''For fixing issue #8: https://github.com/critrolesync/critrolesync.github.io/issues/8'''

    anchor_podcast_episodes = data[1]['episodes'][19:]
    for ep in anchor_podcast_episodes:
        if 'timestampsBitrate' in ep:
            # need to adjust for new bitrate
            bitrateRatio = 128/127.7
        else:
            # do need to adjust for bitrate
            bitrateRatio = 1

        print(ep['id'])
        print()
        print('                "timestamps": [')

        for i, (youtube, podcast, comment) in enumerate(ep['timestamps']):
            if i<2: # before break
                podcast_new = sec2str(str2sec(podcast)*bitrateRatio)
            else: # after break
                podcast_new = sec2str((str2sec(podcast)-oldAdDuration+newAdDuration)*bitrateRatio)
            if i<len(ep['timestamps'])-1: # include final comma
                print(f'                    ["{youtube}", "{podcast_new}", "{comment}"],')
            else: # no final comma
                print(f'                    ["{youtube}", "{podcast_new}", "{comment}"]')

        print('                ]')
        print()
        print()
