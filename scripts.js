/******************************************************************************
                                INITIALIZE
******************************************************************************/

var data, ep
var seriesSelect = document.getElementById('series-select')
var episodeSelect = document.getElementById('episode-select')
var readMoreButton = document.getElementById("read-more")
var moreText = document.getElementById("more-text")
var inputTime = document.getElementById('input-time')
var inputTimeLabel = document.getElementById('input-time-label')
var outputTime = document.getElementById('output-time')
var outputTimeLabel = document.getElementById('output-time-label')
var videoLink = document.getElementById('video-link')
var podcastLink = document.getElementById('podcast-link')
var transcriptLink = document.getElementById('transcript-link')

// load the episode data
var requestURL = 'data.json'
var request = new XMLHttpRequest()
request.open('GET', requestURL)
request.responseType = 'json'
request.send()
request.onload = function() {
  data = request.response
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
  selectSeries()
}

/******************************************************************************
                                PAGE MANIPULATION
******************************************************************************/

function selectSeries() {
    series = data[seriesSelect.value]

    // remove all episodes from the episode selector
    for (let i = episodeSelect.options.length-1; i >= 0; i--) {
       episodeSelect.remove(i)
    }

    // repopulate the episode selector
    for (let i = 0; i < series['episodes'].length; i++) {
        let option = document.createElement('option')
        option.value = i
        option.textContent = `${series['episodes'][i].id}: ${series['episodes'][i].title}`
        if (series['episodes'][i].timestamps.length == 0) {
            // disable episodes that do not have timestamps yet
            option.disabled = true
            option.textContent = '* ' + option.textContent
        }
        episodeSelect.appendChild(option)
    }

    selectEpisode()
}

function selectEpisode() {
    ep = series['episodes'][episodeSelect.value]
    resetLabels()
}

function resetLabels() {
    direction = document.querySelector('input[name="direction"]:checked').value
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

    videoLink.href = youtubeUrl(ep)
    podcastLink.href = googlePodcastsUrl(ep)
    transcriptLink.href = transcriptUrl(ep)
}

function readMore() {
    readMoreButton.style.display = "none"
    moreText.style.display = "inline"
}

function readLess() {
    readMoreButton.style.display = "inline"
    moreText.style.display = "none"
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
        console.log(`error, bad time got past form validator: ${string}`)
        return false
    }

    total = 3600*h + 60*m + s

    return {string: string, h: h, m: m, s: s, total: total}
}

function timeObjFromTotal(total) {
    if (!total || total < 0) {
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

function convertTimeObj(timeObj, source, dest) {

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
    if (bitrateMode == 'abr' && source == 'podcast' && ep.CBR && ep.ABR) {
        // if source time is from a podcast player with ABR decoding, the time
        // needs to be fixed before conversion to work with the CBR timestamps
        // stored in data.json, where the factor 127.7/128 represents the ratio
        // of the average bitrate used by ABR decoders and the constant bitrate
        // used by CBR decoders
        timeObjs[source] = timeObjFromTotal(timeObjs[source].total * ep.ABR/ep.CBR)
    }
    timeObjs[dest] = convertTimeObj(timeObjs[source], source, dest)
    if (bitrateMode == 'abr' && dest == 'podcast' && ep.CBR && ep.ABR) {
        // if destination time is for a podcast player with ABR decoding, the
        // time needs to be fixed since it was converted using CBR timestamps,
        // where the factor 128/127.7 represents the ratio of the constant
        // bitrate used by CBR decoders and the average bitrate used by ABR
        // decoders
        timeObjs[dest] = timeObjFromTotal(timeObjs[dest].total * ep.CBR/ep.ABR)
    }

    var url = getUrl(dest, ep, timeObjs[dest])
    if (url) {
        outputTime.innerHTML = `<a href="${url}" target="_blank">${timeObjs[dest].string}</a>`
    } else {
        outputTime.innerHTML = timeObjs[dest].string
    }

    videoLink.href = youtubeUrl(ep, timeObjs['youtube'])
    podcastLink.href = googlePodcastsUrl(ep, timeObjs['podcast'])
    transcriptLink.href = transcriptUrl(ep, timeObjs['youtube'])
}

/******************************************************************************
                                    URLS
******************************************************************************/

function getUrl(type, ep, timeObj=null) {
    switch (type) {
        case 'youtube':
            return youtubeUrl(ep, timeObj)
        case 'podcast':
            return googlePodcastsUrl(ep, timeObj)
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
    var url, c = ep.id.split(/[CE]/)[1], e = ep.id.split(/[CE]/)[2]
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
