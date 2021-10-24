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
var convertFieldset = document.getElementById('convert-fieldset')

var convertFieldsetLegend = document.getElementById('convert-fieldset-legend')
var convertFieldsetLabelsRow = document.getElementById('convert-fieldset-labels-row')
var convertFieldsetTimesRow = document.getElementById('convert-fieldset-times-row')

var inputTime = document.getElementById('input-time')
var inputTimeLabel = document.getElementById('input-time-label')
var outputTime = document.getElementById('output-time')
var outputTimeLabel = document.getElementById('output-time-label')

var inputLink = document.getElementById('input-link')
var transcriptLink = document.getElementById('transcript-link')
var outputLink = document.getElementById('output-link')

var showEmbeds = document.getElementById('show-embeds')
var videoEmbed = document.getElementById('video-embed')
var podcastEmbed = document.getElementById('podcast-embed')

var debugContainer = document.getElementById('debug-container')
var debugTable = document.getElementById('debug-table')
var debugDateVerified = document.getElementById('debug-date-verified')

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

  // restore last known hide titles selection
  hideTitles.checked = (localStorage.getItem('hide-titles') == 'true')

  // restore last known podcast player selection
  var bitrateMode = localStorage.getItem('bitrate-mode')
  if (bitrateMode == 'CBR') {
      document.getElementById('cbr').checked = true
  } else if (bitrateMode == 'ABR') {
      document.getElementById('abr').checked = true
  }

  // restore last known direction
  var direction = localStorage.getItem('direction')
  if (direction == 'podcast2youtube') {
      document.getElementById('podcast2youtube').checked = true
  } else if (direction == 'youtube2podcast') {
      document.getElementById('youtube2podcast').checked = true
  }

  // restore last known input time
  var time = localStorage.getItem('input-time')
  inputTime.value = time || ''

  // restore last known show embeds selection
  showEmbeds.checked = (localStorage.getItem('show-embeds') == 'true')

  populateSeries()
  setDirectionLabels()
  showConvertedTimestamp()
}

/******************************************************************************
                                PAGE MANIPULATION
******************************************************************************/

function setupTimePicker() {
    picker = new Picker(inputTime, {
        format: 'H:mm:ss',
        date: '0:00:00',
        text: {title: ''},
        headers: true,
    })

    // do not open the time picker when clicking in the input field
    inputTime.removeEventListener('focus', picker.onFocus)
    inputTime.removeEventListener('click', picker.onFocus)

    // restrict the time picker's max hour
    picker.data.hour.max = 7
    picker.render()

    // automatically update the time input when using the picker
    function updateTimeFromPicker() {
        // similar to picker.pick() but does not close the non-inline time picker
        var value = picker.formatDate(picker.date)
        picker.setValue(value)

        // also auto-convert
        showConvertedTimestamp()
    }
    picker.grid.addEventListener('wheel', updateTimeFromPicker)
    picker.grid.addEventListener('pointerup', updateTimeFromPicker)
    picker.grid.addEventListener('touchend', updateTimeFromPicker)
}

function populateSeries(rememberSelection=true) {
    // remove all series from the series selector
    seriesSelect.innerHTML = ''

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

    // load series from local storage or default to first series
    if (rememberSelection) { seriesSelect.value = localStorage.getItem('series') || 0 }

    // populateSeries runs only on page load, which is the only time that prior
    // episode selection is restored (changing series normally resets the
    // episode selection), so here we pass rememberEpisodeSelection=true
    changeSeries(rememberEpisodeSelection=true)
}

function changeSeries(rememberEpisodeSelection=false) {
    series = data[seriesSelect.value]

    // save series selection in local storage
    localStorage.setItem('series', seriesSelect.value)

    populateEpisodes(rememberEpisodeSelection)
}

function populateEpisodes(rememberSelection=false) {
    // remove all episodes from the episode selector
    episodeSelect.innerHTML = ''

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

    // load episode from local storage or default to first episode
    if (rememberSelection) { episodeSelect.value = localStorage.getItem('episode') || 0 }

    changeEpisode()
}

function changeEpisode() {
    ep = series.episodes[episodeSelect.value]

    // save episode selection in local storage
    localStorage.setItem('episode', episodeSelect.value)

    if (ep.timestamps.length < 2) {
        // disable form controls if timestamp data are missing
        // directionFieldset.disabled = true
        bitrateFieldset.disabled = true
        convertFieldset.disabled = true

        // directionFieldset.style.display = 'none'
        bitrateFieldset.style.display = 'none'
        convertFieldsetLabelsRow.style.display = 'none'
        convertFieldsetTimesRow.style.display = 'none'
        convertFieldsetLegend.textContent = 'Links'

        incompleteWarning.style.display = 'block'
    } else {
        // enable form controls if timestamp data are available
        // directionFieldset.disabled = false
        bitrateFieldset.disabled = false
        convertFieldset.disabled = false

        // directionFieldset.style.display = 'block'
        bitrateFieldset.style.display = 'block'
        convertFieldsetLabelsRow.style.display = 'table-row'
        convertFieldsetTimesRow.style.display = 'table-row'
        convertFieldsetLegend.textContent = 'Convert time'

        incompleteWarning.style.display = 'none'

        if (!ep.CBR || !ep.ABR || !ep.timestampsBitrate || ep.CBR == ep.ABR) {
            // disable podcast player selector if bitrates are undefined or identical
            bitrateFieldset.disabled = true
            bitrateFieldset.style.display = 'none'
        }
    }

    // always hide the direction fieldset
    directionFieldset.disabled = true
    directionFieldset.style.display = 'none'

    updateEmbeds()
    updateEpisodeDebugInfo()
}

function setDirectionLabels() {
    var direction = document.querySelector('input[name="direction"]:checked').value
    if (direction == 'podcast2youtube') {
        inputTimeLabel.innerHTML = '<span class="nowrap"><i class="fa fa-headphones"></i>Podcast</span>'
        outputTimeLabel.innerHTML = '<span class="nowrap"><i class="fa fa-youtube-play"></i>YouTube</span>'
    } else if (direction == 'youtube2podcast') {
        inputTimeLabel.innerHTML = '<span class="nowrap"><i class="fa fa-youtube-play"></i>YouTube</span>'
        outputTimeLabel.innerHTML = '<span class="nowrap"><i class="fa fa-headphones"></i>Podcast</span>'
    } else {
        console.log(`error, bad direction: ${direction}`)
        inputTimeLabel.textContent = ''
        outputTimeLabel.textContent = ''
    }
}

function updateEmbeds() {
    if (showEmbeds.checked) {
        timeObjs = convertTimestamp()
        if (timeObjs) {
            fillEmbed(videoEmbed, 'youtube', ep, timeObjs['youtube'])
            fillEmbed(podcastEmbed, 'spotify', ep, timeObjs['podcast'])
        } else {
            fillEmbed(videoEmbed, 'youtube', ep)
            fillEmbed(podcastEmbed, 'spotify', ep)
        }
    } else {
        videoEmbed.innerHTML = ''
        podcastEmbed.innerHTML = ''
    }
}

function updateEpisodeDebugInfo() {
    if (debug) {
        // display debug information on page
        debugContainer.style.display = 'block'

        if (ep.timestamps.length < 2) {
            // clear debug information if timestamp data are missing
            debugDateVerified.innerHTML = ''
            debugTable.innerHTML = ''
        } else {
            // display last timestamp verification date
            debugDateVerified.innerHTML = `Timestamps last verified on ${ep.date_verified || "date unknown"}`

            // display table header for timestamp links
            var podcastHeader = 'Podcast'
            if (ep.timestampsBitrate && ep.timestampsBitrate == ep.CBR) {
                podcastHeader += ' (Chrome)'
            } else if (ep.timestampsBitrate && ep.timestampsBitrate == ep.ABR) {
                podcastHeader += ' (Firefox)'
            }
            debugTable.innerHTML = `
                <tr>
                    <th>Timestamp</th>
                    <th>YouTube</th>
                    <th>${podcastHeader}</th>
                <tr>`

            // print timestamps to console
            console.log(`${ep.id}: ${ep.title}`)
            console.log(`Timestamps last verified on ${ep.date_verified || "date unknown"}`)
            console.log(ep.timestamps_columns[0], ' ', ep.timestamps_columns[1], ' ', ep.timestamps_columns[2])
            for (let i = 0; i < ep.timestamps.length; i++) {
                var [youtube_time, podcast_time, comment] = ep.timestamps[i]
                console.log(youtube_time, ' ', podcast_time, ' ', comment)

                // add timestamp links to table
                debugTable.innerHTML += `
                    <tr>
                        <td>${comment}</td>
                        <td><a href="${getUrl('youtube', ep, timeObjFromString(youtube_time))}" target=_blank>${youtube_time}</a></td>
                        <td><a href="${getUrl('podcast', ep, timeObjFromString(podcast_time))}" target=_blank>${podcast_time}</a></td>
                    </tr>`
            }
            console.log('')
        }
    } else {
        // hide debug information on page
        debugContainer.style.display = 'none'
    }
}

function changeDirection() {
    var direction = localStorage.getItem('direction')
    if (direction == 'podcast2youtube') {
        document.getElementById('youtube2podcast').checked = true
    } else if (direction == 'youtube2podcast') {
        document.getElementById('podcast2youtube').checked = true
    }
    setDirectionLabels()
    storeDirection()
}

function storeHideTitles() {
    localStorage.setItem('hide-titles', hideTitles.checked)
}

function storeBitrateMode() {
    var bitrateMode = document.querySelector('input[name="bitrate-mode"]:checked').value
    localStorage.setItem('bitrate-mode', bitrateMode)
}

function storeDirection() {
    var direction = document.querySelector('input[name="direction"]:checked').value
    localStorage.setItem('direction', direction)
}

function storeInputTime() {
    localStorage.setItem('input-time', inputTime.value)
}

function storeShowEmbeds() {
    localStorage.setItem('show-embeds', showEmbeds.checked)
}

function toggleDebug(state=null) {
    if (state == null) {
        debug = !debug
    } else {
        debug = state
    }
    updateEpisodeDebugInfo()
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

function fillEmbed(div, type, ep, timeObj=null) {
    if (type == 'youtube') {
        var url = `https://www.youtube-nocookie.com/embed/${ep.youtube_id}`
        if (timeObj) { url += `?start=${Math.floor(timeObj.total)}` }
        div.innerHTML = `<iframe width="100%" height="232" src="${url}" frameborder="0" allow="accelerometer; autoplay; encrypted-media; gyroscope; picture-in-picture" allowfullscreen></iframe>`
    } else if (type == 'spotify') {
        var url = `https://open.spotify.com/embed/episode/${ep.spotify_id}`
        if (timeObj) { url += `?t=${Math.floor(timeObj.total)}` }
        div.innerHTML = `<iframe src="${url}" width="100%" height="232" frameBorder="0" allowfullscreen="" allow="autoplay; clipboard-write; encrypted-media; fullscreen; picture-in-picture"></iframe>`
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

function convertTimestamp() {

    // store before regex validation so that partial entries are restorable
    storeInputTime()

    timeRegEx = /^((\d:[0-5]\d)|([0-5]?\d)):([0-5]\d)$/
    if (!inputTime.value.match(timeRegEx)) { return }

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
    if (!timeObjs[source]) {
        return
    }

    if (isAfterEpisodeEnd(timeObjs[source], source)) {
        lateTimeWarning.style.display = 'table-row'
        return
    } else {
        lateTimeWarning.style.display = 'none'
    }

    // CONVERSION STEP LOGIC:
    // 1. podcast timestamps stored in data.json were obtained using a podcast
    //    player with some bitrate, given by ep.timestampsBitrate. had a
    //    different player been used, the timestamps might have differed,
    //    depending on the podcast file type.
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
    if (!ep.timestampsBitrate || !ep[bitrateMode]) {
        // do nothing about bitrate if information is not provided, which
        // usually signifies that there are no bitrate differences between
        // podcast players for this episode
        timeObjs[dest] = convertMedia(timeObjs[source], source, dest)
    } else {
        if (source == 'podcast') {
            // podcast (user bitrate) --> podcast (timestamp bitrate) --> YouTube
            timeObjs[dest] = convertBitrate(timeObjs[source], ep[bitrateMode], ep.timestampsBitrate)
            timeObjs[dest] = convertMedia(timeObjs[dest], source, dest)

        } else if (dest == 'podcast') {
            // YouTube --> podcast (timestamp bitrate) --> podcast (user bitrate)
            timeObjs[dest] = convertMedia(timeObjs[source], source, dest)
            timeObjs[dest] = convertBitrate(timeObjs[dest], ep.timestampsBitrate, ep[bitrateMode])
        }
    }

    if (!timeObjs[dest]) {
        console.log('error, something bad happened')
        return
    }

    return timeObjs
}

function showConvertedTimestamp() {
    var source, dest, linkText = {'youtube': 'YouTube', 'podcast': 'Spotify'}
    var direction = document.querySelector('input[name="direction"]:checked').value
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

    timeObjs = convertTimestamp()

    if (timeObjs) {
        outputTime.textContent = timeObjs[dest].string

        setLink(inputLink, `${linkText[source]}`, getUrl(source, ep, timeObjs[source]))
        setLink(outputLink, `${linkText[dest]}`, getUrl(dest, ep, timeObjs[dest]))
        if (getUrl('transcript', ep)) {
            setLink(transcriptLink, `Transcript`, getUrl('transcript', ep, timeObjs['youtube']))
        } else {
            setLink(transcriptLink, null)
        }
    } else {
        outputTime.textContent = '-'

        setLink(inputLink, `${linkText[source]}`, getUrl(source, ep))
        setLink(outputLink, `${linkText[dest]}`, getUrl(dest, ep))
        if (getUrl('transcript', ep)) {
            setLink(transcriptLink, `Transcript`, getUrl('transcript', ep))
        } else {
            setLink(transcriptLink, null)
        }
    }

    updateEmbeds()
}

/******************************************************************************
                                    URLS
******************************************************************************/

function getUrl(type, ep, timeObj=null) {
    switch (type) {
        case 'youtube':
            return youtubeUrl(ep, timeObj)
        case 'podcast':
            var url = spotifyUrl(ep, timeObj)
            if (!url) { url = googlePodcastsUrl(ep, timeObj) }
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

    var c, e, p
    if (ep.transcript_id) {
        [c, e] = ep.transcript_id

    } else if (ep.id.match(/C(\d+)E(\d+)/)) {
        [, c, e, p] = ep.id.match(/C(\d+)E(\d+)(?: \(Part (\d+)\)|)/)

        if (p && p > 1) {
            // change episode parameter for multi-part episodes
            e = `${e}.${(p-1).toString().padStart(2, 0)}`
        }
    } else {
        // kryogenix.org/crsearch doesn't support all episodes
        return
    }

    var url
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

function spotifyUrl(ep, timeObj=null) {
    if (!ep.spotify_id) { return }

    var url = `https://open.spotify.com/episode/${ep.spotify_id}`
    if (timeObj) { url += `?t=${Math.floor(timeObj.total)}` }
    return url
}
