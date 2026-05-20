// update the clock every second
function updateClock() {
  const now = new Date();
  document.getElementById("time").textContent = now.toLocaleTimeString('en-US', { hour: 'numeric', minute: '2-digit', hour12: true });
  document.getElementById("date").textContent = now.toLocaleDateString('en-US', { weekday: 'long', month: 'long', day: 'numeric', year: 'numeric' });
}
setInterval(updateClock, 1000);
updateClock();

// handle drag and drop so widgets 
interact('.draggable').draggable({
  listeners: {
    start(event) {
      event.target.classList.add('is-dragging');
    },
    move(event) {
      const target = event.target;
      const x = (parseFloat(target.getAttribute('data-x')) || 0) + event.dx;
      const y = (parseFloat(target.getAttribute('data-y')) || 0) + event.dy;
      target.style.transform = `translate(${x}px, ${y}px)`;
      target.setAttribute('data-x', x);
      target.setAttribute('data-y', y);
    },
    end(event) {
      event.target.classList.remove('is-dragging');
      // send the new coordinates to python 
      if (window.socket && window.socket.readyState === WebSocket.OPEN) {
        window.socket.send(JSON.stringify({
          type: "layout_save",
          widget_id: event.target.id,
          x: parseFloat(event.target.getAttribute('data-x')) || 0,
          y: parseFloat(event.target.getAttribute('data-y')) || 0
        }));
      }
    }
  }
});

// visual feedback for the voice assistant 
function setAIState(state) {
  const wave = document.getElementById('waveform');
  const status = document.getElementById('ai-status-text');
  const bgWidgets = ['clock', 'calendar', 'todo', 'weather', 'spotify'];

  if (state === 'listening') {
    wave.classList.add('listening');
    status.textContent = "Listening...";
    bgWidgets.forEach(id => document.getElementById(id)?.classList.add('dimmed'));
  } else if (state === 'thinking') {
    wave.classList.remove('listening');
    status.textContent = "Thinking...";
    wave.style.filter = "hue-rotate(120deg)";
    bgWidgets.forEach(id => document.getElementById(id)?.classList.add('dimmed'));
  } else {
    wave.classList.remove('listening');
    status.textContent = 'Say "Hey Mirror"';
    wave.style.filter = "none";
    bgWidgets.forEach(id => document.getElementById(id)?.classList.remove('dimmed'));
  }
}

// todo list logic
function createNote(text) {
  const li = document.createElement('li');
  li.className = 'note-item';
  li.innerHTML = `<span class="note-text"><i class="fa-regular fa-circle"></i> ${text}</span><i class="fas fa-trash delete-btn"></i>`;

  li.querySelector('.note-text').onclick = () => li.classList.toggle('completed');

  li.querySelector('.delete-btn').onclick = () => {
    li.remove();
    if (window.socket && window.socket.readyState === WebSocket.OPEN) {
      window.socket.send(JSON.stringify({ type: "todo_delete", task: text }));
    }
  };
  return li;
}


document.getElementById('note-input').onkeypress = (e) => {
  if (e.key === 'Enter' && e.target.value.trim()) {
    const task = e.target.value.trim();
    document.getElementById('todo-list').appendChild(createNote(task));
    e.target.value = '';

    if (window.socket && window.socket.readyState === WebSocket.OPEN) {
      window.socket.send(JSON.stringify({ type: "todo_add", task: task }));
    }
  }
};

// spotify progress bar
let localProgressMs = 0, localDurationMs = 1, isPlaying = false;

function formatTime(ms) {
  const totalSecs = Math.floor(ms / 1000);
  return `${Math.floor(totalSecs / 60)}:${(totalSecs % 60).toString().padStart(2, '0')}`;
}

function updateSpotifyProgress() {
  document.getElementById("spotify-progress").style.width = `${(localProgressMs / localDurationMs) * 100}%`;
  document.getElementById("progress-time").textContent = formatTime(localProgressMs);
  document.getElementById("total-time").textContent = formatTime(localDurationMs);
}

setInterval(() => {
  if (isPlaying && localProgressMs < localDurationMs) {
    localProgressMs += 1000;
    updateSpotifyProgress();
  }
}, 1000);

// calendar grid
function renderStaticCalendar() {
  const now = new Date();
  const year = now.getFullYear();
  const month = now.getMonth();
  const today = now.getDate();

  document.getElementById('cal-month-title').textContent = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"][month];

  const firstDay = new Date(year, month, 1).getDay();
  const daysInMonth = new Date(year, month + 1, 0).getDate();
  let startOffset = firstDay === 0 ? 6 : firstDay - 1;

  const grid = document.getElementById('calendar-grid');
  grid.innerHTML = '';

  let week = document.createElement('div');
  week.className = 'calendar-row';


  for (let i = 0; i < startOffset; i++) {
    week.appendChild(document.createElement('div'));
  }

  for (let i = 1; i <= daysInMonth; i++) {
    const dayEl = document.createElement('div');
    dayEl.className = 'cal-day';
    dayEl.textContent = i;

    if (i === today) dayEl.classList.add('today');

    const dotw = new Date(year, month, i).getDay();
    if (dotw === 0 || dotw === 6) dayEl.classList.add('dim'); // dim weekends

    week.appendChild(dayEl);

    if (week.children.length === 7 || i === daysInMonth) {
      if (i === daysInMonth && week.children.length < 7) {
        const diff = 7 - week.children.length;
        for (let j = 0; j < diff; j++) week.appendChild(document.createElement('div'));
      }
      grid.appendChild(week);
      week = document.createElement('div');
      week.className = 'calendar-row';
    }
  }
}
renderStaticCalendar();
setInterval(renderStaticCalendar, 3600000); // refresh every hour

// connect to the python backend websocket
window.socket = new WebSocket("ws://127.0.0.1:8765");

window.socket.onopen = () => console.log("connected to python backend!");

window.socket.onmessage = (event) => {
  const d = JSON.parse(event.data);

  // lock screen mode
  if (d.is_locked !== undefined) {
    if (d.is_locked) {
      document.body.classList.add('locked-mode');
    } else {
      document.body.classList.remove('locked-mode');
    }
  }

  // update name
  if (d.username) {
    document.getElementById("username").textContent = d.username;
  }

  // load saved layout coordinates
  if (d.layout) {
    for (const [id, coords] of Object.entries(d.layout)) {
      const el = document.getElementById(id);
      if (el) {
        el.style.transform = `translate(${coords.x}px, ${coords.y}px)`;
        el.setAttribute('data-x', coords.x);
        el.setAttribute('data-y', coords.y);
      }
    }
  }

  if (d.temp) document.getElementById("temp").textContent = d.temp;
  if (d.ai_state) setAIState(d.ai_state);

  // show what the ai is saying
  if (d.ai_text) {
    const aiEl = document.getElementById("ai-text");
    aiEl.textContent = d.ai_text;

    if (window.aiTextTimeout) clearTimeout(window.aiTextTimeout);
    window.aiTextTimeout = setTimeout(() => {
      aiEl.textContent = "Ready for your command.";
    }, 8000);
  }

  // spotify updates
  if (d.song) {
    document.getElementById("song-name").textContent = d.song;
    document.getElementById("artist-name").textContent = d.artist || "";
    if (d.album_art) document.getElementById("album-art").src = d.album_art;
    if (d.progress_ms !== undefined) {
      localProgressMs = d.progress_ms;
      localDurationMs = d.duration_ms;
      isPlaying = d.is_playing;
      updateSpotifyProgress();
    }
  }

  // update the notes list
  if (d.todos) {
    const list = document.getElementById('todo-list');
    list.innerHTML = "";
    d.todos.forEach(task => list.appendChild(createNote(task)));
  }

  // pomodoro timer message handler
  if (d.type === "start_timer") {
    startPomodoroTimer(d.minutes);
  } else if (d.type === "stop_timer") {
    stopPomodoroTimer();
  }
};

let pomodoroInterval = null;

function stopPomodoroTimer() {
  const timerDiv = document.getElementById("pomodoro-timer");
  if (!timerDiv) return;
  if (pomodoroInterval) {
    clearInterval(pomodoroInterval);
    pomodoroInterval = null;
  }
  timerDiv.style.opacity = "0";
  setTimeout(() => {
    timerDiv.style.display = "none";
  }, 500);
  document.body.classList.remove("study-mode");
}

function playChime() {
  try {
    const audioCtx = new (window.AudioContext || window.webkitAudioContext)();
    
    const playTone = (freq, startTime, duration) => {
      const osc = audioCtx.createOscillator();
      const gain = audioCtx.createGain();
      osc.connect(gain);
      gain.connect(audioCtx.destination);
      
      osc.type = 'sine';
      osc.frequency.value = freq;
      
      gain.gain.setValueAtTime(0, startTime);
      gain.gain.linearRampToValueAtTime(0.5, startTime + 0.05);
      gain.gain.exponentialRampToValueAtTime(0.001, startTime + duration);
      
      osc.start(startTime);
      osc.stop(startTime + duration);
    };
    
    // Sleek dual-tone chime
    playTone(523.25, audioCtx.currentTime, 1.0); // C5
    playTone(659.25, audioCtx.currentTime + 0.35, 1.5); // E5
  } catch (e) {
    console.log("Audio synthesis not supported or blocked: ", e);
  }
}

function startPomodoroTimer(minutes) {
  const timerDiv = document.getElementById("pomodoro-timer");
  const timeDisplay = document.getElementById("pomodoro-time");
  
  if (!timerDiv || !timeDisplay) return;
  
  if (pomodoroInterval) {
    clearInterval(pomodoroInterval);
  }
  
  timerDiv.style.display = "block";
  timerDiv.style.opacity = "1";
  
  // Blur everything else by adding study-mode class to body
  document.body.classList.add("study-mode");
  
  let totalSeconds = minutes * 60;
  
  function updateTimerDisplay() {
    const m = Math.floor(totalSeconds / 60).toString().padStart(2, '0');
    const s = (totalSeconds % 60).toString().padStart(2, '0');
    timeDisplay.textContent = `${m}:${s}`;
  }
  
  updateTimerDisplay();
  
  pomodoroInterval = setInterval(() => {
    totalSeconds--;
    if (totalSeconds < 0) {
      clearInterval(pomodoroInterval);
      pomodoroInterval = null;
      
      // Hide widget gracefully
      timerDiv.style.opacity = "0";
      setTimeout(() => {
        timerDiv.style.display = "none";
      }, 500);
      
      // Restore standard background
      document.body.classList.remove("study-mode");
      
      // Play chime
      playChime();
    } else {
      updateTimerDisplay();
    }
  }, 1000);
}