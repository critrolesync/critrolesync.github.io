var data, ep;
var epSelect = document.getElementById('episode-select');
var inputTime = document.getElementById('input-time');
var inputTimeLabel = document.getElementById('input-time-label');
var outputTime = document.getElementById('output-time');
var outputTimeLabel = document.getElementById('output-time-label');

// load the episode data
var requestURL = 'data.json';
var request = new XMLHttpRequest();
request.open('GET', requestURL);
request.responseType = 'json';
request.send();
request.onload = function() {
  data = request.response;
  for (let i = 0; i < data.length; i++) {
      let option = document.createElement('option')
      option.value = i
      option.textContent = `${data[i].id}: ${data[i].title}`
      if (data[i].timestamps.length == 0) {
          // disable episodes that do not have timestamps yet
          option.disabled = true;
      }
      epSelect.appendChild(option)
  }
  selectEpisode()
  resetLabels()
}

function selectEpisode() {
    ep = data[epSelect.value]
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

    outputTime.textContent = ''
    outputTime.removeAttribute('href')
}

function str2sec(string) {
    var t = string.split(':');
    if (t.length == 3) {
        hours = parseInt(t[0])
        mins = parseInt(t[1])
        secs = parseInt(t[2])
    } else if (t.length == 2) {
        hours = 0
        mins = parseInt(t[0])
        secs = parseInt(t[1])
    } else {
        console.log(`error, bad time got past form validator: ${string}`);
        return false
    }
    seconds = 3600*hours + 60*mins + secs;
    return seconds
}

function sec2str(seconds, format=null) {
    if (!seconds || seconds < 0) {
        console.log(`error, bad time: ${seconds}`)
        return false
    }
    seconds = Math.floor(seconds);
    mins = Math.floor(seconds / 60);
    secs = seconds % 60;
    hours = Math.floor(mins / 60);
    mins = mins % 60;
    if (format =='youtube') {
        return `${hours}h${String(mins).padStart(2, '0')}m${String(secs).padStart(2, '0')}s`
    } else {
        return `${hours}:${String(mins).padStart(2, '0')}:${String(secs).padStart(2, '0')}`
    }
}

function parseTimestamps() {
    ts = {}
    for (let i = 0; i < ep.timestamps_columns.length; i++) {
        if (ep.timestamps_columns[i] == 'comment') {
            col = ep.timestamps.map(function(value, index) { return value[i]; });
        } else {
            col = ep.timestamps.map(function(value, index) { return str2sec(value[i]); });
        }
        ts[ep.timestamps_columns[i]] = col
    }
    return ts
}

function convertTimestamp(source, dest) {

    var seconds = str2sec(inputTime.value);

    var new_seconds, time_string;
    var ts = parseTimestamps();
    if (ts[source].length < 2 || ts[dest].length < 2) {
        console.log('error, not enough timestamps for interpolation');
        return
    } else if (seconds < ts[source][0]) {
        // use earliest destination time
        new_seconds = ts[dest][0];
    } else if (seconds > ts[source].slice(-1)) {
        // use latest destination time
        new_seconds = ts[dest].slice(-1);
    } else {
        new_seconds = everpolate.linear(seconds, ts[source], ts[dest]);
    }

    return new_seconds
}

function showConvertedTimestamp() {

    var source, dest;
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

    var new_seconds = convertTimestamp(source, dest)
    var time_string = sec2str(new_seconds);

    if (!time_string) {
        return
    }

    if (dest == 'youtube') {
        var url;
        if (ep.youtube_playlist) {
            url = `https://www.youtube.com/watch?v=${ep.youtube_id}&list=${ep.youtube_playlist}&t=${sec2str(new_seconds, format='youtube')}`
        } else {
            url = `https://www.youtube.com/watch?v=${ep.youtube_id}&t=${sec2str(new_seconds, format='youtube')}`
        }
        outputTime.href = url;
    } else {
        // disable hyperlink if not converting to YouTube time
        outputTime.removeAttribute('href')
    }

    outputTime.textContent = time_string;
}
