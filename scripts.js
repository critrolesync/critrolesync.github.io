var data, ep
var seriesSelect = document.getElementById('series-select')
var episodeSelect = document.getElementById('episode-select')
var readMoreButton = document.getElementById("read-more")
var moreText = document.getElementById("more-text")
var inputTime = document.getElementById('input-time')
var inputTimeLabel = document.getElementById('input-time-label')
var outputTime = document.getElementById('output-time')
var outputTimeLabel = document.getElementById('output-time-label')
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
    transcriptLink.innerHTML = ''
}

function readMore() {
    readMoreButton.style.display = "none"
    moreText.style.display = "inline"
}

function readLess() {
    readMoreButton.style.display = "inline"
    moreText.style.display = "none"
}

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

function youtubeTimeQuery(time_obj) {
    return `t=${time_obj.h}h${time_obj.m}m${time_obj.s}s`
}

function transcriptTimeQuery(time_obj) {
    return `h=${time_obj.h}&m=${time_obj.m}&s=${time_obj.s}`
}

function parseTimestamps() {
    ts = {}
    for (let i = 0; i < ep.timestamps_columns.length; i++) {
        if (ep.timestamps_columns[i] == 'comment') {
            col = ep.timestamps.map(function(value, index) { return value[i] })
        } else {
            col = ep.timestamps.map(function(value, index) { return timeObjFromString(value[i]).total })
        }
        ts[ep.timestamps_columns[i]] = col
    }
    return ts
}

function convertTimeObj(time_obj, source, dest) {

    var new_total
    var ts = parseTimestamps()
    if (ts[source].length < 2 || ts[dest].length < 2) {
        console.log('error, not enough timestamps for interpolation')
        return
    } else if (time_obj.total < ts[source][0]) {
        // use earliest destination time
        new_total = ts[dest][0]
    } else if (time_obj.total > ts[source].slice(-1)) {
        // use latest destination time
        new_total = ts[dest].slice(-1)
    } else {
        new_total = everpolate.linear(time_obj.total, ts[source], ts[dest])
    }

    return timeObjFromTotal(new_total)
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

    if (dest == 'youtube') {
        var youtubeUrl
        youtubeUrl = `https://www.youtube.com/watch?v=${ep.youtube_id}&t=${timeObjs[dest].h}h${timeObjs[dest].m}m${timeObjs[dest].s}s`
        if (ep.youtube_playlist) {
            youtubeUrl += `&list=${ep.youtube_playlist}`
        }
        outputTime.innerHTML = `<a href="${youtubeUrl}" target="_blank">${timeObjs[dest].string}</a>`
    } else {
        if (ep.overcast_id) {
            var overcastUrl
            overcastUrl = `https://overcast.fm/+${ep.overcast_id}/${timeObjs[dest].string}`
            outputTime.innerHTML = `<a href="${overcastUrl}" target="_blank">${timeObjs[dest].string}</a>`
        } else {
            outputTime.innerHTML = timeObjs[dest].string
        }
    }

    var transcriptUrl, c = ep.id.split(/[CE]/)[1], e = ep.id.split(/[CE]/)[2]
    transcriptUrl = `https://kryogenix.org/crsearch/bytime.php?c=${c}&e=${e}&h=${timeObjs['youtube'].h}&m=${timeObjs['youtube'].m}&s=${timeObjs['youtube'].s}`
    transcriptLink.innerHTML = `<a href="${transcriptUrl}" target="_blank">Go!</a>`

}
