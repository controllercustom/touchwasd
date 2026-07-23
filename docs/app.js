import { ESPLoader, Transport } from 'https://cdn.jsdelivr.net/npm/esptool-js/bundle.js';

let loader = null;
let port = null;
let transport = null;

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

function log(msg, cls) {
  const line = document.createElement('div');
  line.className = cls || 'info';
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
  setStatus('Connecting...', 'flashing');

  try {
    port = await navigator.serial.requestPort();
    if (!port) {
      els.flashBtn.disabled = false;
      setStatus('Ready', 'ready');
      return;
    }

    transport = new Transport(port);
    await transport.connect(BAUD);
    transport.readLoop();
    log('Connected', 'success');
    setStatus('Connected', 'connected');

    loader = new ESPLoader({
      transport,
      baudrate: BAUD,
    });

    log('Downloading firmware...', 'info');
    const firmwareResp = await fetch(url);
    if (!firmwareResp.ok) {
      throw new Error('Firmware download failed: HTTP ' + firmwareResp.status);
    }
    const firmwareData = await firmwareResp.arrayBuffer();
    log('Firmware loaded (' + (firmwareData.byteLength / 1024).toFixed(1) + ' KB)', 'info');

    log('Synchronizing with chip...', 'info');
    const chipDesc = await loader.main();
    log('Chip: ' + chipDesc, 'info');

    const chipName = loader.chip.CHIP_NAME || 'Unknown';
    const mac = await loader.chip.readMac(loader);
    log('Chip: ' + chipName + ' (MAC: ' + mac + ')', 'info');

    if (els.eraseAll.checked) {
      log('Erasing all flash (this takes a while)...', 'warn');
      await loader.eraseFlash();
      log('Full flash erase complete', 'info');
    }

    const fileSize = firmwareData.byteLength;
    const writeSize = loader.FLASH_WRITE_SIZE || 0x400;

    log('Flashing firmware...', 'info');
    setStatus('Flashing...', 'flashing');

    const numBlocks = await loader.flashBegin(fileSize, 0x0);

    for (let seq = 0; seq < numBlocks; seq++) {
      const offset = seq * writeSize;
      const end = Math.min(offset + writeSize, fileSize);
      const chunk = firmwareData.slice(offset, end);
      await loader.flashBlock(chunk, seq);

      const pct = ((seq + 1) / numBlocks) * 100;
      setProgress(pct, 'Block ' + (seq + 1) + '/' + numBlocks);
    }

    log('Flashing complete!', 'success');
    setStatus('Done', 'done');

    log('Rebooting...', 'info');
    await loader.flashFinish(true);

  } catch (e) {
    log('Error: ' + e.message, 'error');
    setStatus('Error', 'error');
  } finally {
    try { if (transport) await transport.disconnect(); } catch (_) {}
    loader = null;
    port = null;
    transport = null;
    els.flashBtn.disabled = false;
    clearProgress();
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
