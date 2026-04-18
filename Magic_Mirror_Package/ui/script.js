// ------------------- FIREBASE CLOUD CONFIG -------------------
const firebaseConfig = {
    apiKey: "AIzaSyAgKaWr6QB5oW2Bg1xccxqUfO0mrzhajZw",
    authDomain: "magic-mirror-6c421.firebaseapp.com",
    databaseURL: "https://magic-mirror-6c421-default-rtdb.firebaseio.com",
    projectId: "magic-mirror-6c421",
    storageBucket: "magic-mirror-6c421.firebasestorage.app",
    messagingSenderId: "942235812648",
    appId: "1:942235812648:web:804f3d3bd8c23fc91b461d"
};

let firebaseDB = null;
try {
    if (Object.keys(firebaseConfig).length > 0) {
        firebase.initializeApp(firebaseConfig);
        firebaseDB = firebase.database();
        console.log("Firebase initialized successfully.");
    } else {
        console.warn("Firebase config is empty. Please add your credentials. Using local fallback.");
    }
} catch(e) {
    console.error("Firebase initialization failed:", e);
}

// ------------------- STATE MANAGEMENT -------------------
let currentProfile = '';
const DEFAULT_LAYOUT = {
    'widget-todo': 'col-left',
    'widget-devices': 'col-left',
    'widget-ai': 'col-right',
    'widget-spotify': 'col-right'
};
const DAYS = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'];
const FULL_DAYS = ['Sunday', 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday'];

// ------------------- DATA LAYER (CLOUD & FALLBACK) -------------------
async function loadProfiles() {
    if (firebaseDB) {
        try {
            const snapshot = await firebaseDB.ref('magicMirrorOS').once('value');
            if (snapshot.exists()) {
                return snapshot.val();
            } else {
                const defaultData = generateDefaultData();
                await saveProfiles(defaultData);
                return defaultData;
            }
        } catch (e) {
            console.error("Firebase load failed, using local.", e);
            return loadLocalProfiles();
        }
    } else {
        return loadLocalProfiles();
    }
}

async function saveProfiles(data) {
    if (firebaseDB) {
        try {
            await firebaseDB.ref('magicMirrorOS').set(data);
            return;
        } catch (e) {
            console.error("Firebase save failed, falling back to local.", e);
        }
    }
    // Fallback
    localStorage.setItem('magicMirrorOS', JSON.stringify(data));
}

function generateDefaultData() {
    return {
        'Pavan': { layout: {...DEFAULT_LAYOUT}, tasks: {0:[], 1:[], 2:[], 3:[], 4:[], 5:[], 6:[]} },
        'Guest': { layout: {...DEFAULT_LAYOUT}, tasks: {0:[], 1:[], 2:[], 3:[], 4:[], 5:[], 6:[]} }
    };
}

function loadLocalProfiles() {
    let saved = localStorage.getItem('magicMirrorOS');
    if (!saved) {
        const defaultData = generateDefaultData();
        localStorage.setItem('magicMirrorOS', JSON.stringify(defaultData));
        return defaultData;
    }
    return typeof saved === 'string' ? JSON.parse(saved) : saved;
}

// ------------------- CLOCK & DATE -------------------
function updateClock() {
    const now = new Date();
    let hours = now.getHours();
    let minutes = now.getMinutes();
    const ampm = hours >= 12 ? 'PM' : 'AM';
    hours = hours % 12;
    hours = hours ? hours : 12; 
    minutes = minutes < 10 ? '0' + minutes : minutes;
    
    document.getElementById('clock').textContent = `${hours}:${minutes} ${ampm}`;
    
    const day = now.getDate() < 10 ? '0' + now.getDate() : now.getDate();
    const month = (now.getMonth() + 1) < 10 ? '0' + (now.getMonth() + 1) : (now.getMonth() + 1);
    
    document.getElementById('date').textContent = `${day} - ${month} - ${now.getFullYear()}`;
}
updateClock();
setInterval(updateClock, 1000);

// ------------------- PROFILE SYSTEM -------------------
window.selectProfile = async function(name) {
    currentProfile = name;
    document.getElementById('startup-screen').style.display = 'none';
    document.getElementById('os-interface').style.display = 'flex';
    document.getElementById('current-user-name').textContent = name;
    
    fetchOllamaGreeting(name);
    
    // Using Cloud Async
    await applyLayout();
    await renderCalendar();
}

window.logout = function() {
    currentProfile = '';
    if(isEditMode) toggleEditMode();
    document.getElementById('os-interface').style.display = 'none';
    document.getElementById('startup-screen').style.display = 'flex';
}

// ------------------- OLLAMA GREETING -------------------
async function fetchOllamaGreeting(name) {
    const greetingText = document.getElementById('ai-greeting');
    greetingText.textContent = "Thinking...";
    greetingText.style.opacity = '0.5';
    
    try {
        const response = await fetch('http://localhost:11434/api/generate', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({
                model: "llama3.2:1b",
                prompt: `Write a warm, very short 3-5 word greeting for ${name}. Start with "Hi ${name}". Do not use quotes or conversational intro.`,
                stream: false
            })
        });
        if (response.ok) {
            const data = await response.json();
            greetingText.textContent = data.response.trim();
        } else {
            greetingText.textContent = `Hi ${name}!`;
        }
    } catch (e) {
        greetingText.textContent = `Hi ${name}!`;
    } finally {
        greetingText.style.opacity = '1';
    }
}

// ------------------- DRAG AND DROP (EDIT MODE) -------------------
let isEditMode = false;
window.toggleEditMode = function() {
    isEditMode = !isEditMode;
    const btn = document.getElementById('edit-layout-btn');
    const os = document.getElementById('os-interface');
    const widgets = document.querySelectorAll('.widget');
    
    if (isEditMode) {
        btn.style.color = '#ef4444';
        os.classList.add('edit-mode');
        widgets.forEach(w => w.setAttribute('draggable', 'true'));
    } else {
        btn.style.color = '#0f172a';
        os.classList.remove('edit-mode');
        widgets.forEach(w => w.setAttribute('draggable', 'false'));
    }
}

// Setup Drag Events
const columns = document.querySelectorAll('.column');
const widgets = document.querySelectorAll('.widget');
let draggedItem = null;

widgets.forEach(widget => {
    widget.addEventListener('dragstart', function(e) {
        if(!isEditMode) return;
        draggedItem = this;
        setTimeout(() => this.style.opacity = '0.5', 0);
    });
    
    widget.addEventListener('dragend', async function() {
        if(!isEditMode) return;
        this.style.opacity = '1';
        draggedItem = null;
        await saveLayout();
    });
});

columns.forEach(col => {
    col.addEventListener('dragover', e => {
        if(!isEditMode) return;
        e.preventDefault();
        col.classList.add('drag-over');
    });
    
    col.addEventListener('dragleave', e => {
        col.classList.remove('drag-over');
    });
    
    col.addEventListener('drop', function(e) {
        if(!isEditMode) return;
        e.preventDefault();
        this.classList.remove('drag-over');
        if (draggedItem) {
            this.appendChild(draggedItem);
        }
    });
});

async function saveLayout() {
    if(!currentProfile) return;
    const db = await loadProfiles();
    
    widgets.forEach(w => {
        if (!db[currentProfile].layout) db[currentProfile].layout = {};
        db[currentProfile].layout[w.id] = w.parentElement.id;
    });
    await saveProfiles(db);
}

async function applyLayout() {
    const db = await loadProfiles();
    if (!db[currentProfile] || !db[currentProfile].layout) return;
    const layout = db[currentProfile].layout;
    
    for (const [widgetId, colId] of Object.entries(layout)) {
        const widget = document.getElementById(widgetId);
        const col = document.getElementById(colId);
        if (widget && col) {
            col.appendChild(widget);
        }
    }
}

// ------------------- DYNAMIC CALENDAR & TO-DO -------------------
async function renderCalendar() {
    const header = document.getElementById('calendar-header');
    const container = document.getElementById('todo-list-container');
    const db = await loadProfiles();
    if (!db[currentProfile] || !db[currentProfile].tasks) return;
    
    const userTasks = db[currentProfile].tasks;
    const todayIdx = new Date().getDay();
    
    const visualOrder = [1, 2, 3, 4, 5, 6, 0];
    header.innerHTML = '';
    
    visualOrder.forEach((dayIdx) => {
        const div = document.createElement('div');
        div.className = 'day' + (dayIdx === todayIdx ? ' active-day' : '');
        div.innerHTML = `${DAYS[dayIdx].charAt(0)}<br><span>${DAYS[dayIdx]}</span>`;
        header.appendChild(div);
    });
    
    container.innerHTML = '';
    const todayTasks = userTasks[todayIdx] || [];
    
    if(todayTasks.length === 0) {
        container.innerHTML = '<li style="color:#94a3b8; font-size:1rem;">No tasks for today. Relax!</li>';
    } else {
        todayTasks.forEach((task, i) => {
            const li = document.createElement('li');
            li.innerHTML = `
                <i class="fa-regular fa-square" onclick="window.completeTask(${todayIdx}, ${i})" style="cursor:pointer;"></i> 
                ${task}
            `;
            container.appendChild(li);
        });
    }
}

window.completeTask = async function(dayIdx, taskIdx) {
    const db = await loadProfiles();
    if (db[currentProfile].tasks[dayIdx]) {
        db[currentProfile].tasks[dayIdx].splice(taskIdx, 1);
        await saveProfiles(db);
        await renderCalendar(); 
    }
}

// ------------------- VOICE & AI NLP -------------------
const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
let recognition = null;
let isListening = false;

if (SpeechRecognition) {
    recognition = new SpeechRecognition();
    recognition.continuous = false;
    recognition.interimResults = false;
    
    recognition.onstart = () => {
        isListening = true;
        document.getElementById('mic-btn').classList.add('listening');
        document.getElementById('ai-text-input').placeholder = "Listening...";
    };
    
    recognition.onresult = (e) => {
        const text = e.results[0][0].transcript;
        document.getElementById('ai-text-input').value = text;
        submitAICommand();
    };
    
    recognition.onend = () => {
        isListening = false;
        document.getElementById('mic-btn').classList.remove('listening');
        document.getElementById('ai-text-input').placeholder = 'e.g. "Add gym to Monday"';
    };
}

window.toggleVoiceListening = function() {
    if (!recognition) {
        alert("Your browser does not support Voice Recognition.");
        return;
    }
    if (isListening) recognition.stop();
    else recognition.start();
}

window.submitAICommand = async function() {
    const input = document.getElementById('ai-text-input');
    const text = input.value.trim();
    if(!text) return;
    
    input.value = '';
    document.getElementById('ai-processing-overlay').style.display = 'flex';
    
    const systemPrompt = `You are a strict data extraction AI. Extract the intent from the user's command.
    Return ONLY standard JSON. No markdown formatting (\`\`\`), no text outside the JSON.
    Format your response EXACTLY like this:
    {"action": "add", "day_index": 1, "task": "gym"}
    
    Rules for day_index: 0=Sunday, 1=Monday, 2=Tuesday, 3=Wednesday, 4=Thursday, 5=Friday, 6=Saturday. If no day specified, output today's index (${new Date().getDay()}).
    Action must be "add" or "remove". If unknown, return {"action": "unknown"}.
    
    User Command: "${text}"`;
    
    try {
        const response = await fetch('http://localhost:11434/api/generate', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({
                model: "llama3.2:1b",
                prompt: systemPrompt,
                stream: false
            })
        });
        
        if(response.ok) {
            const data = await response.json();
            let cleanJsonStr = data.response;
            const match = data.response.match(/\{[\s\S]*?\}/);
            if (match) cleanJsonStr = match[0];
            
            const parsed = JSON.parse(cleanJsonStr);
            console.log("Parsed Intent:", parsed);
            
            if (parsed.action && parsed.action !== 'unknown') {
                await processIntent(parsed);
            } else {
                alert("I couldn't understand that command. Try 'Add [task] to [day]'.");
            }
        }
    } catch(e) {
        console.error("AI Error:", e);
        alert("Failed to reach Ollama AI.");
    } finally {
        document.getElementById('ai-processing-overlay').style.display = 'none';
    }
}

async function processIntent({ action, day_index, task }) {
    if(day_index < 0 || day_index > 6 || !task) return;
    
    const db = await loadProfiles();
    const dayTasks = db[currentProfile].tasks[day_index] || [];
    
    if (action === 'add') {
        dayTasks.push(task);
    } else if (action === 'remove') {
        const idx = dayTasks.findIndex(t => t.toLowerCase().includes(task.toLowerCase()));
        if(idx !== -1) dayTasks.splice(idx, 1);
        else alert(`Could not find task "${task}" on ${FULL_DAYS[day_index]}.`);
    }
    
    db[currentProfile].tasks[day_index] = dayTasks;
    await saveProfiles(db);
    await renderCalendar();
    
    const widgetInfo = document.getElementById('widget-todo');
    widgetInfo.style.boxShadow = "0 0 30px #0ea5e9";
    setTimeout(() => widgetInfo.style.boxShadow = "", 500);
}

// ------------------- AUTOMATIC FACE LOGIN -------------------
setInterval(async () => {
    try {
        // Poll the local Python headless API
        const response = await fetch('http://localhost:8080/');
        if (!response.ok) return;
        
        const data = await response.json();
        
        // Auto Log-In: If Python detects a registered user and we are at the startup screen
        if (data.user && !currentProfile) {
            console.log("Face detected automatically: ", data.user);
            await window.selectProfile(data.user);
        }
        
        // Auto Log-Out: If Python loses the face for > 15s and we are currently logged in
        if (!data.user && currentProfile) {
            console.log("User left camera frame. Auto logging out...");
            window.logout();
        }
    } catch(e) {
        // Face API not running, fail silently so page still works manually
    }
}, 1500);
