/*
 * MIT License
 *
 * Copyright (c) 2026 controllercustom@myyahoo.com
 *
 * Permission is hereby granted, free of charge, to any person obtaining a copy
 * of this software and associated documentation files (the "Software"), to deal
 * in the Software without restriction, including without limitation the rights
 * to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
 * copies of the Software, and to permit persons to whom the Software is
 * furnished to do so, subject to the following conditions:
 *
 * The above copyright notice and this permission notice shall be included in all
 * copies or substantial portions of the Software.
 *
 * THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
 * IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
 * FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
 * AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
 * LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
 * OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
 * SOFTWARE.
 */

#ifndef WEBPAGE_H
#define WEBPAGE_H

#include <Arduino.h>

const char index_html[] PROGMEM = R"rawliteral(
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
    <meta name="apple-mobile-web-app-capable" content="yes">
    <meta name="apple-mobile-web-app-status-bar-style" content="black-translucent">
    <meta name="mobile-web-app-capable" content="yes">
    <title>touchWASD v1.0.3</title>
    <style>
        :root {
            --bg: #1a1a2e;
            --text: #ffffff;
            --text-dim: #8888aa;
            --accent: #ff4081;
        }
        html, body {
            margin: 0; padding: 0;
            width: 100%; height: 100%;
            overflow: hidden;
            font-family: 'Segoe UI', Helvetica, Arial, sans-serif;
            background: var(--bg);
            display: flex;
            flex-direction: column;
            -webkit-touch-callout: none;
            -webkit-user-select: none;
            user-select: none;
            touch-action: none;
        }

        body.ps-center  { justify-content: center; align-items: center; }
        body.ps-top     { justify-content: flex-start; align-items: center; }
        body.ps-bottom  { justify-content: flex-end; align-items: center; }
        body.ps-topleft { justify-content: flex-start; align-items: flex-start; }
        body.ps-topright { justify-content: flex-start; align-items: flex-end; }
        body.ps-bottomleft { justify-content: flex-end; align-items: flex-start; }
        body.ps-bottomright { justify-content: flex-end; align-items: flex-end; }

        #circle-container {
            position: relative;
            flex-shrink: 0;
        }
        #circle-container.sz-sm { width: min(40vw, 50svh, 240px); height: min(40vw, 50svh, 240px); }
        #circle-container.sz-md { width: min(60vw, 60svh, 360px); height: min(60vw, 60svh, 360px); }
        #circle-container.sz-lg { width: min(80vw, 80svh, 480px); height: min(80vw, 80svh, 480px); }
        #circle-container.sz-xl { width: min(98vw, 98svh); height: min(98vw, 98svh); }

        #circle-container svg {
            width: 100%;
            height: 100%;
            display: block;
        }

        .slice {
            cursor: pointer;
            transition: opacity 0.05s ease;
        }
        .slice:active {
            opacity: 0.6;
        }
        .slice.active {
            opacity: 0.6;
        }

        #center-circle {
            fill: var(--bg);
            pointer-events: none;
        }
        #center-label {
            pointer-events: none;
            fill: var(--text-dim);
            font-size: 13px;
            text-anchor: middle;
            dominant-baseline: central;
            font-family: 'Segoe UI', Helvetica, Arial, sans-serif;
        }

        #settings-btn {
            position: fixed;
            top: 12px;
            right: 16px;
            width: 48px;
            height: 48px;
            border-radius: 24px;
            border: 2px solid var(--text-dim);
            background: rgba(255,255,255,0.08);
            color: var(--text-dim);
            font-size: 22px;
            cursor: pointer;
            display: flex;
            align-items: center;
            justify-content: center;
            z-index: 200;
            touch-action: none;
        }
        #settings-btn:active {
            background: rgba(255,255,255,0.2);
        }

        #settings-panel {
            display: none;
            position: fixed;
            inset: 0;
            background: rgba(0,0,0,0.85);
            z-index: 300;
            flex-direction: column;
            align-items: center;
            justify-content: center;
            gap: 24px;
            padding-top: env(safe-area-inset-top, 20px);
            padding-bottom: env(safe-area-inset-bottom, 20px);
            box-sizing: border-box;
            overflow-y: auto;
        }
        #settings-panel.open {
            display: flex;
        }

        .toggle-btn {
            padding: 10px 24px;
            border-radius: 8px;
            border: 2px solid var(--text-dim);
            background: transparent;
            color: var(--text-dim);
            font-size: 18px;
            font-weight: bold;
            cursor: pointer;
            touch-action: none;
        }
        .toggle-btn.active, .pos-btn.active, .size-btn.active {
            border-color: var(--accent);
            color: var(--accent);
            background: rgba(255,64,129,0.15);
        }
        .close-btn {
            padding: 12px 48px;
            border-radius: 8px;
            border: none;
            background: var(--accent);
            color: white;
            font-size: 18px;
            font-weight: bold;
            cursor: pointer;
            margin-top: 16px;
            touch-action: none;
        }
        .settings-label {
            color: var(--text);
            font-size: 16px;
            font-weight: bold;
            margin-bottom: 4px;
        }
        .size-row, .pos-row {
            display: flex;
            flex-wrap: wrap;
            justify-content: center;
            gap: 6px;
        }
        .size-btn {
            padding: 8px 16px;
            border-radius: 6px;
            border: 2px solid var(--text-dim);
            background: transparent;
            color: var(--text-dim);
            font-size: 14px;
            font-weight: bold;
            cursor: pointer;
            touch-action: none;
        }
        .pos-btn {
            width: 40px;
            height: 40px;
            border-radius: 6px;
            border: 2px solid var(--text-dim);
            background: transparent;
            color: var(--text-dim);
            font-size: 18px;
            cursor: pointer;
            touch-action: none;
            display: flex;
            align-items: center;
            justify-content: center;
        }
    </style>
</head>
<body>
    <div id="circle-container" class="sz-lg">
        <svg viewBox="0 0 200 200" xmlns="http://www.w3.org/2000/svg">
            <g id="slices"></g>

            <circle id="center-circle" cx="100" cy="100" r="28"/>
            <text id="center-label" x="100" y="100">touchWASD</text>

            <circle cx="100" cy="100" r="96" fill="none" stroke="#333" stroke-width="1.5"/>
            <circle cx="100" cy="100" r="28" fill="none" stroke="#444" stroke-width="1"/>
        </svg>
    </div>

    <button id="settings-btn">⚙</button>

    <div id="settings-panel">
        <div class="settings-label">Mode</div>
        <div class="size-row">
            <button class="toggle-btn" id="mode-wasd">WASD</button>
            <button class="toggle-btn" id="mode-arrows">Arrows</button>
        </div>

        <div class="settings-label">Size</div>
        <div class="size-row">
            <button class="size-btn" data-sz="sm">Small</button>
            <button class="size-btn" data-sz="md">Medium</button>
            <button class="size-btn active" data-sz="lg">Large</button>
            <button class="size-btn" data-sz="xl">Full</button>
        </div>

        <div class="settings-label">Position</div>
        <div class="pos-row">
            <div></div>       <button class="pos-btn" data-ps="top">↑</button>     <div></div>
            <button class="pos-btn" data-ps="topleft">↖</button>
            <button class="pos-btn active" data-ps="center">●</button>
            <button class="pos-btn" data-ps="topright">↗</button>
            <button class="pos-btn" data-ps="bottomleft">↙</button>
            <button class="pos-btn" data-ps="bottom">↓</button>
            <button class="pos-btn" data-ps="bottomright">↘</button>
        </div>

        <button class="close-btn" id="settings-close">Close</button>
    </div>

<script>
let ws;
let wsRetries = 0;
let currentMode = 'wasd';
let currentSz = localStorage.getItem('tw-sz') || 'lg';
let currentPs = localStorage.getItem('tw-ps') || 'center';

const arrowMap = { w: '↑', s: '↓', a: '←', d: '→' };

const slices = [
    { id: 'n',    label: 'W',  arrow: '↑',  keys: ['w'],               color: '#00bcd4', start: 337.5, end: 22.5  },
    { id: 'ne',   label: 'W+D', arrow: '↗', keys: ['w','d'],          color: '#455a64', start: 22.5,  end: 67.5  },
    { id: 'e',    label: 'D',  arrow: '→',  keys: ['d'],               color: '#9c27b0', start: 67.5,  end: 112.5 },
    { id: 'se',   label: 'D+S', arrow: '↘', keys: ['d','s'],           color: '#455a64', start: 112.5, end: 157.5 },
    { id: 's',    label: 'S',  arrow: '↓',  keys: ['s'],               color: '#ff9800', start: 157.5, end: 202.5 },
    { id: 'sw',   label: 'S+A', arrow: '↙', keys: ['s','a'],           color: '#455a64', start: 202.5, end: 247.5 },
    { id: 'w',    label: 'A',  arrow: '←',  keys: ['a'],               color: '#4caf50', start: 247.5, end: 292.5 },
    { id: 'nw',   label: 'A+W', arrow: '↖', keys: ['a','w'],           color: '#455a64', start: 292.5, end: 337.5 }
];

function describeArc(cx, cy, r, startAngle, endAngle) {
    const outerR = r;
    const innerR = 28;
    function angle(a) {
        const rad = (a - 90) * Math.PI / 180;
        return { x: cx + outerR * Math.cos(rad), y: cy + outerR * Math.sin(rad) };
    }
    const s = angle(startAngle);
    const e = angle(endAngle);
    function innerAngle(a) {
        const rad = (a - 90) * Math.PI / 180;
        return { x: cx + innerR * Math.cos(rad), y: cy + innerR * Math.sin(rad) };
    }
    const si = innerAngle(startAngle);
    const ei = innerAngle(endAngle);
    const sweep = ((endAngle - startAngle + 360) % 360) > 180 ? 1 : 0;
    return [
        'M', s.x, s.y,
        'A', outerR, outerR, 0, sweep, 1, e.x, e.y,
        'L', ei.x, ei.y,
        'A', innerR, innerR, 0, sweep, 0, si.x, si.y,
        'Z'
    ].join(' ');
}

function renderSlices() {
    const g = document.getElementById('slices');
    g.innerHTML = '';
    slices.forEach((slice, idx) => {
        let sa, ea;
        if (slice.id === 'n')      { sa = 337.5; ea = 22.5; }
        else if (slice.id === 'ne'){ sa = 22.5;  ea = 67.5; }
        else if (slice.id === 'e') { sa = 67.5;  ea = 112.5; }
        else if (slice.id === 'se'){ sa = 112.5; ea = 157.5; }
        else if (slice.id === 's') { sa = 157.5; ea = 202.5; }
        else if (slice.id === 'sw'){ sa = 202.5; ea = 247.5; }
        else if (slice.id === 'w') { sa = 247.5; ea = 292.5; }
        else                       { sa = 292.5; ea = 337.5; }
        const path = document.createElementNS('http://www.w3.org/2000/svg', 'path');
        path.setAttribute('d', describeArc(100, 100, 96, sa, ea));
        path.setAttribute('fill', slice.color);
        path.setAttribute('opacity', '0.85');
        path.setAttribute('stroke', '#333');
        path.setAttribute('stroke-width', '0.5');
        path.classList.add('slice');
        path.dataset.index = idx;
        g.appendChild(path);
    });
}

function cxToCart(cx, cy, r, angleDeg, offsetR) {
    const rad = (angleDeg - 90) * Math.PI / 180;
    return { x: cx + offsetR * Math.cos(rad), y: cy + offsetR * Math.sin(rad) };
}

function renderLabels() {
    const g = document.getElementById('slices');
    slices.forEach((sl) => {
        const sa = sl.start;
        const ea = sl.end;
        let midAngle;
        if (ea > sa) {
            midAngle = (sa + ea) / 2;
        } else {
            midAngle = (sa + ea + 360) / 2;
            if (midAngle >= 360) midAngle -= 360;
        }
        const isDiag = sl.keys.length === 2;
        const r = isDiag ? 52 : 48;

        if (!isDiag) {
            const pt = cxToCart(100, 100, 96, midAngle, r);
            const text = document.createElementNS('http://www.w3.org/2000/svg', 'text');
            text.setAttribute('x', pt.x);
            text.setAttribute('y', pt.y);
            text.setAttribute('text-anchor', 'middle');
            text.setAttribute('dominant-baseline', 'central');
            text.setAttribute('fill', 'white');
            text.setAttribute('font-size', '22');
            text.setAttribute('font-weight', 'bold');
            text.setAttribute('pointer-events', 'none');
            if (currentMode === 'arrows') {
                text.textContent = sl.keys.map(k => arrowMap[k]).join('');
            } else {
                text.textContent = sl.label;
            }
            g.appendChild(text);

            const apt = cxToCart(100, 100, 96, midAngle, 66);
            const arrow = document.createElementNS('http://www.w3.org/2000/svg', 'text');
            arrow.setAttribute('x', apt.x);
            arrow.setAttribute('y', apt.y);
            arrow.setAttribute('text-anchor', 'middle');
            arrow.setAttribute('dominant-baseline', 'central');
            arrow.setAttribute('fill', 'rgba(255,255,255,0.5)');
            arrow.setAttribute('font-size', '14');
            arrow.setAttribute('pointer-events', 'none');
            if (currentMode === 'arrows') {
                arrow.textContent = '';
            } else {
                arrow.textContent = sl.arrow;
            }
            g.appendChild(arrow);
        } else {
            const pt = cxToCart(100, 100, 96, midAngle, 48);
            const t = document.createElementNS('http://www.w3.org/2000/svg', 'text');
            t.setAttribute('x', pt.x);
            t.setAttribute('y', pt.y);
            t.setAttribute('text-anchor', 'middle');
            t.setAttribute('dominant-baseline', 'central');
            t.setAttribute('fill', 'white');
            t.setAttribute('font-size', '16');
            t.setAttribute('font-weight', 'bold');
            t.setAttribute('pointer-events', 'none');
            if (currentMode === 'arrows') {
                t.textContent = sl.keys.map(k => arrowMap[k]).join('');
            } else {
                t.textContent = sl.label;
            }
            g.appendChild(t);
        }
    });
}

function updateCenterLabel() {
    document.getElementById('center-label').textContent = currentMode === 'wasd' ? 'WASD' : 'Arrows';
}

function draw() {
    const g = document.getElementById('slices');
    g.innerHTML = '';
    renderSlices();
    renderLabels();
    updateCenterLabel();
}

function applySettings() {
    document.body.className = 'ps-' + currentPs;
    const c = document.getElementById('circle-container');
    c.className = 'sz-' + currentSz;
    localStorage.setItem('tw-sz', currentSz);
    localStorage.setItem('tw-ps', currentPs);
    updateGearPosition();
}

function updateGearPosition() {
    const btn = document.getElementById('settings-btn');
    if (currentPs === 'topright') {
        btn.style.bottom = '12px';
        btn.style.left = '16px';
        btn.style.top = 'auto';
        btn.style.right = 'auto';
    } else {
        btn.style.top = '12px';
        btn.style.right = '16px';
        btn.style.bottom = 'auto';
        btn.style.left = 'auto';
    }
}

function setSize(sz) {
    currentSz = sz;
    applySettings();
    document.querySelectorAll('.size-btn').forEach(b => b.classList.toggle('active', b.dataset.sz === sz));
}

function setPosition(ps) {
    currentPs = ps;
    applySettings();
    document.querySelectorAll('.pos-btn').forEach(b => b.classList.toggle('active', b.dataset.ps === ps));
}

function connectWS() {
    ws = new WebSocket('ws://' + location.hostname + ':81/');
    ws.onopen = () => { wsRetries = 0; };
    ws.onmessage = (e) => {
        const d = e.data;
        if (d === '#MODE:wasd') {
            currentMode = 'wasd';
            draw();
            updateModeButtons();
        } else if (d === '#MODE:arrows') {
            currentMode = 'arrows';
            draw();
            updateModeButtons();
        }
    };
    ws.onclose = () => {
        if (wsRetries < 10) {
            wsRetries++;
            setTimeout(connectWS, Math.min(1000 * wsRetries, 10000));
        }
    };
    ws.onerror = () => {};
}
connectWS();

function sendKeysDown(keys) {
    if (!(ws && ws.readyState === 1)) return;
    keys.forEach(k => ws.send(k));
}

function sendKeysUp(keys) {
    if (!(ws && ws.readyState === 1)) return;
    keys.forEach(k => ws.send('~' + k));
}

let pressedPointers = new Map();

function getSliceFromPoint(el) {
    if (!el || !el.closest) return null;
    const sliceEl = el.closest('.slice');
    if (!sliceEl) return null;
    return slices[parseInt(sliceEl.dataset.index)];
}

document.addEventListener('pointerdown', function(e) {
    const el = document.elementFromPoint(e.clientX, e.clientY);
    const sliceEl = el && el.closest('.slice');
    if (!sliceEl) return;
    const slice = slices[parseInt(sliceEl.dataset.index)];
    if (!slice) return;
    e.preventDefault();
    sliceEl.classList.add('active');
    pressedPointers.set(e.pointerId, { slice: slice, el: sliceEl });
    sendKeysDown(slice.keys);
});

document.addEventListener('pointermove', function(e) {
    const entry = pressedPointers.get(e.pointerId);
    if (!entry) return;
    const el = document.elementFromPoint(e.clientX, e.clientY);
    const sliceEl = el && el.closest('.slice');
    const newSlice = sliceEl ? slices[parseInt(sliceEl.dataset.index)] : null;
    if (!newSlice || newSlice.id === entry.slice.id) return;
    sendKeysUp(entry.slice.keys);
    entry.el.classList.remove('active');
    sendKeysDown(newSlice.keys);
    sliceEl.classList.add('active');
    entry.slice = newSlice;
    entry.el = sliceEl;
});

function pointerEnd(e) {
    const entry = pressedPointers.get(e.pointerId);
    if (!entry) return;
    pressedPointers.delete(e.pointerId);
    sendKeysUp(entry.slice.keys);
    entry.el.classList.remove('active');
}
document.addEventListener('pointerup', pointerEnd);
document.addEventListener('pointercancel', pointerEnd);

const settingsBtn = document.getElementById('settings-btn');
const settingsPanel = document.getElementById('settings-panel');
const closeBtn = document.getElementById('settings-close');

settingsBtn.addEventListener('click', function(e) {
    settingsPanel.classList.add('open');
    updateModeButtons();
    document.querySelectorAll('.size-btn').forEach(b => b.classList.toggle('active', b.dataset.sz === currentSz));
    document.querySelectorAll('.pos-btn').forEach(b => b.classList.toggle('active', b.dataset.ps === currentPs));
});

closeBtn.addEventListener('click', function(e) {
    settingsPanel.classList.remove('open');
});

document.querySelectorAll('.size-btn').forEach(function(btn) {
    btn.addEventListener('click', function() { setSize(this.dataset.sz); });
});

document.querySelectorAll('.pos-btn').forEach(function(btn) {
    btn.addEventListener('click', function() { setPosition(this.dataset.ps); });
});

document.getElementById('mode-wasd').addEventListener('click', function() {
    if (ws && ws.readyState === 1) ws.send('#MODE:wasd');
});

document.getElementById('mode-arrows').addEventListener('click', function() {
    if (ws && ws.readyState === 1) ws.send('#MODE:arrows');
});

function updateModeButtons() {
    document.getElementById('mode-wasd').classList.toggle('active', currentMode === 'wasd');
    document.getElementById('mode-arrows').classList.toggle('active', currentMode === 'arrows');
}

document.addEventListener('contextmenu', function(e) { e.preventDefault(); });

applySettings();
draw();
</script>
</body>
</html>
)rawliteral";

#endif
