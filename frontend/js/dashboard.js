'use strict';

// ================================================================
// WebSocket connection
// ================================================================
const ws = new WebSocket(`ws://${window.location.host}/ws`);
const statusDot = document.getElementById('status-dot');
const statusText = document.getElementById('status-text');

ws.onopen = () => {
    statusDot.classList.remove('disconnected');
    statusText.textContent = 'Connected';
};

ws.onclose = () => {
    statusDot.classList.add('disconnected');
    statusText.textContent = 'Disconnected';
};

ws.onmessage = (event) => {
    const tags = JSON.parse(event.data);
    lastTags = tags;
    renderTags(tags);
    updateEstopIndicator(tags);

    const activeView = document.querySelector('.simulation-view.active');
    if (activeView) {
        if (activeView.id === 'sim-conveyor') updateConveyor(tags);
        else if (activeView.id === 'sim-tank') updateTank(tags);
        else if (activeView.id === 'sim-traffic') updateTrafficLight(tags);
    }

    const editorPanel = document.getElementById('editor-panel');
    if (editorPanel && editorPanel.style.display === 'block') {
        updateCanvasPowerFeedback(tags);
    }
};

// ================================================================
// State variables
// ================================================================
let lastTags = {};
let currentProgram = null;
let partPosition = 0;
let lastSensorState = false;
let lastEndLimitState = false;
let tankLevel = 30;
let lastTankSensorState = false;

// ================================================================
// Tag type detection
// ================================================================
function getTagType(name) {
    const inputs   = ['START_BUTTON','STOP_BUTTON','EMERGENCY_STOP','PART_SENSOR','END_LIMIT_SWITCH','LEVEL_SENSOR','TEMPERATURE_SENSOR'];
    const outputs  = ['MOTOR_MAIN','CONVEYOR_MOTOR','ALARM_LIGHT','VALVE_OPEN','GREEN_LAMP','RED_LAMP'];
    const timers   = ['TON_MOTOR_DELAY','TOF_MOTOR_OFF','TON_CONVEYOR_DELAY'];
    const counters = ['CTU_PART_COUNT','CTD_BATCH_COUNT'];

    if (inputs.includes(name))   return { type:'input',   label:'INPUT',   color:'#4ecdc4', icon:'eye'       };
    if (outputs.includes(name))  return { type:'output',  label:'OUTPUT',  color:'#ff6b6b', icon:'lightning' };
    if (timers.includes(name))   return { type:'timer',   label:'TIMER',   color:'#a29bfe', icon:'clock'     };
    if (counters.includes(name)) return { type:'counter', label:'COUNTER', color:'#fd79a8', icon:'hash'      };
    return                              { type:'memory',  label:'MEMORY',  color:'#f9ca24', icon:'memory'    };
}

// ================================================================
// SVG icons
// ================================================================
function getIconSVG(iconName) {
    const svgs = {
        eye: `<svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" fill="currentColor" viewBox="0 0 16 16"><path d="M10.5 8a2.5 2.5 0 1 1-5 0 2.5 2.5 0 0 1 5 0"/><path d="M0 8s3-5.5 8-5.5S16 8 16 8s-3 5.5-8 5.5S0 8 0 8m8 3.5a3.5 3.5 0 1 0 0-7 3.5 3.5 0 0 0 0 7"/></svg>`,
        lightning: `<svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" fill="currentColor" viewBox="0 0 16 16"><path d="M11.251.068a.5.5 0 0 1 .227.58L9.677 6.5H13a.5.5 0 0 1 .364.843l-8 8.5a.5.5 0 0 1-.842-.49L6.323 9.5H3a.5.5 0 0 1-.364-.843l8-8.5a.5.5 0 0 1 .615-.09z"/></svg>`,
        memory: `<svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" fill="currentColor" viewBox="0 0 16 16"><path d="M1 3a1 1 0 0 0-1 1v8a1 1 0 0 0 1 1h4.586a1 1 0 0 0 .707-.293l.353-.353a.5.5 0 0 1 .708 0l.353.353a1 1 0 0 0 .707.293H15a1 1 0 0 0 1-1V4a1 1 0 0 0-1-1zm.5 1h3a.5.5 0 0 1 .5.5v4a.5.5 0 0 1-.5.5h-3a.5.5 0 0 1-.5-.5v-4a.5.5 0 0 1 .5-.5m5 0h3a.5.5 0 0 1 .5.5v4a.5.5 0 0 1-.5.5h-3a.5.5 0 0 1-.5-.5v-4a.5.5 0 0 1 .5-.5m4.5.5a.5.5 0 0 1 .5-.5h3a.5.5 0 0 1 .5.5v4a.5.5 0 0 1-.5.5h-3a.5.5 0 0 1-.5-.5zM2 10v2H1v-2zm2 0v2H3v-2zm2 0v2H5v-2zm3 0v2H8v-2zm2 0v2h-1v-2zm2 0v2h-1v-2zm2 0v2h-1v-2z"/></svg>`,
        clock: `<svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" fill="currentColor" viewBox="0 0 16 16"><path d="M16 8A8 8 0 1 1 0 8a8 8 0 0 1 16 0M8 3.5a.5.5 0 0 0-1 0V9a.5.5 0 0 0 .252.434l3.5 2a.5.5 0 0 0 .496-.868L8 8.71z"/></svg>`,
        hash: `<svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" fill="currentColor" viewBox="0 0 16 16"><path d="M8.39 12.648a1 1 0 0 0-.015.18c0 .305.21.508.5.508.266 0 .492-.172.555-.477l.554-2.703h1.204c.421 0 .617-.234.617-.547 0-.312-.188-.53-.617-.53h-.985l.516-2.524h1.265c.43 0 .618-.227.618-.547 0-.313-.188-.524-.618-.524h-1.046l.476-2.304a1 1 0 0 0 .016-.164.51.51 0 0 0-.516-.516.54.54 0 0 0-.539.43l-.523 2.554H7.617l.477-2.304c.008-.04.015-.118.015-.164a.51.51 0 0 0-.523-.516.54.54 0 0 0-.531.43L6.53 5.484H5.414c-.43 0-.617.22-.617.532s.187.539.617.539h.906l-.515 2.523H4.609c-.421 0-.609.219-.609.531s.188.547.61.547h.976l-.516 2.492c-.008.04-.015.125-.015.18 0 .305.21.508.5.508.265 0 .492-.172.554-.477l.555-2.703h2.242zm-1-6.109h2.266l-.515 2.563H6.859l.532-2.563z"/></svg>`,
    };
    return svgs[iconName] || '';
}

// ================================================================
// Render IO tags
// ================================================================
function renderTags(tags) {
    const container = document.getElementById('tags-container');
    container.innerHTML = '';

    for (const [name, value] of Object.entries(tags)) {
        if (name.endsWith('_ACC')) continue;

        const card = document.createElement('div');
        card.className = 'io-card';

        const isTrue = (typeof value === 'boolean') ? value : (typeof value === 'number' && value > 0);
        if (isTrue) card.classList.add('active');

        const info = getTagType(name);
        const display = (typeof value === 'boolean')
            ? (value ? 'ENERGIZED' : 'OFF')
            : (typeof value === 'number' ? value.toFixed(1) : value);

        let html = `<div class="io-label">${name}</div>
                    <div class="io-icon ${info.type}" style="color:${info.color}">
                        ${getIconSVG(info.icon)} ${info.label}
                    </div>
                    <div class="indicator ${isTrue ? 'on' : ''}"></div>
                    <div class="io-value ${isTrue ? 'on' : 'off'}">${display}</div>`;

        if (info.type === 'timer' || info.type === 'counter') {
            const acc = tags[name + '_ACC'];
            if (acc !== undefined) {
                html += `<div class="io-acc">${info.type === 'timer' ? acc.toFixed(2) + ' s' : acc}</div>`;
            }
        }

        card.innerHTML = html;
        container.appendChild(card);
    }
}

// ================================================================
// E-STOP indicator
// ================================================================
function updateEstopIndicator(tags) {
    const alert = document.getElementById('estop-alert');
    alert.classList.toggle('active', !!tags['EMERGENCY_STOP']);
}

// ================================================================
// Conveyor simulation
// ================================================================
function updateConveyor(tags) {
    const motor = tags['CONVEYOR_MOTOR'];
    const part = document.getElementById('conveyor-part');
    const sensor = document.getElementById('conveyor-sensor');
    if (!part || !sensor) return;

    if (motor && !lastEndLimitState) {
        partPosition += 1.5;
        if (partPosition >= 100) {
            partPosition = 100;
            if (!lastEndLimitState) {
                lastEndLimitState = true;
                forceInput('END_LIMIT_SWITCH', true);
            }
        }
    }

    part.style.left = partPosition + '%';

    const active = partPosition > 70 && partPosition < 80;
    sensor.classList.toggle('active', active);
    if (active !== lastSensorState) {
        lastSensorState = active;
        forceInput('PART_SENSOR', active);
    }
}

// ================================================================
// Tank simulation
// ================================================================
function updateTank(tags) {
    const valve = tags['VALVE_OPEN'];
    const motor = tags['MOTOR_MAIN'];
    const levelEl = document.getElementById('tank-level');
    if (!levelEl) return;

    if (valve && !motor) tankLevel = Math.min(100, tankLevel + 0.5);
    else if (motor && !valve) tankLevel = Math.max(0, tankLevel - 0.3);

    levelEl.style.height = tankLevel + '%';

    let sensor = lastTankSensorState;
    if (!lastTankSensorState && tankLevel >= 80) sensor = true;
    else if (lastTankSensorState && tankLevel <= 20) sensor = false;

    if (sensor !== lastTankSensorState) {
        lastTankSensorState = sensor;
        forceInput('LEVEL_SENSOR', sensor);
    }

    document.getElementById('tank-valve')?.classList.toggle('open', valve);
    document.getElementById('tank-agitator')?.classList.toggle('running', motor);
}

// ================================================================
// Traffic light simulation
// ================================================================
function updateTrafficLight(tags) {
    document.getElementById('traffic-red')?.classList.toggle('on', tags['RED_LAMP']);
    document.getElementById('traffic-green')?.classList.toggle('on', tags['GREEN_LAMP']);
}

// ================================================================
// API helpers
// ================================================================
async function forceInput(tag, value) {
    try { await fetch(`/api/inputs/${tag}?value=${value}`, { method: 'POST' }); } catch {}
    await new Promise(r => setTimeout(r, 150));
    try {
        const resp = await fetch('/api/tags');
        const tags = await resp.json();
        lastTags = tags;
        renderTags(tags);
        updateEstopIndicator(tags);
    } catch { if (lastTags) renderTags(lastTags); }
}

async function pulseInput(tag, duration = 250) {
    await forceInput(tag, true);
    await new Promise(r => setTimeout(r, duration));
    await forceInput(tag, false);
    if (tag === 'STOP_BUTTON') {
        const btn = document.getElementById('btn-stop');
        if (btn) {
            btn.style.background = 'var(--danger)'; btn.style.color = '#fff';
            setTimeout(() => { btn.style.background = 'transparent'; btn.style.color = 'var(--danger)'; }, 200);
        }
    }
}

async function sendProgramToEngine(program) {
    await fetch('/api/program', { method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify(program) });
}

// ================================================================
// E‑STOP toggle
// ================================================================
function toggleEstop() {
    const current = lastTags ? lastTags['EMERGENCY_STOP'] : false;
    const newState = !current;
    forceInput('EMERGENCY_STOP', newState);
    if (newState) {
        partPosition = 0; lastEndLimitState = false; lastSensorState = false;
        const part = document.getElementById('conveyor-part');
        if (part) part.style.left = '0%';
        document.getElementById('conveyor-sensor')?.classList.remove('active');
        forceInput('PART_SENSOR', false);
        forceInput('END_LIMIT_SWITCH', false);
        tankLevel = 30; lastTankSensorState = false;
        forceInput('LEVEL_SENSOR', false);
    }
    document.getElementById('btn-emergency')?.classList.toggle('active', newState);
}

// ================================================================
// Program loading / saving / management
// ================================================================
async function loadProgram(filename) {
    try {
        const resp = await fetch(`/programs/${filename}?_=${Date.now()}`);
        if (!resp.ok) throw new Error('Not found');
        const program = await resp.json();
        currentProgram = program;
        await sendProgramToEngine(program);
        switchSimulationView(filename);
        loadProgramToCanvas(program);   // <-- NEW
    } catch (e) { console.error(e); }
}

async function loadSelectedProgram() {
    const sel = document.getElementById('program-select');
    if (!sel.value) return;
    await loadProgram(sel.value);
}

async function uploadProgram(event) {
    const file = event.target.files[0];
    if (!file) return;
    try {
        const text = await file.text();
        const program = JSON.parse(text);
        currentProgram = program;
        await sendProgramToEngine(program);
        switchSimulationView(file.name);
        loadProgramToCanvas(program);   // <-- NEW
    } catch (e) { console.error(e); alert('Invalid JSON file.'); }
    finally { event.target.value = ''; }
}

async function saveCurrentProgram() {
    if (!currentProgram) { alert('No program loaded.'); return; }
    const name = await askTag('Enter a name for this program:', 'My Program');
    if (!name) return;
    try {
        const resp = await fetch('/api/program', {
            method:'POST', headers:{'Content-Type':'application/json'},
            body: JSON.stringify({ name: name.trim(), content: currentProgram })
        });
        if (!resp.ok) throw new Error('Save failed');
        refreshSavedProgramsList();
    } catch (e) { console.error(e); alert('Save failed.'); }
}

async function fetchSavedPrograms() {
    try { return await (await fetch('/api/programs')).json(); }
    catch { return []; }
}

async function loadSavedProgram(id) {
    try {
        const resp = await fetch(`/api/programs/${id}`);
        if (!resp.ok) throw new Error('Not found');
        const prog = await resp.json();
        currentProgram = prog.content;
        await sendProgramToEngine(prog.content);
        switchSimulationView(prog.name);
        loadProgramToCanvas(prog.content);   // <-- NEW
    } catch (e) { console.error(e); }
}

async function deleteSavedProgram(id) {
    await fetch(`/api/programs/${id}`, { method:'DELETE' });
    refreshSavedProgramsList();
}

async function refreshSavedProgramsList() {
    const container = document.getElementById('saved-programs-list');
    if (!container) return;
    const programs = await fetchSavedPrograms();
    container.innerHTML = programs.length
        ? programs.map(p => `<div class="saved-program-item"><span class="saved-program-name">${p.name}</span><div class="saved-program-actions"><button class="mini-btn" onclick="loadSavedProgram(${p.id})">▶</button><button class="mini-btn delete" onclick="deleteSavedProgram(${p.id})">✕</button></div></div>`).join('')
        : '<div class="saved-program-item">No saved programs</div>';
}

function toggleSavedProgramsPanel() {
    const panel = document.getElementById('saved-programs-panel');
    if (!panel) return;
    const show = panel.style.display !== 'block';
    panel.style.display = show ? 'block' : 'none';
    if (show) refreshSavedProgramsList();
}

// ================================================================
// Simulation view switching
// ================================================================
function switchSimulationView(filename) {
    document.querySelectorAll('.simulation-view').forEach(v => v.classList.remove('active'));
    if (filename.includes('conveyor')) {
        document.getElementById('sim-conveyor')?.classList.add('active');
        partPosition = 0; lastSensorState = false; lastEndLimitState = false;
        forceInput('PART_SENSOR', false); forceInput('END_LIMIT_SWITCH', false);
    } else if (filename.includes('tank')) {
        document.getElementById('sim-tank')?.classList.add('active');
        tankLevel = 30; lastTankSensorState = false;
        forceInput('LEVEL_SENSOR', false);
    } else if (filename.includes('traffic')) {
        document.getElementById('sim-traffic')?.classList.add('active');
    }
}

// ================================================================
// Event log
// ================================================================
async function fetchEvents() {
    try {
        const events = await (await fetch('/api/events')).json();
        const container = document.getElementById('event-log-container');
        container.innerHTML = events.length
            ? events.map(e => `<div class="event-item ${e.severity ? 'severity-'+e.severity : ''}"><span class="event-timestamp">${new Date(e.timestamp).toLocaleTimeString()}</span><span>${e.message}</span></div>`).join('')
            : '<p style="color:var(--text-secondary)">No events recorded.</p>';
    } catch (e) { console.error(e); }
}

// ================================================================
// Conveyor reset
// ================================================================
function resetConveyor() {
    if (lastTags['CONVEYOR_MOTOR']) { console.warn('Reset blocked: motor running.'); return; }
    partPosition = 0;
    document.getElementById('conveyor-part')?.style.setProperty('left', '0%');
    if (lastEndLimitState) { lastEndLimitState = false; forceInput('END_LIMIT_SWITCH', false); }
    lastSensorState = false;
    document.getElementById('conveyor-sensor')?.classList.remove('active');
    forceInput('PART_SENSOR', false);
}

// ================================================================
// Modal for tag input
// ================================================================
let _tagModalResolve = null;

function askTag(question, defaultValue = '') {
    return new Promise(resolve => {
        const modal = document.getElementById('tag-modal');
        if (!modal) { resolve(prompt(question, defaultValue)); return; }
        document.getElementById('tag-modal-question').textContent = question;
        document.getElementById('tag-modal-input').value = defaultValue;
        modal.style.display = 'flex';
        document.getElementById('tag-modal-input').focus();
        _tagModalResolve = resolve;
    });
}

window.submitTagModal = () => {
    const val = document.getElementById('tag-modal-input').value.trim();
    document.getElementById('tag-modal').style.display = 'none';
    if (_tagModalResolve) { _tagModalResolve(val); _tagModalResolve = null; }
};

window.cancelTagModal = () => {
    document.getElementById('tag-modal').style.display = 'none';
    if (_tagModalResolve) { _tagModalResolve(null); _tagModalResolve = null; }
};

// ================================================================
// FREE CANVAS LADDER EDITOR
// ================================================================
let canvasBlocks = [];
let connectionMode = null;
let nextBlockId = 0;
const SVG_NS = 'http://www.w3.org/2000/svg';
let currentZoom = 1;
const ZOOM_MIN = 0.2, ZOOM_MAX = 3, ZOOM_STEP = 0.1;

function toggleEditor() {
    const panel = document.getElementById('editor-panel');
    if (!panel) return;
    const visible = panel.style.display === 'block';
    panel.style.display = visible ? 'none' : 'block';
    if (!visible) initCanvasEditor();
}

function initCanvasEditor() {
    const svg = document.getElementById('editor-canvas-svg');
    if (!svg) return;
    svg.querySelector('#canvas-blocks').innerHTML = '';
    svg.querySelector('#canvas-wires').innerHTML = '';
    canvasBlocks = []; nextBlockId = 0; connectionMode = null;
    currentZoom = 1; updateZoom();
    setupPanAndZoom();
}

function setupPanAndZoom() {
    const container = document.querySelector('.editor-canvas-container');
    if (!container || container._panInitialized) return;
    container._panInitialized = true;

    container.addEventListener('wheel', e => {
        e.preventDefault();
        currentZoom = Math.min(ZOOM_MAX, Math.max(ZOOM_MIN, currentZoom + (e.deltaY < 0 ? 1 : -1) * ZOOM_STEP));
        updateZoom();
    });

    let isPanning = false, startX, startY;
    container.addEventListener('mousedown', e => {
        if (e.target === container || e.target === document.getElementById('editor-canvas-svg')) {
            isPanning = true;
            startX = e.clientX; startY = e.clientY;
            container.style.cursor = 'grabbing';
        }
    });
    window.addEventListener('mousemove', e => {
        if (!isPanning) return;
        container.scrollLeft -= e.clientX - startX;
        container.scrollTop  -= e.clientY - startY;
        startX = e.clientX; startY = e.clientY;
    });
    window.addEventListener('mouseup', () => {
        isPanning = false;
        if (container) container.style.cursor = '';
    });
}

function updateZoom() {
    const svg = document.getElementById('editor-canvas-svg');
    if (!svg) return;
    svg.style.transform = `scale(${currentZoom})`;
    svg.style.transformOrigin = '0 0';
    const indicator = document.getElementById('zoom-indicator');
    if (indicator) indicator.textContent = Math.round(currentZoom * 100) + '%';
}

function setupDragAndDrop() {
    document.querySelectorAll('.palette-item').forEach(item => {
        item.setAttribute('draggable', 'true');
        item.addEventListener('dragstart', e => e.dataTransfer.setData('text/plain', e.target.dataset.type));
    });
}
setupDragAndDrop();
setTimeout(setupDragAndDrop, 200);

document.addEventListener('dragover', e => e.preventDefault());

document.addEventListener('drop', async e => {
    e.preventDefault();
    const canvas = document.getElementById('editor-canvas-svg');
    if (!canvas) return;
    const rect = canvas.getBoundingClientRect();
    const { clientX: mx, clientY: my } = e;
    if (mx < rect.left || mx > rect.right || my < rect.top || my > rect.bottom) return;

    const type = e.dataTransfer.getData('text/plain');
    if (!type) return;

    let x, y;
    try {
        const pt = canvas.createSVGPoint();
        pt.x = mx; pt.y = my;
        const ctm = canvas.getScreenCTM();
        if (ctm) { const gp = pt.matrixTransform(ctm.inverse()); x = gp.x; y = gp.y; }
        else { x = (mx - rect.left) / currentZoom; y = (my - rect.top) / currentZoom; }
    } catch { x = (mx - rect.left) / currentZoom; y = (my - rect.top) / currentZoom; }

    let tag, preset;
    if (type === 'TON') {
        tag = await askTag('Timer name?', 'TON_MOTOR_DELAY');
        if (!tag) return;
        preset = parseFloat(await askTag('Preset (seconds)?', '3.0'));
        if (isNaN(preset)) return;
    } else if (type === 'CTU') {
        tag = await askTag('Counter name?', 'CTU_PART_COUNT');
        if (!tag) return;
        preset = parseInt(await askTag('Preset count?', '10'));
        if (isNaN(preset)) return;
    } else {
        tag = await askTag(`Tag name for this ${type}?`, type === 'COIL' ? 'M0' : 'START_BUTTON');
        if (!tag) return;
    }
    addBlockToCanvas(type, tag.trim(), x, y, preset);
});

function addBlockToCanvas(type, tag, x, y, preset = null) {
    const svg = document.getElementById('editor-canvas-svg');
    const blocksGroup = svg.querySelector('#canvas-blocks');
    if (!blocksGroup) return;

    const id = nextBlockId++;
    const data = { id, type, tag, preset, x, y, connections: [] };
    canvasBlocks.push(data);

    const g = document.createElementNS(SVG_NS, 'g');
    g.setAttribute('class', `canvas-block ${type.toLowerCase()}`);
    g.setAttribute('transform', `translate(${x}, ${y})`);
    g.dataset.blockId = id; g.dataset.type = type; g.dataset.tag = tag;
    if (preset) g.dataset.preset = preset;
    g.style.cursor = 'move';

    const w = 160, h = 70;

    const rect = document.createElementNS(SVG_NS, 'rect');
    rect.setAttribute('width', w);
    rect.setAttribute('height', h);
    rect.setAttribute('rx', '10');
    rect.style.setProperty('fill', '#4c3a7c', 'important');
    rect.setAttribute('stroke', type === 'TON' ? '#a29bfe' : type === 'CTU' ? '#fd79a8' : type === 'COIL' ? '#f9ca24' : type === 'NC' ? '#ff6b6b' : '#4ecdc4');
    rect.setAttribute('stroke-width', '3');
    g.appendChild(rect);

    let label = type + ' ' + tag;
    if (type === 'TON') label = `TON ${tag} (${preset}s)`;
    else if (type === 'CTU') label = `CTU ${tag} (${preset})`;
    const text = document.createElementNS(SVG_NS, 'text');
    text.setAttribute('x', w / 2);
    text.setAttribute('y', h / 2 + 4);
    text.setAttribute('text-anchor', 'middle');
    text.style.setProperty('fill', '#ffffff', 'important');
    text.style.setProperty('font-size', '12px', 'important');
    text.style.setProperty('font-weight', 'bold', 'important');
    text.textContent = label;
    g.appendChild(text);

    const connPoint = document.createElementNS(SVG_NS, 'circle');
    connPoint.setAttribute('cx', w); connPoint.setAttribute('cy', h/2);
    connPoint.setAttribute('r', '9');
    connPoint.setAttribute('fill', '#b44dff');
    connPoint.setAttribute('stroke', '#ffffff'); connPoint.setAttribute('stroke-width', '2');
    connPoint.style.cursor = 'pointer';
    connPoint.addEventListener('click', e => { e.stopPropagation(); connectionMode ? finishConnection(id) : startConnection(id); });
    g.appendChild(connPoint);

    const closeBtn = document.createElementNS(SVG_NS, 'circle');
    closeBtn.setAttribute('cx', '0'); closeBtn.setAttribute('cy', '0');
    closeBtn.setAttribute('r', '12');
    closeBtn.setAttribute('fill', '#ff4d6a');
    closeBtn.setAttribute('stroke', '#ffffff'); closeBtn.setAttribute('stroke-width', '2');
    closeBtn.style.cursor = 'pointer';
    closeBtn.addEventListener('click', e => { e.stopPropagation(); removeBlock(id); });
    g.appendChild(closeBtn);

    const closeText = document.createElementNS(SVG_NS, 'text');
    closeText.setAttribute('x', '0'); closeText.setAttribute('y', '5');
    closeText.setAttribute('text-anchor', 'middle');
    closeText.style.setProperty('fill', '#ffffff', 'important');
    closeText.style.setProperty('font-size', '14px', 'important');
    closeText.style.setProperty('font-weight', 'bold', 'important');
    closeText.textContent = '×';
    g.appendChild(closeText);

    let isDragging = false, startX, startY;
    g.addEventListener('mousedown', e => {
        if (e.target === connPoint || e.target === closeBtn || e.target === closeText) return;
        isDragging = true;
        const pt = svg.createSVGPoint(); pt.x = e.clientX; pt.y = e.clientY;
        const ctm = svg.getScreenCTM();
        if (ctm) { const gp = pt.matrixTransform(ctm.inverse()); startX = gp.x - data.x; startY = gp.y - data.y; }
        else { startX = e.clientX - data.x; startY = e.clientY - data.y; }
        g.style.cursor = 'grabbing';
    });
    window.addEventListener('mousemove', e => {
        if (!isDragging) return;
        const pt = svg.createSVGPoint(); pt.x = e.clientX; pt.y = e.clientY;
        const ctm = svg.getScreenCTM();
        if (ctm) { const gp = pt.matrixTransform(ctm.inverse()); data.x = gp.x - startX; data.y = gp.y - startY; }
        else { data.x = e.clientX - startX; data.y = e.clientY - startY; }
        g.setAttribute('transform', `translate(${data.x}, ${data.y})`);
        redrawAllWires();
    });
    window.addEventListener('mouseup', () => { isDragging = false; g.style.cursor = 'move'; });

    blocksGroup.appendChild(g);
}

function connectBlocks(fromId, toId) {
    const fromBlock = canvasBlocks.find(b => b.id === fromId);
    const toBlock = canvasBlocks.find(b => b.id === toId);
    if (fromBlock && toBlock && !fromBlock.connections.includes(toId)) {
        fromBlock.connections.push(toId);
    }
}

function startConnection(fromId) {
    connectionMode = { fromBlockId: fromId };
    document.querySelectorAll('.canvas-block').forEach(b => b.style.outline = 'none');
    document.querySelector(`.canvas-block[data-block-id="${fromId}"]`)?.style.setProperty('outline', '2px solid var(--accent)');
}

function finishConnection(toId) {
    if (!connectionMode) return;
    const from = canvasBlocks.find(b => b.id === connectionMode.fromBlockId);
    const to   = canvasBlocks.find(b => b.id === toId);
    if (from && to && from.id !== to.id && !from.connections.includes(toId)) {
        from.connections.push(toId);
    }
    connectionMode = null;
    document.querySelectorAll('.canvas-block').forEach(b => b.style.outline = 'none');
    redrawAllWires();
}

function removeBlock(id) {
    canvasBlocks = canvasBlocks.filter(b => b.id !== id);
    canvasBlocks.forEach(b => b.connections = b.connections.filter(cid => cid !== id));
    document.querySelector(`.canvas-block[data-block-id="${id}"]`)?.remove();
    redrawAllWires();
}

function redrawAllWires() {
    const wiresGroup = document.getElementById('canvas-wires');
    if (!wiresGroup) return;
    wiresGroup.innerHTML = '';
    canvasBlocks.forEach(block => {
        block.connections.forEach(targetId => {
            const target = canvasBlocks.find(b => b.id === targetId);
            if (!target) return;
            const line = document.createElementNS(SVG_NS, 'line');
            line.setAttribute('x1', block.x + 160);
            line.setAttribute('y1', block.y + 35);
            line.setAttribute('x2', target.x);
            line.setAttribute('y2', target.y + 35);
            line.setAttribute('stroke', '#b44dff');
            line.setAttribute('stroke-width', '2');
            line.setAttribute('marker-end', 'url(#arrowhead)');
            wiresGroup.appendChild(line);
        });
    });
}

function clearAllCanvasBlocks() {
    canvasBlocks = []; nextBlockId = 0; connectionMode = null;
    document.getElementById('canvas-blocks').innerHTML = '';
    document.getElementById('canvas-wires').innerHTML = '';
}

function loadProgramToCanvas(program) {
    const panel = document.getElementById('editor-panel');
    if (!panel || panel.style.display !== 'block') return;

    clearAllCanvasBlocks();

    const rungs = program.rungs || [];
    let startX = 100;
    let startY = 100;
    const xSpacing = 220;
    const ySpacing = 200;

    rungs.forEach(rung => {
        const contacts = rung.contacts || [];
        let currentX = startX;
        let previousBlockId = null;
        let blockIdsInRow = [];

        function createBlock(type, tag, preset = null, x, y, parallelParentId = null) {
            addBlockToCanvas(type, tag, x, y, preset);
            const newId = canvasBlocks[canvasBlocks.length - 1].id;
            if (parallelParentId) {
                const parallelBlock = canvasBlocks.find(b => b.id === newId);
                const parentBlock = canvasBlocks.find(b => b.id === parallelParentId);
                if (parallelBlock && parentBlock) {
                    parallelBlock.dataset.parallel = 'true';
                    parallelBlock.dataset.parent = `${parentBlock.tag}-${parentBlock.type}`;
                }
            }
            return newId;
        }

        contacts.forEach(contactElement => {
            if (Array.isArray(contactElement)) {
                const mainContact = contactElement[0];
                const parallelContact = contactElement[1];
                if (!mainContact || !parallelContact) return;

                const mainId = createBlock(mainContact.type, mainContact.tag, null, currentX, startY);
                const parallelId = createBlock(parallelContact.type, parallelContact.tag, null, currentX, startY + 100, mainId);

                if (previousBlockId !== null) {
                    connectBlocks(previousBlockId, mainId);
                    connectBlocks(previousBlockId, parallelId);
                }
                blockIdsInRow.push({ type: 'parallel', ids: [mainId, parallelId] });
            } else {
                const contactId = createBlock(contactElement.type, contactElement.tag, null, currentX, startY);
                if (previousBlockId !== null) {
                    connectBlocks(previousBlockId, contactId);
                }
                blockIdsInRow.push(contactId);
                previousBlockId = contactId;
            }
            currentX += xSpacing;
        });

        let outputId = null;
        if (rung.coil) {
            outputId = createBlock('COIL', rung.coil, null, currentX, startY);
        } else if (rung.timer) {
            outputId = createBlock('TON', rung.timer.name, rung.timer.preset, currentX, startY);
        } else if (rung.counter) {
            outputId = createBlock('CTU', rung.counter.name, rung.counter.preset, currentX, startY);
        }

        if (outputId !== null) {
            const lastElement = blockIdsInRow[blockIdsInRow.length - 1];
            if (lastElement) {
                if (typeof lastElement === 'object' && lastElement.type === 'parallel') {
                    lastElement.ids.forEach(id => connectBlocks(id, outputId));
                } else {
                    connectBlocks(lastElement, outputId);
                }
            }
        }

        startY += ySpacing;
    });

    redrawAllWires();
}

function runProgramFromCanvasEditor() {
    const visited = new Set(), order = [];
    function visit(id) {
        if (visited.has(id)) return;
        visited.add(id);
        const block = canvasBlocks.find(b => b.id === id);
        if (block) block.connections.forEach(visit);
        if (block) order.push(block);
    }
    canvasBlocks.forEach(b => visit(b.id));

    const rungs = [], used = new Set();
    for (const block of order) {
        if (used.has(block.id) || !['COIL','TON','CTU'].includes(block.type)) continue;
        const rung = { contacts: [] };
        const path = [];
        (function collectInput(bid) {
            canvasBlocks.filter(b => b.connections.includes(bid) && !used.has(b.id)).forEach(pred => {
                collectInput(pred.id);
                if (!used.has(pred.id)) { path.push(pred); used.add(pred.id); }
            });
        })(block.id);
        path.reverse().forEach(b => { if (b.type === 'NO' || b.type === 'NC') rung.contacts.push({ tag: b.tag, type: b.type }); });
        if (block.type === 'TON') rung.timer = { name: block.tag, type:'TON', preset: block.preset || 3 };
        else if (block.type === 'CTU') rung.counter = { name: block.tag, type:'CTU', preset: block.preset || 10 };
        else rung.coil = block.tag;
        rungs.push(rung);
        used.add(block.id);
    }

    const program = { rungs };
    console.log('Generated program:', JSON.stringify(program, null, 2));
    fetch('/api/program', { method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify(program) })
        .then(resp => alert(resp.ok ? '✅ Program sent to PLC successfully! Close the editor and press START.' : '❌ Failed to send program.'))
        .catch(err => { console.error(err); alert('❌ Error sending program.'); });
}

function updateCanvasPowerFeedback(tags) {
    canvasBlocks.forEach(block => {
        const el = document.querySelector(`.canvas-block[data-block-id="${block.id}"]`);
        if (!el) return;
        let active = false;
        if (block.type === 'NO') active = !!tags[block.tag];
        else if (block.type === 'NC') active = !tags[block.tag];
        else if (block.type === 'COIL') {
            const inputs = canvasBlocks.filter(b => b.connections.includes(block.id));
            active = inputs.every(inp => document.querySelector(`.canvas-block[data-block-id="${inp.id}"]`)?.classList.contains('active'));
        } else if (block.type === 'TON' || block.type === 'CTU') active = !!tags[block.tag];

        el.classList.toggle('active', active);
        const rect = el.querySelector('rect');
        if (rect) rect.setAttribute('fill', active ? '#b44dff' : '#4c3a7c');
    });

    const wiresGroup = document.getElementById('canvas-wires');
    if (!wiresGroup) return;
    wiresGroup.querySelectorAll('line').forEach(line => {
        const fromX = parseFloat(line.getAttribute('x1'));
        const fromY = parseFloat(line.getAttribute('y1'));
        const fromBlock = canvasBlocks.find(b => Math.abs(b.x + 160 - fromX) < 5 && Math.abs(b.y + 35 - fromY) < 5);
        if (fromBlock) {
            const fromEl = document.querySelector(`.canvas-block[data-block-id="${fromBlock.id}"]`);
            const on = fromEl?.classList.contains('active');
            line.setAttribute('stroke', on ? '#b44dff' : 'var(--text-secondary)');
            line.setAttribute('stroke-width', on ? '3' : '2');
        }
    });
}

// ================================================================
// Initialization
// ================================================================
loadProgram('example_conveyor.json');
setInterval(fetchEvents, 3000);
fetchEvents();