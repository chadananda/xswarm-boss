/**
 * Demo Editor - Timeline-based demo script editor
 * For creating automated gameplay demos for videos and testing
 */

// State
const state = {
  demo: {
    name: 'untitled-demo',
    description: '',
    stage: 1,
    startChallenge: 1,
    randomSeed: 12345,
    events: []
  },
  selectedEvent: null,
  zoom: 100, // pixels per second
  playbackTime: 0,
  isPlaying: false,
  playbackInterval: null
};

// DOM Elements
const elements = {
  demoName: document.getElementById('demoName'),
  demoDescription: document.getElementById('demoDescription'),
  demoStage: document.getElementById('demoStage'),
  startChallenge: document.getElementById('startChallenge'),
  randomSeed: document.getElementById('randomSeed'),
  totalDuration: document.getElementById('totalDuration'),
  totalEvents: document.getElementById('totalEvents'),
  eventCount: document.getElementById('eventCount'),
  playBtn: document.getElementById('playBtn'),
  playbackTime: document.getElementById('playbackTime'),
  zoomLevel: document.getElementById('zoomLevel'),
  timelineRuler: document.getElementById('timelineRuler'),
  keypressTrack: document.getElementById('keypressTrack'),
  mouseTrack: document.getElementById('mouseTrack'),
  delayTrack: document.getElementById('delayTrack'),
  eventList: document.getElementById('eventList'),
  eventPanel: document.getElementById('eventPanel'),
  eventProperties: document.getElementById('eventProperties'),
  playhead: document.getElementById('playhead'),
  addEventModal: document.getElementById('addEventModal'),
  fileInput: document.getElementById('fileInput')
};

// Initialize
function init() {
  bindPropertyInputs();
  bindToolbarButtons();
  bindModalEvents();
  renderTimeline();
  renderEventList();
  updateStats();
}

// Bind property panel inputs
function bindPropertyInputs() {
  elements.demoName.addEventListener('input', () => {
    state.demo.name = elements.demoName.value;
  });

  elements.demoDescription.addEventListener('input', () => {
    state.demo.description = elements.demoDescription.value;
  });

  elements.demoStage.addEventListener('change', () => {
    state.demo.stage = parseInt(elements.demoStage.value);
  });

  elements.startChallenge.addEventListener('input', () => {
    state.demo.startChallenge = parseInt(elements.startChallenge.value) || 1;
  });

  elements.randomSeed.addEventListener('input', () => {
    state.demo.randomSeed = parseInt(elements.randomSeed.value) || 0;
  });
}

// Bind toolbar buttons
function bindToolbarButtons() {
  // Playback
  elements.playBtn.addEventListener('click', togglePlayback);
  document.getElementById('stopBtn').addEventListener('click', stopPlayback);

  // Zoom
  document.getElementById('zoomInBtn').addEventListener('click', () => setZoom(state.zoom + 25));
  document.getElementById('zoomOutBtn').addEventListener('click', () => setZoom(state.zoom - 25));

  // Add events
  document.getElementById('addKeyBtn').addEventListener('click', () => showAddModal('keypress'));
  document.getElementById('addMouseBtn').addEventListener('click', () => showAddModal('mouse'));
  document.getElementById('addDelayBtn').addEventListener('click', () => showAddModal('delay'));

  // File operations
  document.getElementById('newBtn').addEventListener('click', newDemo);
  document.getElementById('loadBtn').addEventListener('click', () => elements.fileInput.click());
  document.getElementById('saveBtn').addEventListener('click', saveDemo);
  document.getElementById('exportBtn').addEventListener('click', exportDemo);

  elements.fileInput.addEventListener('change', loadDemo);
}

// Bind modal events
function bindModalEvents() {
  document.getElementById('cancelAddEvent').addEventListener('click', hideAddModal);
  document.getElementById('confirmAddEvent').addEventListener('click', addEvent);

  // Preset buttons
  document.querySelectorAll('.preset-btn').forEach(btn => {
    btn.addEventListener('click', () => {
      const key = btn.dataset.key;
      applyKeyPreset(key);
    });
  });
}

// ============================================================
// PLAYBACK
// ============================================================

function togglePlayback() {
  if (state.isPlaying) {
    pausePlayback();
  } else {
    startPlayback();
  }
}

function startPlayback() {
  state.isPlaying = true;
  elements.playBtn.textContent = '⏸';

  const startTime = Date.now() - state.playbackTime;

  state.playbackInterval = setInterval(() => {
    state.playbackTime = Date.now() - startTime;
    updatePlayhead();

    const duration = getDuration();
    if (state.playbackTime >= duration) {
      stopPlayback();
    }
  }, 16);
}

function pausePlayback() {
  state.isPlaying = false;
  elements.playBtn.textContent = '▶';

  if (state.playbackInterval) {
    clearInterval(state.playbackInterval);
    state.playbackInterval = null;
  }
}

function stopPlayback() {
  pausePlayback();
  state.playbackTime = 0;
  updatePlayhead();
}

function updatePlayhead() {
  const x = 100 + (state.playbackTime / 1000) * state.zoom;
  elements.playhead.style.left = x + 'px';
  elements.playbackTime.textContent = formatTime(state.playbackTime);
}

// ============================================================
// ZOOM
// ============================================================

function setZoom(level) {
  state.zoom = Math.max(25, Math.min(400, level));
  elements.zoomLevel.textContent = state.zoom + '%';
  renderTimeline();
}

// ============================================================
// TIMELINE RENDERING
// ============================================================

function renderTimeline() {
  renderRuler();
  renderTracks();
}

function renderRuler() {
  const duration = Math.max(getDuration(), 10000);
  const width = (duration / 1000) * state.zoom;
  elements.timelineRuler.style.width = width + 'px';
  elements.timelineRuler.innerHTML = '';

  // Major marks every second, minor every 500ms
  for (let ms = 0; ms <= duration; ms += 500) {
    const mark = document.createElement('div');
    mark.className = 'ruler-mark' + (ms % 1000 === 0 ? ' major' : '');
    mark.style.left = (ms / 1000) * state.zoom + 'px';

    if (ms % 1000 === 0) {
      mark.textContent = formatTimeShort(ms);
    }

    elements.timelineRuler.appendChild(mark);
  }
}

function renderTracks() {
  // Clear tracks
  elements.keypressTrack.innerHTML = '';
  elements.mouseTrack.innerHTML = '';
  elements.delayTrack.innerHTML = '';

  // Render each event
  state.demo.events.forEach((event, index) => {
    const el = createTimelineEvent(event, index);

    switch (event.type) {
      case 'keypress':
        elements.keypressTrack.appendChild(el);
        break;
      case 'mouse':
        elements.mouseTrack.appendChild(el);
        break;
      case 'delay':
        elements.delayTrack.appendChild(el);
        break;
    }
  });
}

function createTimelineEvent(event, index) {
  const el = document.createElement('div');
  el.className = 'timeline-event ' + event.type;
  el.dataset.index = index;

  // Position
  const x = (event.timestamp / 1000) * state.zoom;
  el.style.left = x + 'px';

  // Width for delays
  if (event.type === 'delay' && event.duration) {
    const width = (event.duration / 1000) * state.zoom;
    el.style.width = Math.max(width, 60) + 'px';
  }

  // Content
  el.textContent = getEventLabel(event);

  // Selection
  if (state.selectedEvent === index) {
    el.classList.add('selected');
  }

  // Click handler
  el.addEventListener('click', () => selectEvent(index));

  return el;
}

function getEventLabel(event) {
  switch (event.type) {
    case 'keypress':
      return event.key || 'Key';
    case 'mouse':
      return event.action || 'Mouse';
    case 'delay':
      return event.duration ? `${event.duration}ms` : 'Delay';
    default:
      return event.type;
  }
}

// ============================================================
// EVENT LIST
// ============================================================

function renderEventList() {
  const sorted = [...state.demo.events]
    .map((e, i) => ({ ...e, originalIndex: i }))
    .sort((a, b) => a.timestamp - b.timestamp);

  elements.eventCount.textContent = `(${sorted.length})`;

  elements.eventList.innerHTML = sorted.map(event => `
    <div class="event-item ${event.type} ${state.selectedEvent === event.originalIndex ? 'selected' : ''}"
         data-index="${event.originalIndex}">
      <span class="event-time">${formatTime(event.timestamp)}</span>
      <span class="event-type">${event.type}</span>
      <span class="event-value">${getEventDescription(event)}</span>
      <div class="event-actions">
        <button data-action="duplicate" title="Duplicate">⧉</button>
        <button data-action="delete" title="Delete">✕</button>
      </div>
    </div>
  `).join('');

  // Bind click handlers
  elements.eventList.querySelectorAll('.event-item').forEach(el => {
    el.addEventListener('click', (e) => {
      if (e.target.closest('.event-actions')) return;
      selectEvent(parseInt(el.dataset.index));
    });
  });

  // Bind action buttons
  elements.eventList.querySelectorAll('[data-action]').forEach(btn => {
    btn.addEventListener('click', (e) => {
      e.stopPropagation();
      const index = parseInt(btn.closest('.event-item').dataset.index);
      const action = btn.dataset.action;

      if (action === 'delete') {
        deleteEvent(index);
      } else if (action === 'duplicate') {
        duplicateEvent(index);
      }
    });
  });
}

function getEventDescription(event) {
  switch (event.type) {
    case 'keypress':
      return event.key || 'Unknown key';
    case 'mouse':
      let desc = event.action || 'move';
      if (event.x !== undefined && event.y !== undefined) {
        desc += ` (${event.x}, ${event.y})`;
      }
      return desc;
    case 'delay':
      return `${event.duration || 0}ms${event.reason ? ' - ' + event.reason : ''}`;
    default:
      return '';
  }
}

// ============================================================
// EVENT SELECTION & EDITING
// ============================================================

function selectEvent(index) {
  state.selectedEvent = index;
  renderTimeline();
  renderEventList();
  renderEventProperties();
}

function renderEventProperties() {
  if (state.selectedEvent === null || !state.demo.events[state.selectedEvent]) {
    elements.eventProperties.innerHTML = '<p class="placeholder">Select an event to edit</p>';
    return;
  }

  const event = state.demo.events[state.selectedEvent];

  elements.eventProperties.innerHTML = `
    <div class="form-group">
      <label>Timestamp (ms)</label>
      <input type="number" id="editTimestamp" value="${event.timestamp}" min="0" step="100">
    </div>
    ${renderEventTypeFields(event)}
    <button class="btn btn-primary" id="updateEventBtn" style="width: 100%; margin-top: 1rem;">
      Update Event
    </button>
  `;

  // Bind update
  document.getElementById('updateEventBtn').addEventListener('click', updateSelectedEvent);
}

function renderEventTypeFields(event) {
  switch (event.type) {
    case 'keypress':
      const parts = parseKey(event.key);
      return `
        <div class="form-group">
          <label>Key Combination</label>
          <div class="key-combo">
            <label><input type="checkbox" id="editSuper" ${parts.super ? 'checked' : ''}> Super</label>
            <label><input type="checkbox" id="editShift" ${parts.shift ? 'checked' : ''}> Shift</label>
            <label><input type="checkbox" id="editCtrl" ${parts.ctrl ? 'checked' : ''}> Ctrl</label>
            <label><input type="checkbox" id="editAlt" ${parts.alt ? 'checked' : ''}> Alt</label>
          </div>
          <input type="text" id="editKeyValue" value="${parts.key}" placeholder="e.g., Return, q">
        </div>
      `;

    case 'mouse':
      return `
        <div class="form-group">
          <label>Action</label>
          <select id="editMouseAction">
            <option value="move" ${event.action === 'move' ? 'selected' : ''}>Move</option>
            <option value="click" ${event.action === 'click' ? 'selected' : ''}>Click</option>
            <option value="erratic" ${event.action === 'erratic' ? 'selected' : ''}>Erratic</option>
          </select>
        </div>
        <div class="form-group">
          <label>Position</label>
          <div class="position-inputs">
            <input type="number" id="editMouseX" placeholder="X" value="${event.x || ''}">
            <input type="number" id="editMouseY" placeholder="Y" value="${event.y || ''}">
          </div>
        </div>
        <div class="form-group">
          <label>Duration (ms)</label>
          <input type="number" id="editMouseDuration" value="${event.duration || 500}">
        </div>
      `;

    case 'delay':
      return `
        <div class="form-group">
          <label>Duration (ms)</label>
          <input type="number" id="editDelayDuration" value="${event.duration || 1000}">
        </div>
        <div class="form-group">
          <label>Reason</label>
          <input type="text" id="editDelayReason" value="${event.reason || ''}">
        </div>
      `;

    default:
      return '';
  }
}

function updateSelectedEvent() {
  if (state.selectedEvent === null) return;

  const event = state.demo.events[state.selectedEvent];
  event.timestamp = parseInt(document.getElementById('editTimestamp').value) || 0;

  switch (event.type) {
    case 'keypress':
      event.key = buildKeyCombo(
        document.getElementById('editSuper').checked,
        document.getElementById('editShift').checked,
        document.getElementById('editCtrl').checked,
        document.getElementById('editAlt').checked,
        document.getElementById('editKeyValue').value
      );
      break;

    case 'mouse':
      event.action = document.getElementById('editMouseAction').value;
      event.x = parseInt(document.getElementById('editMouseX').value) || undefined;
      event.y = parseInt(document.getElementById('editMouseY').value) || undefined;
      event.duration = parseInt(document.getElementById('editMouseDuration').value) || 500;
      break;

    case 'delay':
      event.duration = parseInt(document.getElementById('editDelayDuration').value) || 1000;
      event.reason = document.getElementById('editDelayReason').value || undefined;
      break;
  }

  renderTimeline();
  renderEventList();
  updateStats();
}

// ============================================================
// ADD EVENT MODAL
// ============================================================

let currentAddType = 'keypress';

function showAddModal(type) {
  currentAddType = type;

  document.getElementById('modalTitle').textContent =
    `Add ${type.charAt(0).toUpperCase() + type.slice(1)} Event`;

  // Show correct form
  document.getElementById('keypressForm').style.display = type === 'keypress' ? 'block' : 'none';
  document.getElementById('mouseForm').style.display = type === 'mouse' ? 'block' : 'none';
  document.getElementById('delayForm').style.display = type === 'delay' ? 'block' : 'none';

  // Set default timestamp to current playback position
  const defaultTime = Math.round(state.playbackTime / 100) * 100;
  document.getElementById('keyTimestamp').value = defaultTime;
  document.getElementById('mouseTimestamp').value = defaultTime;
  document.getElementById('delayTimestamp').value = defaultTime;

  elements.addEventModal.classList.add('open');
}

function hideAddModal() {
  elements.addEventModal.classList.remove('open');
}

function addEvent() {
  let event;

  switch (currentAddType) {
    case 'keypress':
      event = {
        type: 'keypress',
        timestamp: parseInt(document.getElementById('keyTimestamp').value) || 0,
        key: buildKeyCombo(
          document.getElementById('keySuper').checked,
          document.getElementById('keyShift').checked,
          document.getElementById('keyCtrl').checked,
          document.getElementById('keyAlt').checked,
          document.getElementById('keyValue').value
        )
      };
      break;

    case 'mouse':
      event = {
        type: 'mouse',
        timestamp: parseInt(document.getElementById('mouseTimestamp').value) || 0,
        action: document.getElementById('mouseAction').value,
        duration: parseInt(document.getElementById('mouseDuration').value) || 500
      };
      const x = parseInt(document.getElementById('mouseX').value);
      const y = parseInt(document.getElementById('mouseY').value);
      if (!isNaN(x)) event.x = x;
      if (!isNaN(y)) event.y = y;
      break;

    case 'delay':
      event = {
        type: 'delay',
        timestamp: parseInt(document.getElementById('delayTimestamp').value) || 0,
        duration: parseInt(document.getElementById('delayDuration').value) || 1000
      };
      const reason = document.getElementById('delayReason').value.trim();
      if (reason) event.reason = reason;
      break;
  }

  state.demo.events.push(event);
  hideAddModal();
  renderTimeline();
  renderEventList();
  updateStats();

  // Select the new event
  selectEvent(state.demo.events.length - 1);
}

function applyKeyPreset(keyCombo) {
  const parts = parseKey(keyCombo);
  document.getElementById('keySuper').checked = parts.super;
  document.getElementById('keyShift').checked = parts.shift;
  document.getElementById('keyCtrl').checked = parts.ctrl;
  document.getElementById('keyAlt').checked = parts.alt;
  document.getElementById('keyValue').value = parts.key;
}

// ============================================================
// EVENT OPERATIONS
// ============================================================

function deleteEvent(index) {
  state.demo.events.splice(index, 1);

  if (state.selectedEvent === index) {
    state.selectedEvent = null;
  } else if (state.selectedEvent > index) {
    state.selectedEvent--;
  }

  renderTimeline();
  renderEventList();
  renderEventProperties();
  updateStats();
}

function duplicateEvent(index) {
  const event = { ...state.demo.events[index] };
  event.timestamp += 1000; // Offset by 1 second
  state.demo.events.push(event);

  renderTimeline();
  renderEventList();
  updateStats();

  selectEvent(state.demo.events.length - 1);
}

// ============================================================
// FILE OPERATIONS
// ============================================================

function newDemo() {
  if (state.demo.events.length > 0) {
    if (!confirm('Create new demo? Unsaved changes will be lost.')) return;
  }

  state.demo = {
    name: 'untitled-demo',
    description: '',
    stage: 1,
    startChallenge: 1,
    randomSeed: 12345,
    events: []
  };

  state.selectedEvent = null;
  state.playbackTime = 0;

  elements.demoName.value = state.demo.name;
  elements.demoDescription.value = state.demo.description;
  elements.demoStage.value = state.demo.stage;
  elements.startChallenge.value = state.demo.startChallenge;
  elements.randomSeed.value = state.demo.randomSeed;

  renderTimeline();
  renderEventList();
  renderEventProperties();
  updateStats();
  updatePlayhead();
}

function loadDemo() {
  const file = elements.fileInput.files[0];
  if (!file) return;

  const reader = new FileReader();
  reader.onload = (e) => {
    try {
      const data = JSON.parse(e.target.result);

      state.demo = {
        name: data.name || 'untitled',
        description: data.description || '',
        stage: data.stage || 1,
        startChallenge: data.startChallenge || 1,
        randomSeed: data.randomSeed || 12345,
        events: data.events || []
      };

      state.selectedEvent = null;
      state.playbackTime = 0;

      elements.demoName.value = state.demo.name;
      elements.demoDescription.value = state.demo.description;
      elements.demoStage.value = state.demo.stage;
      elements.startChallenge.value = state.demo.startChallenge;
      elements.randomSeed.value = state.demo.randomSeed;

      renderTimeline();
      renderEventList();
      renderEventProperties();
      updateStats();
      updatePlayhead();

    } catch (err) {
      alert('Failed to load demo: ' + err.message);
    }
  };

  reader.readAsText(file);
  elements.fileInput.value = '';
}

function saveDemo() {
  const json = JSON.stringify(state.demo, null, 2);
  const blob = new Blob([json], { type: 'application/json' });
  const url = URL.createObjectURL(blob);

  const a = document.createElement('a');
  a.href = url;
  a.download = `${state.demo.name}.json`;
  a.click();

  URL.revokeObjectURL(url);
}

function exportDemo() {
  // Export in game-ready format
  const exported = {
    meta: {
      name: state.demo.name,
      description: state.demo.description,
      stage: state.demo.stage,
      startChallenge: state.demo.startChallenge,
      randomSeed: state.demo.randomSeed,
      duration: getDuration(),
      eventCount: state.demo.events.length,
      created: new Date().toISOString()
    },
    events: [...state.demo.events].sort((a, b) => a.timestamp - b.timestamp)
  };

  const json = JSON.stringify(exported, null, 2);
  const blob = new Blob([json], { type: 'application/json' });
  const url = URL.createObjectURL(blob);

  const a = document.createElement('a');
  a.href = url;
  a.download = `${state.demo.name}-export.json`;
  a.click();

  URL.revokeObjectURL(url);
}

// ============================================================
// UTILITIES
// ============================================================

function getDuration() {
  if (state.demo.events.length === 0) return 0;

  let maxTime = 0;
  for (const event of state.demo.events) {
    const endTime = event.timestamp + (event.duration || 0);
    if (endTime > maxTime) maxTime = endTime;
  }

  return maxTime + 1000; // Add 1 second padding
}

function updateStats() {
  elements.totalDuration.textContent = formatTimeShort(getDuration());
  elements.totalEvents.textContent = state.demo.events.length;
}

function formatTime(ms) {
  const totalSeconds = ms / 1000;
  const mins = Math.floor(totalSeconds / 60);
  const secs = (totalSeconds % 60).toFixed(3);
  return `${mins}:${secs.padStart(6, '0')}`;
}

function formatTimeShort(ms) {
  const totalSeconds = Math.floor(ms / 1000);
  const mins = Math.floor(totalSeconds / 60);
  const secs = totalSeconds % 60;
  return `${mins}:${secs.toString().padStart(2, '0')}`;
}

function buildKeyCombo(super_, shift, ctrl, alt, key) {
  const parts = [];
  if (super_) parts.push('Super');
  if (ctrl) parts.push('Ctrl');
  if (alt) parts.push('Alt');
  if (shift) parts.push('Shift');
  if (key) parts.push(key);
  return parts.join('+');
}

function parseKey(keyCombo) {
  const result = { super: false, shift: false, ctrl: false, alt: false, key: '' };
  if (!keyCombo) return result;

  const parts = keyCombo.split('+');
  const modifiers = ['Super', 'Shift', 'Ctrl', 'Alt'];

  for (const part of parts) {
    const lower = part.toLowerCase();
    if (lower === 'super') result.super = true;
    else if (lower === 'shift') result.shift = true;
    else if (lower === 'ctrl') result.ctrl = true;
    else if (lower === 'alt') result.alt = true;
    else result.key = part;
  }

  return result;
}

// Initialize on load
init();
