/******************************************************************************
                                INITIALIZE
******************************************************************************/

var data, series, ep, debug = false

var readMoreButton = document.getElementById('read-more')
var moreText = document.getElementById('more-text')

var seriesSelect = document.getElementById('series-select')
var episodeSelect = document.getElementById('episode-select')
var hideTitles = document.getElementById('hide-titles')

var incompleteWarning = document.getElementById('incomplete-warning')
var lateTimeWarning = document.getElementById('late-time-warning')

var directionFieldset = document.getElementById('direction-fieldset')
var bitrateFieldset = document.getElementById('bitrate-fieldset')
var timesFieldset = document.getElementById('times-fieldset')

var inputTime = document.getElementById('input-time')
var inputTimeLabel = document.getElementById('input-time-label')
var outputTime = document.getElementById('output-time')
var outputTimeLabel = document.getElementById('output-time-label')

var videoLink = document.getElementById('video-link')
var podcastLink = document.getElementById('podcast-link')
var transcriptLink = document.getElementById('transcript-link')

var debugContainer = document.getElementById('debug-container')
var debugTable = document.getElementById('debug-table')

var c1ProgressBar = document.getElementById('c1-progress-bar')
var c2ProgressBar = document.getElementById('c2-progress-bar')

// load mobile-friendly tooltips
tippy('[data-tippy-content]')

// set up time picker
var picker
setupTimePicker()

// load the episode data
var requestURL = 'data.json'
var request = new XMLHttpRequest()
request.open('GET', requestURL)
request.responseType = 'json'
request.send()
request.onload = function() {
  data = request.response
  updateProgressBars()
  populateSeries()
}

/******************************************************************************
                                PAGE MANIPULATION
******************************************************************************/

function setupTimePicker() {
    picker = new Picker(inputTime, {
        format: 'HH:mm:ss',
        date: '00:00:00',
        text: {title: ''},
        headers: true,
    })

    // do not open the time picker when clicking in the input field
    inputTime.removeEventListener('focus', picker.onFocus)
    inputTime.removeEventListener('click', picker.onFocus)

    // restrict the time picker's max hour
    picker.data.hour.max = 5
    picker.render()
}

function updateProgressBars() {
    var eps, numEpisodesComplete

    // evaluate campaign 1 episode progress
    eps = data[0].episodes
    numEpisodesComplete = 0
    for (let i = 0; i < eps.length; i++) {
        if (eps[i].timestamps.length >= 2) {
            numEpisodesComplete += 1
        }
    }
    c1ProgressBar.src = `https://progress-bar.dev/${numEpisodesComplete}/?scale=${eps.length}&suffix=/${eps.length}&title=Campaign%201%20&width=250&color=666666`

    // evaluate campaign 2 episode progress
    eps = data[1].episodes
    numEpisodesComplete = 0
    for (let i = 0; i < eps.length; i++) {
        if (eps[i].timestamps.length >= 2) {
            numEpisodesComplete += 1
        }
    }
    c2ProgressBar.src = `https://progress-bar.dev/${numEpisodesComplete}/?scale=${eps.length}&suffix=/${eps.length}&title=Campaign%202%20&width=250&color=666666`
}

function populateSeries() {
    // remove all series from the series selector
    for (let i = seriesSelect.options.length-1; i >= 0; i--) {
       seriesSelect.remove(i)
    }

    // repopulate the series selector
    for (let i = 0; i < data.length; i++) {
        let option = document.createElement('option')
        option.value = i
        option.textContent = data[i].series
        if (data[i].episodes.length == 0) {
            // disable series that do not have episodes yet
            option.disabled = true
            option.textContent = '* ' + option.textContent
        }
        seriesSelect.appendChild(option)
    }

    changeSeries()
}

function changeSeries() {
    series = data[seriesSelect.value]
    populateEpisodes()
}

function populateEpisodes(keepSelectedIndex=false) {
    var selectedIndex = 0
    if (keepSelectedIndex) { selectedIndex = episodeSelect.selectedIndex }

    // remove all episodes from the episode selector
    for (let i = episodeSelect.options.length-1; i >= 0; i--) {
       episodeSelect.remove(i)
    }

    // repopulate the episode selector
    for (let i = 0; i < series.episodes.length; i++) {
        let option = document.createElement('option')
        option.value = i
        option.textContent = series.episodes[i].id
        if (!hideTitles.checked) {
            // show episode titles
            option.textContent += `: ${series.episodes[i].title}`
        }
        if (series.episodes[i].timestamps.length < 2) {
            // mark episodes that do not have timestamps yet
            option.textContent = '* ' + option.textContent
        }
        episodeSelect.appendChild(option)
    }
    episodeSelect.selectedIndex = selectedIndex

    changeEpisode()
}

function changeEpisode() {
    ep = series.episodes[episodeSelect.value]

    if (ep.timestamps.length < 2) {
        // disable form controls if timestamp data are missing
        directionFieldset.disabled = true
        bitrateFieldset.disabled = true
        timesFieldset.disabled = true

        directionFieldset.style.display = 'none'
        bitrateFieldset.style.display = 'none'
        timesFieldset.style.display = 'none'

        incompleteWarning.style.display = 'block'
    } else {
        // enable form controls if timestamp data are available
        directionFieldset.disabled = false
        bitrateFieldset.disabled = false
        timesFieldset.disabled = false

        directionFieldset.style.display = 'block'
        bitrateFieldset.style.display = 'block'
        timesFieldset.style.display = 'block'

        incompleteWarning.style.display = 'none'

        if (ep.CBR == ep.ABR) {
            // disable podcast player selector if bitrates are identical
            bitrateFieldset.disabled = true
            bitrateFieldset.style.display = 'none'
        }
    }

    resetLabels()
    updateEpisodeDebugInfo()
}

function resetLabels() {
    var direction = document.querySelector('input[name="direction"]:checked').value
    if (direction == 'podcast2youtube') {
        inputTimeLabel.textContent = 'Podcast time:'
        outputTimeLabel.textContent = 'YouTube time:'
    } else if (direction == 'youtube2podcast') {
        inputTimeLabel.textContent = 'YouTube time:'
        outputTimeLabel.textContent = 'Podcast time:'
    } else {
        console.log(`error, bad direction: ${direction}`)
        inputTimeLabel.textContent = ''
        outputTimeLabel.textContent = ''
    }

    outputTime.innerHTML = ''

    setLink(videoLink, 'Video', getUrl('youtube', ep))
    setLink(podcastLink, 'Podcast', getUrl('podcast', ep))
    setLink(transcriptLink, 'Transcript', getUrl('transcript', ep))

    lateTimeWarning.style.display = 'none'
}

function updateEpisodeDebugInfo() {
    if (debug) {
        // display debug information on page
        debugContainer.style.display = 'block'

        if (ep.timestamps.length < 2) {
            // clear timestamp link table if timestamp data are missing
            debugTable.innerHTML = ''
        } else {
            // display timestamp link table header
            debugTable.innerHTML = `
                <tr>
                    <th>Timestamp</th>
                    <th>YouTube</th>
                    <th>Podcast</th>
                <tr>`

            // print timestamps to console
            console.log(`${ep.id}: ${ep.title}`)
            console.log(ep.timestamps_columns[0], ' ', ep.timestamps_columns[1], ' ', ep.timestamps_columns[2])
            for (let i = 0; i < ep.timestamps.length; i++) {
                var [youtube_time, podcast_time, comment] = ep.timestamps[i]
                console.log(youtube_time, ' ', podcast_time, ' ', comment)

                // add timestamp links to table
                debugTable.innerHTML += `
                    <tr>
                        <td>${comment}</td>
                        <td><a href="${getUrl('youtube', ep, timeObjFromString(youtube_time))}">${youtube_time}</a></td>
                        <td><a href="${getUrl('podcast', ep, timeObjFromString(podcast_time))}">${podcast_time}</a></td>
                    </tr>`
            }
            console.log('')
        }
    } else {
        // hide debug information on page
        debugContainer.style.display = 'none'
    }
}

function readMore() {
    readMoreButton.style.display = 'none'
    moreText.style.display = 'block'
}

function readLess() {
    readMoreButton.style.display = 'inline'
    moreText.style.display = 'none'
}

function setLink(span, text, url=null, target='_blank') {
    if (url) {
        span.innerHTML = `<a href="${url}" target=${target}>${text}</a>`
    } else {
        span.innerHTML = text
    }
}

function showPicker() {
    // similar to picker.show() but first copies input time to time picker
    var timeObj = timeObjFromString(inputTime.value)
    if (timeObj && timeObj.string) {
        // current input is a valid time, so set the time picker to that value
        picker.setDate(picker.parseDate(timeObj.string))
    }
    picker.show()
}

/******************************************************************************
                                TIME OBJECTS
******************************************************************************/

function timeObjFromString(string) {
    var t = string.split(':')
    if (t.length == 3) {
        h = parseInt(t[0])
        m = parseInt(t[1])
        s = parseInt(t[2])
    } else if (t.length == 2) {
        h = 0
        m = parseInt(t[0])
        s = parseInt(t[1])
    } else {
        // console.log(`error, bad time got past form validator: ${string}`)
        return false
    }

    total = 3600*h + 60*m + s

    // make sure hours are in string even if they are zero
    string = `${h}:${String(m).padStart(2, '0')}:${String(s).padStart(2, '0')}`

    return {string: string, h: h, m: m, s: s, total: total}
}

function timeObjFromTotal(total) {
    if (isNaN(total) || total < 0) {
        console.log(`error, bad time: ${total}`)
        return false
    }
    s = Math.floor(total % 60)
    m = Math.floor(total / 60)
    h = Math.floor(m / 60)
    m = m % 60

    string = `${h}:${String(m).padStart(2, '0')}:${String(s).padStart(2, '0')}`

    return {string: string, h: h, m: m, s: s, total: total}
}

/******************************************************************************
                                TIME CONVERSION
******************************************************************************/

function parseTimestamps() {
    ts = {}
    for (let i = 0; i < ep.timestamps_columns.length; i++) {
        colLabel = ep.timestamps_columns[i]
        if (colLabel == 'comment') {
            col = ep.timestamps.map(function(value, index) { return value[i] })
        } else {
            col = ep.timestamps.map(function(value, index) { return timeObjFromString(value[i]).total })
        }
        ts[colLabel] = col
    }
    return ts
}

function isAfterEpisodeEnd(timeObj, source) {
    var ts = parseTimestamps()
    if (ts[source].length < 2) {
        console.log('error, not enough timestamps')
        return
    } else if (timeObj.total > ts[source].slice(-1)) {
        return true
    } else {
        return false
    }
}

function convertMedia(timeObj, source, dest) {

    var newTotal
    var ts = parseTimestamps()
    if (ts[source].length < 2 || ts[dest].length < 2) {
        console.log('error, not enough timestamps for interpolation')
        return
    } else if (timeObj.total < ts[source][0]) {
        // use earliest destination time
        newTotal = ts[dest][0]
    } else if (timeObj.total > ts[source].slice(-1)) {
        // use latest destination time
        newTotal = ts[dest].slice(-1)
    } else {
        newTotal = everpolate.linear(timeObj.total, ts[source], ts[dest])
    }

    return timeObjFromTotal(newTotal)
}

function convertBitrate(timeObj, oldBitrate, newBitrate) {
    // has no effect if oldBitrate == newBitrate
    var newTotal = timeObj.total * oldBitrate/newBitrate
    return timeObjFromTotal(newTotal)
}

function showConvertedTimestamp() {

    var source, dest
    var direction = document.querySelector('input[name="direction"]:checked').value
    var bitrateMode = document.querySelector('input[name="bitrate-mode"]:checked').value
    if (direction == 'podcast2youtube') {
        source = 'podcast'
        dest = 'youtube'
    } else if (direction == 'youtube2podcast') {
        source = 'youtube'
        dest = 'podcast'
    } else {
        console.log(`error, bad direction: ${direction}`)
        return
    }

    var timeObjs = {}
    timeObjs[source] = timeObjFromString(inputTime.value)

    if (isAfterEpisodeEnd(timeObjs[source], source)) {
        lateTimeWarning.style.display = 'block'
        return
    } else {
        lateTimeWarning.style.display = 'none'
    }

    // CONVERSION STEP LOGIC:
    // 1. podcast timestamps stored in data.json were obtained using a podcast
    //    player with some bitrate, given by ep.timestampsBitrate. had a
    //    different player been used, the timestamps might have differed.
    // 2. the user's selected podcast bitrate, given by ep[bitrateMode], may or
    //    may not match this.
    // 3. if they match, no extra bitrate conversion is necessary, and the
    //    timestamps can be used to straightforwardly convert between media
    //    types via linear interpolation with convertMedia(); in this case,
    //    convertBitrate() below will have no effect.
    // 4. however, if the user's podcast bitrate does not match the timestamp
    //    bitrate, podcast times must be adjusted for this difference in
    //    bitrate, either before or after media conversion, depending on the
    //    direction.
    if (source == 'podcast') {
        // podcast (user bitrate) --> podcast (timestamp bitrate) --> YouTube
        timeObjs[dest] = convertBitrate(timeObjs[source], ep[bitrateMode], ep.timestampsBitrate)
        timeObjs[dest] = convertMedia(timeObjs[dest], source, dest)

    } else if (dest == 'podcast') {
        // YouTube --> podcast (timestamp bitrate) --> podcast (user bitrate)
        timeObjs[dest] = convertMedia(timeObjs[source], source, dest)
        timeObjs[dest] = convertBitrate(timeObjs[dest], ep.timestampsBitrate, ep[bitrateMode])
    }

    if (!timeObjs[dest]) {
        console.log('error, something bad happened')
        return
    }

    setLink(outputTime, timeObjs[dest].string, getUrl(dest, ep, timeObjs[dest]))

    setLink(videoLink, `Video @ ${timeObjs['youtube'].string}`, getUrl('youtube', ep, timeObjs['youtube']))
    setLink(podcastLink, `Podcast @ ${timeObjs['podcast'].string}`, getUrl('podcast', ep, timeObjs['podcast']))
    setLink(transcriptLink, `Transcript @ ${timeObjs['youtube'].string}`, getUrl('transcript', ep, timeObjs['youtube']))
}

/******************************************************************************
                                    URLS
******************************************************************************/

function getUrl(type, ep, timeObj=null) {
    switch (type) {
        case 'youtube':
            return youtubeUrl(ep, timeObj)
        case 'podcast':
            var url = googlePodcastsUrl(ep, timeObj)
            if (!url) { url = overcastUrl(ep, timeObj) }
            return url
        case 'transcript':
            return transcriptUrl(ep, timeObj)
        default:
            return
    }
}

function youtubeUrl(ep, timeObj=null) {
    if (!ep.youtube_id) { return }

    var url = `https://www.youtube.com/watch?v=${ep.youtube_id}`
    if (ep.youtube_playlist) { url += `&list=${ep.youtube_playlist}` }
    if (timeObj) { url += `&t=${timeObj.h}h${timeObj.m}m${timeObj.s}s` }
    return url
}

function transcriptUrl(ep, timeObj=null) {
    // see searchable transcript API: https://kryogenix.org/crsearch/api.html

    var url, [, c, e, p] = ep.id.match(/C(\d+)E(\d+)(?: \(Part (\d+)\)|)/)

    if (p && p > 1) {
        // change episode parameter for multi-part episodes
        e = `${e}.${(p-1).toString().padStart(2, 0)}`
    }

    if (timeObj) {
            url = `https://kryogenix.org/crsearch/bytime.php?c=${c}&e=${e}&h=${timeObj.h}&m=${timeObj.m}&s=${timeObj.s}`
    } else {
            url = `https://kryogenix.org/crsearch/html/cr${c}-${e}.html`
    }

    return url
}

function googlePodcastsUrl(ep, timeObj=null) {
    if (!ep.google_podcasts_feed || !ep.google_podcasts_episode) { return }

    var url = `https://podcasts.google.com/?feed=${ep.google_podcasts_feed}&episode=${ep.google_podcasts_episode}`
    if (timeObj) { url += `&pe=1&pep=${Math.floor(timeObj.total)}000` }
    return url
}

function overcastUrl(ep, timeObj=null) {
    if (!ep.overcast_id) { return }

    var url = `https://overcast.fm/+${ep.overcast_id}`
    if (timeObj) { url += `/${timeObj.string}` }
    return url
}
