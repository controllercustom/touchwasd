import { ESPLoader, Transport } from 'https://cdn.jsdelivr.net/npm/esptool-js/lib/esptool.js';

let loader = null;
let port = null;

const els = {
  board: document.getElementById('board'),
  version: document.getElementById('version'),
  eraseAll: document.getElementById('erase-all'),
  flashBtn: document.getElementById('flash-btn'),
  log: document.getElementById('log'),
  statusText: document.getElementById('status-text'),
  statusBadge: document.getElementById('status-badge'),
  progressBar: document.getElementById('progress-bar'),
  progressFill: document.getElementById('progress-fill'),
  progressText: document.getElementById('progress-text'),
  atoms3Info: document.getElementById('atoms3-info'),
  esp32s3Info: document.getElementById('esp32s3-info'),
};

const BAUD = 921600;

function log(msg, cls = 'info') {
  const line = document.createElement('div');
  line.className = cls;
  line.textContent = msg;
  els.log.appendChild(line);
  els.log.scrollTop = els.log.scrollHeight;
}

function setStatus(text, badge) {
  els.statusText.textContent = text;
  els.statusBadge.textContent = badge;
  els.statusBadge.className = 'status-badge ' + badge;
}

function setProgress(pct, text) {
  els.progressBar.classList.add('active');
  els.progressFill.style.width = Math.round(pct) + '%';
  els.progressText.textContent = text || '';
}

function clearProgress() {
  els.progressBar.classList.remove('active');
  els.progressFill.style.width = '0%';
  els.progressText.textContent = '';
}

async function loadFirmwareManifest() {
  try {
    const res = await fetch('firmware.json');
    if (!res.ok) throw new Error('HTTP ' + res.status);
    return await res.json();
  } catch (e) {
    log('Failed to load firmware manifest: ' + e.message, 'error');
    return null;
  }
}

function populateVersions(manifest) {
  const sel = els.version;
  sel.innerHTML = '';
  if (!manifest || !manifest.versions || manifest.versions.length === 0) {
    sel.innerHTML = '<option value="">No versions available</option>';
    return;
  }
  for (const v of manifest.versions) {
    const opt = document.createElement('option');
    opt.value = v;
    opt.textContent = v;
    sel.appendChild(opt);
  }
  if (manifest.latest) {
    sel.value = manifest.latest;
  }
}

function updateInstructions() {
  const board = els.board.value;
  els.atoms3Info.classList.toggle('hidden', board !== 'atoms3');
  els.esp32s3Info.classList.toggle('hidden', board !== 'esp32s3');
}

function firmwareUrl() {
  const board = els.board.value;
  const version = els.version.value;
  if (!version) return null;
  return 'firmware/' + version + '/' + board + '/touchwasd.ino.merged.bin';
}

async function connectSerial() {
  try {
    port = await navigator.serial.requestPort();
    await port.open({ baudRate: BAUD });
    log('Connected', 'success');
    setStatus('Connected', 'connected');
    return port;
  } catch (e) {
    if (e.name === 'NotFoundError') {
      log('No port selected', 'warn');
    } else {
      log('Serial connection failed: ' + e.message, 'error');
    }
    return null;
  }
}

async function flash() {
  if (loader) {
    log('Already flashing', 'warn');
    return;
  }

  const url = firmwareUrl();
  if (!url) {
    log('No firmware version selected', 'error');
    return;
  }

  els.flashBtn.disabled = true;
  setStatus('Flashing...', 'flashing');

  try {
    port = await connectSerial();
    if (!port) {
      els.flashBtn.disabled = false;
      setStatus('Ready', 'ready');
      return;
    }

    log('Downloading firmware...', 'info');
    const firmwareResp = await fetch(url);
    if (!firmwareResp.ok) {
      throw new Error('Firmware download failed: HTTP ' + firmwareResp.status);
    }
    const firmwareData = await firmwareResp.arrayBuffer();
    log('Firmware loaded (' + (firmwareData.byteLength / 1024).toFixed(1) + ' KB)', 'info');

    const transport = new Transport(port);
    loader = new ESPLoader(transport, BAUD);

    loader.on('progress', (pct, text) => {
      setProgress(pct * 100, text);
    });

    log('Synchronizing with chip...', 'info');
    await loader.main();
    log('Chip: ' + loader.chipName + ' (MAC: ' + loader.macAddr + ')', 'info');

    const eraseAll = els.eraseAll.checked;
    if (eraseAll) {
      log('Erasing all flash (this takes a while)...', 'warn');
    }

    log('Flashing firmware...', 'info');
    await loader.flash({
      flashSize: 'keep',
      flashMode: 'keep',
      flashFreq: 'keep',
      eraseAll,
      compress: true,
      reportProgress: true,
      partitions: [
        { address: 0x0, data: new Uint8Array(firmwareData) },
      ],
    });

    log('Flashing complete!', 'success');
    setStatus('Done', 'done');
    clearProgress();

    log('Resetting board...', 'info');
    await loader.hard_reset();

  } catch (e) {
    log('Error: ' + e.message, 'error');
    setStatus('Error', 'error');
  } finally {
    try {
      if (port && port.readable) {
        await port.close();
      }
    } catch (_) {}
    loader = null;
    port = null;
    els.flashBtn.disabled = false;
  }
}

els.board.addEventListener('change', updateInstructions);
els.flashBtn.addEventListener('click', flash);

(async function init() {
  log('touchWASD Firmware Flasher ready', 'info');
  log('Select a board and version, then click Flash Firmware', 'info');

  const manifest = await loadFirmwareManifest();
  if (manifest) {
    populateVersions(manifest);
    log('Found ' + manifest.versions.length + ' firmware version(s)', 'info');
  } else {
    log('No firmware manifest found. Push a git tag to trigger a build.', 'warn');
  }

  updateInstructions();
})();
