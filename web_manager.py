#!/usr/bin/env python3
"""JukeboxPi web manager — add, edit and delete tracks via a browser.
Run:  python3 web_manager.py
Then open:  http://<pi-ip>:5000"""

import json
import os
from pathlib import Path
from flask import Flask, request, jsonify, send_from_directory, render_template_string
from werkzeug.utils import secure_filename

app = Flask(__name__)
BASE_DIR = Path(__file__).parent
MAPPINGS_FILE = BASE_DIR / 'music_mappings.json'
TRACKART_DIR = BASE_DIR / 'trackart'

# ---------------------------------------------------------------------------

HTML = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>JukeboxPi Manager</title>
<style>
  * { box-sizing: border-box; margin: 0; padding: 0; }

  body { font-family: 'Helvetica Neue', Arial, sans-serif; background: #f0f0f0; }

  header {
    background: #1a1a1a;
    color: white;
    padding: 16px 24px;
    display: flex;
    align-items: center;
    justify-content: space-between;
    position: sticky;
    top: 0;
    z-index: 10;
  }
  header h1 { font-size: 1.3rem; letter-spacing: -0.3px; }

  .btn {
    padding: 8px 16px;
    border: none;
    border-radius: 6px;
    cursor: pointer;
    font-size: 0.88rem;
    font-weight: 600;
  }
  .btn-green  { background: #1DB954; color: white; }
  .btn-blue   { background: #4A90D9; color: white; }
  .btn-red    { background: #e74c3c; color: white; }
  .btn-gray   { background: #aaa;    color: white; }
  .btn:hover  { opacity: 0.85; }

  .grid {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(190px, 1fr));
    gap: 16px;
    padding: 24px;
    max-width: 1200px;
    margin: 0 auto;
  }

  .card {
    background: white;
    border-radius: 10px;
    padding: 16px;
    text-align: center;
    box-shadow: 0 2px 8px rgba(0,0,0,0.09);
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 10px;
  }

  .number {
    background: #1DB954;
    color: white;
    font-size: 1.4rem;
    font-weight: 700;
    width: 44px;
    height: 44px;
    border-radius: 50%;
    display: flex;
    align-items: center;
    justify-content: center;
    flex-shrink: 0;
  }

  .card img {
    width: 148px;
    height: 148px;
    object-fit: cover;
    border-radius: 6px;
  }

  .no-art {
    width: 148px;
    height: 148px;
    background: #eee;
    border-radius: 6px;
    display: flex;
    align-items: center;
    justify-content: center;
    color: #bbb;
    font-size: 0.8rem;
  }

  .title { font-size: 0.85rem; color: #333; line-height: 1.4; }

  .card-actions { display: flex; gap: 8px; }

  /* Modal */
  .overlay {
    display: none;
    position: fixed;
    inset: 0;
    background: rgba(0,0,0,0.5);
    z-index: 100;
    align-items: center;
    justify-content: center;
  }
  .overlay.open { display: flex; }

  .modal {
    background: white;
    border-radius: 12px;
    padding: 28px;
    width: 480px;
    max-width: 95vw;
    max-height: 90vh;
    overflow-y: auto;
  }
  .modal h2 { margin-bottom: 20px; font-size: 1.15rem; }

  .field { margin-bottom: 16px; }
  .field label {
    display: block;
    font-size: 0.82rem;
    color: #555;
    font-weight: 600;
    margin-bottom: 5px;
  }
  .field input[type=text],
  .field input[type=number] {
    width: 100%;
    padding: 9px 12px;
    border: 1px solid #ddd;
    border-radius: 6px;
    font-size: 0.93rem;
  }
  .field input:focus { outline: none; border-color: #1DB954; }
  .hint { font-size: 0.78rem; color: #999; margin-top: 4px; }

  .art-preview { margin-top: 8px; }
  .art-preview img { width: 72px; height: 72px; object-fit: cover; border-radius: 4px; }

  .modal-actions { display: flex; gap: 10px; margin-top: 20px; }

  .toast {
    position: fixed;
    bottom: 24px;
    right: 24px;
    background: #1a1a1a;
    color: white;
    padding: 12px 20px;
    border-radius: 8px;
    font-size: 0.88rem;
    opacity: 0;
    transition: opacity 0.3s;
    z-index: 200;
    pointer-events: none;
  }
  .toast.show { opacity: 1; }
</style>
</head>
<body>

<header>
  <h1>JukeboxPi Manager</h1>
  <button class="btn btn-green" onclick="openModal()">+ Add Track</button>
</header>

<div class="grid" id="track-grid"></div>

<div class="overlay" id="overlay">
  <div class="modal">
    <h2 id="modal-heading">Add Track</h2>

    <div class="field">
      <label>Keypad Number</label>
      <input type="number" id="f-number" min="0" max="999" placeholder="e.g. 1 or 99">
    </div>
    <div class="field">
      <label>Title</label>
      <input type="text" id="f-title" placeholder="Artist: Album Name">
    </div>
    <div class="field">
      <label>Spotify URI</label>
      <input type="text" id="f-uri" placeholder="spotify:album:... or spotify:playlist:...">
      <div class="hint">Find it in Spotify: right-click album → Share → Copy Spotify URI</div>
    </div>
    <div class="field">
      <label>Artwork</label>
      <input type="file" id="f-file" accept="image/*" onchange="onFileChosen(this)">
      <div class="art-preview" id="art-preview"></div>
      <div class="hint" style="margin-top:8px">Or type an existing filename from the trackart folder:</div>
      <input type="text" id="f-filename" placeholder="AlbumName.png" style="margin-top:6px">
    </div>

    <div class="modal-actions">
      <button class="btn btn-green" onclick="saveTrack()">Save</button>
      <button class="btn btn-gray"  onclick="closeModal()">Cancel</button>
    </div>
  </div>
</div>

<div class="toast" id="toast"></div>

<script>
let tracks = {};
let editingNumber = null;

async function load() {
  const res = await fetch('/api/tracks');
  tracks = await res.json();
  render();
}

function render() {
  const grid = document.getElementById('track-grid');
  const sorted = Object.entries(tracks).sort((a, b) => parseInt(a[0]) - parseInt(b[0]));

  grid.innerHTML = sorted.map(([num, t]) => {
    const img = t.filename
      ? `<img src="/trackart/${t.filename}" alt="${t.title}"
             onerror="this.replaceWith(noArt())">`
      : `<div class="no-art">No artwork</div>`;
    return `<div class="card">
      <div class="number">${num}</div>
      ${img}
      <div class="title">${t.title}</div>
      <div class="card-actions">
        <button class="btn btn-blue"  onclick="openModal('${num}')" style="font-size:0.8rem;padding:6px 12px">Edit</button>
        <button class="btn btn-red"   onclick="del('${num}')"       style="font-size:0.8rem;padding:6px 12px">Delete</button>
      </div>
    </div>`;
  }).join('');
}

function noArt() {
  const d = document.createElement('div');
  d.className = 'no-art';
  d.textContent = 'No artwork';
  return d;
}

function openModal(number = null) {
  editingNumber = number;
  document.getElementById('modal-heading').textContent = number ? 'Edit Track' : 'Add Track';
  document.getElementById('f-number').value    = number || '';
  document.getElementById('f-number').disabled = !!number;
  const t = number ? (tracks[number] || {}) : {};
  document.getElementById('f-title').value    = t.title    || '';
  document.getElementById('f-uri').value      = t.uri      || '';
  document.getElementById('f-filename').value = t.filename || '';
  document.getElementById('art-preview').innerHTML = t.filename
    ? `<img src="/trackart/${t.filename}" alt="">` : '';
  document.getElementById('f-file').value = '';
  document.getElementById('overlay').classList.add('open');
}

function closeModal() {
  document.getElementById('overlay').classList.remove('open');
}

function onFileChosen(input) {
  const file = input.files[0];
  if (!file) return;
  document.getElementById('art-preview').innerHTML =
    `<img src="${URL.createObjectURL(file)}" alt="preview">`;
  document.getElementById('f-filename').value = file.name;
}

async function saveTrack() {
  const number   = (editingNumber || document.getElementById('f-number').value).toString().trim();
  const title    = document.getElementById('f-title').value.trim();
  const uri      = document.getElementById('f-uri').value.trim();
  let   filename = document.getElementById('f-filename').value.trim();

  if (!number || !title || !uri) {
    toast('Number, title and URI are all required'); return;
  }

  const fileInput = document.getElementById('f-file');
  if (fileInput.files[0]) {
    const form = new FormData();
    form.append('file', fileInput.files[0]);
    const res  = await fetch('/api/upload', { method: 'POST', body: form });
    const data = await res.json();
    filename = data.filename;
  }

  const track = { title, uri };
  if (filename) track.filename = filename;

  await fetch(`/api/tracks/${number}`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(track)
  });

  closeModal();
  await load();
  toast(`Track ${number} saved`);
}

async function del(number) {
  if (!confirm(`Delete track ${number}: ${tracks[number]?.title}?`)) return;
  await fetch(`/api/tracks/${number}`, { method: 'DELETE' });
  await load();
  toast(`Track ${number} deleted`);
}

function toast(msg) {
  const el = document.getElementById('toast');
  el.textContent = msg;
  el.classList.add('show');
  setTimeout(() => el.classList.remove('show'), 2500);
}

document.getElementById('overlay').addEventListener('click', e => {
  if (e.target.id === 'overlay') closeModal();
});

load();
</script>
</body>
</html>"""

# ---------------------------------------------------------------------------

def load_mappings():
    with open(MAPPINGS_FILE) as f:
        return json.load(f)

def save_mappings(data):
    with open(MAPPINGS_FILE, 'w') as f:
        json.dump(data, f, indent=2)

@app.route('/')
def index():
    return render_template_string(HTML)

@app.route('/api/tracks')
def get_tracks():
    return jsonify(load_mappings())

@app.route('/api/tracks/<number>', methods=['PUT'])
def update_track(number):
    data = load_mappings()
    data[number] = request.json
    save_mappings(data)
    return jsonify({'ok': True})

@app.route('/api/tracks/<number>', methods=['DELETE'])
def delete_track(number):
    data = load_mappings()
    data.pop(number, None)
    save_mappings(data)
    return jsonify({'ok': True})

@app.route('/api/upload', methods=['POST'])
def upload():
    f = request.files['file']
    filename = secure_filename(f.filename)
    f.save(TRACKART_DIR / filename)
    return jsonify({'filename': filename})

@app.route('/trackart/<path:filename>')
def trackart(filename):
    return send_from_directory(str(TRACKART_DIR), filename)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=False)
