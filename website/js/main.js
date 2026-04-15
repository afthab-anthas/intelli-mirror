// 1. Clock Logic
function updateClock() {
  const now = new Date();
  document.getElementById("time").textContent = now.toLocaleTimeString('en-US', { hour: 'numeric', minute: '2-digit', hour12: true });
  document.getElementById("date").textContent = now.toLocaleDateString('en-US', { weekday: 'long', month: 'long', day: 'numeric', year: 'numeric' });
}
setInterval(updateClock, 1000); updateClock();

// 2. Persistent Dragging (Interact.js) with Glow Feedback
interact('.draggable').draggable({
  listeners: {
    start(event) { event.target.classList.add('is-dragging'); },
    move(event) {
      const target = event.target;
      const x = (parseFloat(target.getAttribute('data-x')) || 0) + event.dx;
      const y = (parseFloat(target.getAttribute('data-y')) || 0) + event.dy;
      target.style.transform = `translate(${x}px, ${y}px)`;
      target.setAttribute('data-x', x); target.setAttribute('data-y', y);
    },
    end(event) { event.target.classList.remove('is-dragging'); }
  }
});

// 3. AI Waveform States & Cinematic Focus Mode
function setAIState(state) {
  const wave = document.getElementById('waveform');
  const status = document.getElementById('ai-status-text');
  const bgWidgets = ['clock', 'calendar', 'todo', 'weather', 'spotify'];

  if (state === 'listening') {
    wave.classList.add('listening'); status.textContent = "Listening...";
    bgWidgets.forEach(id => document.getElementById(id)?.classList.add('dimmed'));
  } else if (state === 'thinking') {
    wave.classList.remove('listening'); status.textContent = "Thinking...";
    wave.style.filter = "hue-rotate(120deg)";
    bgWidgets.forEach(id => document.getElementById(id)?.classList.add('dimmed'));
  } else {
    wave.classList.remove('listening'); status.textContent = 'Say "Hey Mirror"';
    wave.style.filter = "none";
    bgWidgets.forEach(id => document.getElementById(id)?.classList.remove('dimmed'));
  }
}

// 4. Notes Logic
function createNote(text) {
  const li = document.createElement('li'); li.className = 'note-item';
  li.innerHTML = `<span class="note-text"><i class="fa-regular fa-circle"></i> ${text}</span><i class="fas fa-trash delete-btn"></i>`;
  li.querySelector('.note-text').onclick = () => li.classList.toggle('completed');
  li.querySelector('.delete-btn').onclick = () => li.remove();
  return li;
}
document.getElementById('note-input').onkeypress = (e) => {
  if (e.key === 'Enter' && e.target.value.trim()) {
    document.getElementById('todo-list').appendChild(createNote(e.target.value.trim())); e.target.value = '';
  }
};

// 5. Spotify Live Ticker Engine
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
  if (isPlaying && localProgressMs < localDurationMs) { localProgressMs += 1000; updateSpotifyProgress(); }
}, 1000);

// 6. Pure Visual Calendar Builder
function renderStaticCalendar() {
  const now = new Date(), year = now.getFullYear(), month = now.getMonth(), today = now.getDate();
  document.getElementById('cal-month-title').textContent = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"][month];

  const firstDay = new Date(year, month, 1).getDay();
  const daysInMonth = new Date(year, month + 1, 0).getDate();
  let startOffset = firstDay === 0 ? 6 : firstDay - 1;

  const grid = document.getElementById('calendar-grid'); grid.innerHTML = '';
  let week = document.createElement('div'); week.className = 'calendar-row';

  for (let i = 0; i < startOffset; i++) week.appendChild(document.createElement('div'));

  for (let i = 1; i <= daysInMonth; i++) {
    const dayEl = document.createElement('div'); dayEl.className = 'cal-day'; dayEl.textContent = i;
    if (i === today) dayEl.classList.add('today');
    const dotw = new Date(year, month, i).getDay();
    if (dotw === 0 || dotw === 6) dayEl.classList.add('dim');

    week.appendChild(dayEl);
    if (week.children.length === 7 || i === daysInMonth) {
      if (i === daysInMonth && week.children.length < 7) {
        const diff = 7 - week.children.length;
        for (let j = 0; j < diff; j++) week.appendChild(document.createElement('div'));
      }
      grid.appendChild(week);
      week = document.createElement('div'); week.className = 'calendar-row';
    }
  }
}
renderStaticCalendar(); setInterval(renderStaticCalendar, 3600000);

// 7. WebSocket Integration
const socket = new WebSocket("ws://127.0.0.1:8765");
socket.onopen = () => console.log("Connected to Python Backend!");
socket.onmessage = (event) => {
  const d = JSON.parse(event.data);
  if (d.temp) document.getElementById("temp").textContent = d.temp;
  if (d.ai_state) setAIState(d.ai_state);

  if (d.ai_text) {
    const aiEl = document.getElementById("ai-text"); aiEl.textContent = d.ai_text;
    if (window.aiTextTimeout) clearTimeout(window.aiTextTimeout);
    window.aiTextTimeout = setTimeout(() => { aiEl.textContent = "Ready for your command."; }, 8000);
  }

  if (d.song) {
    document.getElementById("song-name").textContent = d.song;
    document.getElementById("artist-name").textContent = d.artist || "";
    if (d.album_art) document.getElementById("album-art").src = d.album_art;
    if (d.progress_ms !== undefined) {
      localProgressMs = d.progress_ms; localDurationMs = d.duration_ms;
      isPlaying = d.is_playing; updateSpotifyProgress();
    }
  }

  if (d.todos) {
    const list = document.getElementById('todo-list'); list.innerHTML = "";
    d.todos.forEach(task => list.appendChild(createNote(task)));
  }
};