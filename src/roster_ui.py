import json
import re
import subprocess
import sys
import threading
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse

from .config import CHARACTERS_FILE, load_existing_roster, save_roster


DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 8765
ACCOUNT_SUMMARY_FILE = Path("output/account_summary.html")


def character_identity(character):
    if character.get("key"):
        return str(character["key"])
    if character.get("id") is not None and character.get("region"):
        return f"{character.get('region')}:id:{character.get('id')}"
    return "|".join([
        str(character.get("region") or ""),
        str(character.get("realm_slug") or character.get("realm") or "").casefold(),
        str(character.get("name") or "").casefold(),
    ])


def roster_payload(path=CHARACTERS_FILE):
    roster = load_existing_roster(path)
    characters = []
    for character in roster.get("characters", []):
        if not isinstance(character, dict):
            continue
        characters.append({
            "identity": character_identity(character),
            "name": character.get("name") or "",
            "realm": character.get("realm") or "",
            "realm_slug": character.get("realm_slug") or "",
            "region": character.get("region") or "",
            "id": character.get("id"),
            "enabled": character.get("enabled") is True,
            "stale": character.get("stale") is True,
        })
    return {
        "path": str(Path(path).resolve()),
        "character_count": len(characters),
        "enabled_count": sum(1 for character in characters if character["enabled"]),
        "characters": characters,
    }


def set_character_enabled(identity, enabled, path=CHARACTERS_FILE):
    roster = load_existing_roster(path)
    changed = False
    for character in roster.get("characters", []):
        if not isinstance(character, dict):
            continue
        if character_identity(character) == identity:
            character["enabled"] = bool(enabled)
            changed = True
            break

    if not changed:
        raise KeyError(f"Character not found: {identity}")

    save_roster(roster, path)
    return roster_payload(path)


def set_all_enabled(enabled, realm=None, path=CHARACTERS_FILE):
    roster = load_existing_roster(path)
    changed = 0
    for character in roster.get("characters", []):
        if not isinstance(character, dict):
            continue
        if realm and character.get("realm") != realm:
            continue
        if character.get("enabled") is not bool(enabled):
            character["enabled"] = bool(enabled)
            changed += 1

    if changed:
        save_roster(roster, path)
    return roster_payload(path)


HTML = r"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>wow-profile Roster</title>
  <style>
    :root {
      color-scheme: light;
      --bg: #f5f7fb;
      --panel: #fff;
      --text: #17202a;
      --muted: #667085;
      --line: #d8dee9;
      --accent: #1f6feb;
      --accent-soft: #e8f1ff;
      --on: #1a7f37;
      --off: #8a94a6;
      --stale: #9a6700;
    }
    * { box-sizing: border-box; }
    body {
      margin: 0;
      background: var(--bg);
      color: var(--text);
      font-family: Segoe UI, system-ui, -apple-system, BlinkMacSystemFont, sans-serif;
      font-size: 14px;
      line-height: 1.45;
    }
    main {
      width: min(1280px, calc(100% - 32px));
      margin: 0 auto;
      padding: 24px 0 44px;
    }
    header {
      display: flex;
      align-items: flex-end;
      justify-content: space-between;
      gap: 16px;
      margin-bottom: 16px;
    }
    h1 {
      margin: 0;
      font-size: 28px;
      line-height: 1.15;
      letter-spacing: 0;
    }
    .subtle {
      color: var(--muted);
      font-size: 13px;
      margin-top: 4px;
    }
    .stats {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(160px, 1fr));
      gap: 10px;
      margin-bottom: 14px;
    }
    .stat {
      background: var(--panel);
      border: 1px solid var(--line);
      border-radius: 8px;
      padding: 12px 14px;
    }
    .stat-label {
      color: var(--muted);
      font-size: 12px;
      text-transform: uppercase;
      letter-spacing: .04em;
    }
    .stat-value {
      font-size: 22px;
      font-weight: 700;
      margin-top: 3px;
    }
    .toolbar {
      display: grid;
      grid-template-columns: minmax(220px, 1fr) 180px 160px auto auto;
      gap: 10px;
      align-items: center;
      margin-bottom: 14px;
    }
    input, select, button {
      min-height: 36px;
      border: 1px solid var(--line);
      border-radius: 6px;
      background: var(--panel);
      color: var(--text);
      font: inherit;
    }
    input, select {
      padding: 0 10px;
      width: 100%;
    }
    button {
      padding: 0 12px;
      cursor: pointer;
      white-space: nowrap;
    }
    button.primary {
      border-color: var(--accent);
      background: var(--accent);
      color: #fff;
    }
    button:disabled {
      opacity: .55;
      cursor: default;
    }
    .header-actions {
      display: flex;
      gap: 8px;
      align-items: center;
    }
    .table-wrap {
      overflow-x: auto;
      background: var(--panel);
      border: 1px solid var(--line);
      border-radius: 8px;
    }
    table {
      width: 100%;
      border-collapse: collapse;
      min-width: 860px;
    }
    th, td {
      padding: 10px 12px;
      border-bottom: 1px solid var(--line);
      text-align: left;
      vertical-align: middle;
      white-space: nowrap;
    }
    th {
      background: #eef2f7;
      color: #344054;
      font-size: 12px;
      font-weight: 650;
      letter-spacing: .04em;
      text-transform: uppercase;
    }
    th.sortable {
      cursor: pointer;
      user-select: none;
    }
    th.sortable button {
      min-height: 0;
      width: 100%;
      padding: 0;
      border: 0;
      background: transparent;
      color: inherit;
      text-align: left;
      text-transform: inherit;
      letter-spacing: inherit;
      font: inherit;
      cursor: pointer;
    }
    tbody tr:last-child td { border-bottom: 0; }
    .name {
      font-weight: 650;
    }
    .pill {
      display: inline-flex;
      align-items: center;
      min-height: 24px;
      padding: 0 8px;
      border-radius: 999px;
      background: #eef2f7;
      color: #344054;
      font-size: 12px;
      font-weight: 600;
    }
    .pill.stale {
      background: #fff4d6;
      color: var(--stale);
    }
    .switch {
      position: relative;
      display: inline-flex;
      width: 46px;
      height: 26px;
    }
    .switch input {
      opacity: 0;
      width: 0;
      height: 0;
    }
    .slider {
      position: absolute;
      inset: 0;
      border-radius: 999px;
      background: var(--off);
      transition: .16s;
    }
    .slider::before {
      content: "";
      position: absolute;
      width: 20px;
      height: 20px;
      left: 3px;
      top: 3px;
      border-radius: 50%;
      background: #fff;
      transition: .16s;
      box-shadow: 0 1px 2px rgba(0, 0, 0, .24);
    }
    .switch input:checked + .slider {
      background: var(--on);
    }
    .switch input:checked + .slider::before {
      transform: translateX(20px);
    }
    .status {
      min-height: 20px;
      margin-top: 10px;
      color: var(--muted);
      font-size: 13px;
    }
    .modal-backdrop {
      position: fixed;
      inset: 0;
      display: grid;
      place-items: center;
      padding: 20px;
      background: rgba(15, 23, 42, .42);
      z-index: 20;
    }
    .modal-backdrop[hidden] {
      display: none;
    }
    .status-modal {
      width: min(560px, 100%);
      max-height: min(680px, calc(100vh - 40px));
      overflow: hidden;
      background: var(--panel);
      border: 1px solid var(--line);
      border-radius: 8px;
      box-shadow: 0 24px 72px rgba(15, 23, 42, .28);
      display: grid;
      grid-template-rows: auto auto 1fr;
    }
    .status-modal-header {
      display: flex;
      justify-content: space-between;
      align-items: center;
      gap: 12px;
      padding: 16px 18px 10px;
    }
    .status-modal-title {
      display: flex;
      align-items: center;
      gap: 9px;
      font-size: 18px;
      font-weight: 700;
    }
    .status-indicator {
      width: 12px;
      height: 12px;
      border-radius: 50%;
      background: var(--muted);
      box-shadow: 0 0 0 4px #eef2f7;
    }
    .status-indicator.running {
      background: var(--accent);
      animation: pulse 1.2s ease-in-out infinite;
    }
    .status-indicator.success {
      background: var(--on);
    }
    .status-indicator.failed {
      background: #cf222e;
    }
    @keyframes pulse {
      0%, 100% { transform: scale(1); opacity: .8; }
      50% { transform: scale(1.18); opacity: 1; }
    }
    .status-close {
      min-height: 32px;
      min-width: 32px;
      padding: 0;
      font-size: 20px;
      line-height: 1;
    }
    .status-modal-body {
      padding: 0 18px 16px;
    }
    .status-message {
      color: var(--muted);
      min-height: 20px;
      margin-bottom: 10px;
    }
    .progress-track {
      height: 10px;
      overflow: hidden;
      border-radius: 999px;
      background: #eef2f7;
      border: 1px solid var(--line);
    }
    .progress-fill {
      height: 100%;
      width: 0%;
      background: var(--accent);
      transition: width .18s ease;
    }
    .progress-track.indeterminate .progress-fill {
      width: 36%;
      animation: slide 1.1s ease-in-out infinite;
    }
    @keyframes slide {
      0% { transform: translateX(-110%); }
      100% { transform: translateX(300%); }
    }
    .progress-meta {
      display: flex;
      justify-content: space-between;
      gap: 12px;
      min-height: 20px;
      margin-top: 8px;
      color: var(--muted);
      font-size: 13px;
    }
    .status-output {
      margin: 0;
      padding: 12px 18px 16px;
      border-top: 1px solid var(--line);
      overflow: auto;
      max-height: 260px;
      background: #0f172a;
      color: #dbeafe;
      font: 12px Consolas, monospace;
      white-space: pre-wrap;
    }
    @media (max-width: 820px) {
      header {
        display: block;
      }
      .toolbar {
        grid-template-columns: 1fr 1fr;
      }
      .toolbar input {
        grid-column: 1 / -1;
      }
    }
  </style>
</head>
<body>
  <main>
    <header>
      <div>
        <h1>wow-profile Roster</h1>
        <div class="subtle" id="path"></div>
      </div>
      <div class="header-actions">
        <button id="home" type="button">Account Summary</button>
        <button id="discover" type="button">Discover</button>
        <button class="primary" id="refresh" type="button">Refresh</button>
      </div>
    </header>

    <section class="stats">
      <div class="stat"><div class="stat-label">Characters</div><div class="stat-value" id="total">0</div></div>
      <div class="stat"><div class="stat-label">Enabled</div><div class="stat-value" id="enabled">0</div></div>
      <div class="stat"><div class="stat-label">Visible</div><div class="stat-value" id="visible">0</div></div>
    </section>

    <section class="toolbar">
      <input id="search" type="search" placeholder="Search characters or realms">
      <select id="realm"></select>
      <select id="state">
        <option value="all">All states</option>
        <option value="enabled">Enabled</option>
        <option value="disabled">Disabled</option>
        <option value="stale">Stale</option>
      </select>
      <button id="enable-visible" type="button">Enable Visible</button>
      <button id="disable-visible" type="button">Disable Visible</button>
    </section>

    <div class="table-wrap">
      <table>
        <thead>
          <tr>
            <th>Enabled</th>
            <th class="sortable"><button id="sort-name" type="button">Character</button></th>
            <th class="sortable"><button id="sort-realm" type="button">Realm</button></th>
            <th>Region</th>
            <th>Status</th>
          </tr>
        </thead>
        <tbody id="rows"></tbody>
      </table>
    </div>
    <div class="status" id="status"></div>
  </main>
  <div class="modal-backdrop" id="status-modal-backdrop" hidden>
    <section class="status-modal" role="dialog" aria-modal="true" aria-labelledby="status-modal-title">
      <div class="status-modal-header">
        <div class="status-modal-title">
          <span class="status-indicator" id="status-indicator"></span>
          <span id="status-modal-title">Working</span>
        </div>
        <button class="status-close" id="status-close" type="button" aria-label="Close status">x</button>
      </div>
      <div class="status-modal-body">
        <div class="status-message" id="status-message"></div>
        <div class="progress-track" id="progress-track"><div class="progress-fill" id="progress-fill"></div></div>
        <div class="progress-meta">
          <span id="progress-count"></span>
          <span id="progress-label"></span>
        </div>
      </div>
      <pre class="status-output" id="status-output"></pre>
    </section>
  </div>

  <script>
    let characters = [];
    let filtered = [];
    let sortField = "realm";
    let sortDirection = "asc";

    const els = {
      path: document.getElementById("path"),
      total: document.getElementById("total"),
      enabled: document.getElementById("enabled"),
      visible: document.getElementById("visible"),
      search: document.getElementById("search"),
      realm: document.getElementById("realm"),
      state: document.getElementById("state"),
      rows: document.getElementById("rows"),
      status: document.getElementById("status"),
      statusModalBackdrop: document.getElementById("status-modal-backdrop"),
      statusModalTitle: document.getElementById("status-modal-title"),
      statusIndicator: document.getElementById("status-indicator"),
      statusClose: document.getElementById("status-close"),
      statusMessage: document.getElementById("status-message"),
      progressTrack: document.getElementById("progress-track"),
      progressFill: document.getElementById("progress-fill"),
      progressCount: document.getElementById("progress-count"),
      progressLabel: document.getElementById("progress-label"),
      statusOutput: document.getElementById("status-output"),
      home: document.getElementById("home"),
      refresh: document.getElementById("refresh"),
      discover: document.getElementById("discover"),
      sortName: document.getElementById("sort-name"),
      sortRealm: document.getElementById("sort-realm"),
      enableVisible: document.getElementById("enable-visible"),
      disableVisible: document.getElementById("disable-visible"),
    };

    function setStatus(message) {
      els.status.textContent = message || "";
    }

    function showStatusModal(title, message, state = "running") {
      els.statusModalTitle.textContent = title;
      els.statusMessage.textContent = message || "";
      els.statusIndicator.className = "status-indicator " + state;
      els.statusModalBackdrop.hidden = false;
    }

    function closeStatusModal() {
      els.statusModalBackdrop.hidden = true;
    }

    function updateStatusModal(title, status, runningMessage, doneMessage, failedMessage) {
      const progress = status.progress || {};
      const state = status.running ? "running" : (status.returncode === 0 ? "success" : "failed");
      const message = status.running
        ? runningMessage
        : (status.returncode === 0 ? doneMessage : failedMessage);
      showStatusModal(title, message, state);

      if (progress.total) {
        const current = progress.current || 0;
        const percent = progress.percent ?? Math.round((current / progress.total) * 100);
        els.progressTrack.classList.remove("indeterminate");
        els.progressFill.style.width = `${Math.max(0, Math.min(100, percent))}%`;
        els.progressCount.textContent = `${current} of ${progress.total} characters`;
        els.progressLabel.textContent = progress.label || "";
      } else {
        els.progressTrack.classList.add("indeterminate");
        els.progressFill.style.width = "";
        els.progressCount.textContent = "";
        els.progressLabel.textContent = "";
      }

      const output = status.output || "";
      els.statusOutput.textContent = output.split("\n").slice(-20).join("\n");
      els.statusOutput.scrollTop = els.statusOutput.scrollHeight;
      els.statusClose.disabled = status.running;
    }

    function escapeHtml(value) {
      return String(value ?? "").replace(/[&<>"']/g, ch => ({
        "&": "&amp;",
        "<": "&lt;",
        ">": "&gt;",
        '"': "&quot;",
        "'": "&#39;",
      }[ch]));
    }

    function populateRealms() {
      const current = els.realm.value;
      const realms = [...new Set(characters.map(c => c.realm).filter(Boolean))].sort();
      els.realm.innerHTML = '<option value="all">All realms</option>' +
        realms.map(realm => `<option value="${escapeHtml(realm)}">${escapeHtml(realm)}</option>`).join("");
      els.realm.value = realms.includes(current) ? current : "all";
    }

    function applyFilters() {
      const query = els.search.value.trim().toLowerCase();
      const realm = els.realm.value;
      const state = els.state.value;
      filtered = characters.filter(character => {
        const matchesQuery = !query ||
          character.name.toLowerCase().includes(query) ||
          character.realm.toLowerCase().includes(query);
        const matchesRealm = realm === "all" || character.realm === realm;
        const matchesState =
          state === "all" ||
          (state === "enabled" && character.enabled) ||
          (state === "disabled" && !character.enabled) ||
          (state === "stale" && character.stale);
        return matchesQuery && matchesRealm && matchesState;
      });
      filtered.sort((left, right) => {
        const primary = compareText(left[sortField], right[sortField]);
        const result = primary || compareText(left.name, right.name) || compareText(left.realm, right.realm);
        return sortDirection === "asc" ? result : -result;
      });
      render();
    }

    function compareText(left, right) {
      return String(left ?? "").localeCompare(String(right ?? ""), undefined, { sensitivity: "base" });
    }

    function setSort(field) {
      if (sortField === field) {
        sortDirection = sortDirection === "asc" ? "desc" : "asc";
      } else {
        sortField = field;
        sortDirection = "asc";
      }
      updateSortLabels();
      applyFilters();
    }

    function updateSortLabels() {
      els.sortName.textContent = "Character" + (sortField === "name" ? (sortDirection === "asc" ? " ↑" : " ↓") : "");
      els.sortRealm.textContent = "Realm" + (sortField === "realm" ? (sortDirection === "asc" ? " ↑" : " ↓") : "");
    }

    function render() {
      els.total.textContent = characters.length;
      els.enabled.textContent = characters.filter(c => c.enabled).length;
      els.visible.textContent = filtered.length;
      els.rows.innerHTML = filtered.map(character => `
        <tr>
          <td>
            <label class="switch" title="${character.enabled ? "Enabled" : "Disabled"}">
              <input type="checkbox" data-id="${escapeHtml(character.identity)}" ${character.enabled ? "checked" : ""}>
              <span class="slider"></span>
            </label>
          </td>
          <td class="name">${escapeHtml(character.name)}</td>
          <td>${escapeHtml(character.realm)}</td>
          <td>${escapeHtml(character.region)}</td>
          <td>${character.stale ? '<span class="pill stale">Stale</span>' : '<span class="pill">Current</span>'}</td>
        </tr>
      `).join("");
      for (const input of els.rows.querySelectorAll("input[type=checkbox]")) {
        input.addEventListener("change", event => {
          setEnabled(event.target.dataset.id, event.target.checked);
        });
      }
    }

    async function api(path, options = {}) {
      const response = await fetch(path, {
        headers: { "Content-Type": "application/json" },
        ...options,
      });
      if (!response.ok) {
        const text = await response.text();
        throw new Error(text || `HTTP ${response.status}`);
      }
      return response.json();
    }

    async function load(message = "Loaded characters.yaml") {
      setStatus("Loading roster...");
      const data = await api("/api/characters");
      characters = data.characters;
      els.path.textContent = data.path;
      populateRealms();
      applyFilters();
      setStatus(message);
    }

    async function discover() {
      els.discover.disabled = true;
      setStatus("Starting Battle.net discovery...");
      showStatusModal("Discovering Characters", "Starting Battle.net discovery...", "running");
      await api("/api/discover", { method: "POST", body: "{}" });
      pollDiscover();
    }

    async function pollDiscover() {
      try {
        const status = await api("/api/discover/status");
        if (status.running || status.returncode !== null) {
          updateStatusModal(
            "Discovering Characters",
            status,
            "Discovery is running. Complete the Battle.net browser authorization if prompted.",
            "Discovery completed and roster reloaded.",
            "Discovery failed."
          );
        }
        if (status.running) {
          els.discover.disabled = true;
          setStatus("Discovery is running. Complete the Battle.net browser authorization if prompted.");
          window.setTimeout(pollDiscover, 1500);
          return;
        }

        els.discover.disabled = false;
        if (status.returncode === 0) {
          await load();
          setStatus("Discovery completed and roster reloaded.");
        } else if (status.returncode !== null) {
          setStatus("Discovery failed. " + (status.output || "").slice(-500));
        }
      } catch (error) {
        els.discover.disabled = false;
        setStatus(error.message);
      }
    }

    async function updateProfiles() {
      els.refresh.disabled = true;
      setStatus("Starting profile update for enabled characters...");
      showStatusModal("Updating Profiles", "Starting profile update for enabled characters...", "running");
      await api("/api/update", { method: "POST", body: "{}" });
      pollUpdate();
    }

    async function pollUpdate() {
      try {
        const status = await api("/api/update/status");
        if (status.running || status.returncode !== null) {
          updateStatusModal(
            "Updating Profiles",
            status,
            "Profile update is running.",
            "Profile update completed and roster reloaded.",
            "Profile update failed."
          );
        }
        if (status.running) {
          els.refresh.disabled = true;
          const progress = status.progress || {};
          setStatus(progress.total ? `Updating ${progress.current} of ${progress.total}: ${progress.label || ""}` : "Profile update is running.");
          window.setTimeout(pollUpdate, 1500);
          return;
        }

        els.refresh.disabled = false;
        if (status.returncode === 0) {
          await load("Profile update completed and roster reloaded.");
        } else if (status.returncode !== null) {
          setStatus("Profile update failed. " + (status.output || "").slice(-500));
        }
      } catch (error) {
        els.refresh.disabled = false;
        setStatus(error.message);
      }
    }

    async function setEnabled(identity, enabled) {
      setStatus("Saving...");
      const data = await api("/api/characters/enabled", {
        method: "POST",
        body: JSON.stringify({ identity, enabled }),
      });
      characters = data.characters;
      populateRealms();
      applyFilters();
      setStatus("Saved characters.yaml");
    }

    async function setVisible(enabled) {
      if (!filtered.length) return;
      setStatus("Saving visible characters...");
      for (const character of filtered) {
        if (character.enabled !== enabled) {
          await api("/api/characters/enabled", {
            method: "POST",
            body: JSON.stringify({ identity: character.identity, enabled }),
          });
        }
      }
      await load();
      setStatus(enabled ? "Enabled visible characters" : "Disabled visible characters");
    }

    els.search.addEventListener("input", applyFilters);
    els.realm.addEventListener("change", applyFilters);
    els.state.addEventListener("change", applyFilters);
    els.home.addEventListener("click", () => { window.location.href = "/"; });
    els.statusClose.addEventListener("click", closeStatusModal);
    els.refresh.addEventListener("click", updateProfiles);
    els.discover.addEventListener("click", discover);
    els.sortName.addEventListener("click", () => setSort("name"));
    els.sortRealm.addEventListener("click", () => setSort("realm"));
    els.enableVisible.addEventListener("click", () => setVisible(true));
    els.disableVisible.addEventListener("click", () => setVisible(false));

    updateSortLabels();
    load().catch(error => setStatus(error.message));
    pollDiscover();
    pollUpdate();
  </script>
</body>
</html>
"""


class CommandState:
    def __init__(self, args):
        self.args = args
        self.lock = threading.Lock()
        self.running = False
        self.returncode = None
        self.output = ""
        self.progress = {}

    def start(self):
        with self.lock:
            if self.running:
                return False
            self.running = True
            self.returncode = None
            self.output = ""
            self.progress = {}

        thread = threading.Thread(target=self._run, daemon=True)
        thread.start()
        return True

    def _run(self):
        try:
            process = subprocess.Popen(
                [sys.executable, "wow_profile.py", *self.args],
                cwd=Path.cwd(),
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                bufsize=1,
            )
            if process.stdout:
                for line in process.stdout:
                    self.append_output(line.rstrip())
            returncode = process.wait()
            with self.lock:
                self.returncode = returncode
        except Exception as exc:
            with self.lock:
                self.returncode = 1
                self.output = str(exc)
        finally:
            with self.lock:
                self.running = False

    def append_output(self, line):
        if not line:
            return
        progress = self.parse_progress(line)
        with self.lock:
            self.output = f"{self.output}\n{line}".strip()
            if progress:
                self.progress.update(progress)

    def parse_progress(self, line):
        return {}

    def snapshot(self):
        with self.lock:
            return {
                "running": self.running,
                "returncode": self.returncode,
                "output": self.output,
                "progress": dict(self.progress),
            }


class DiscoverState(CommandState):
    def __init__(self):
        super().__init__(["discover"])


class UpdateState(CommandState):
    PROGRESS_PATTERN = re.compile(r"^Updating \[(\d+)/(\d+)\] (.+)\.\.\.$")

    def __init__(self):
        super().__init__(["update"])

    def parse_progress(self, line):
        match = self.PROGRESS_PATTERN.match(line)
        if not match:
            return {}
        current = int(match.group(1))
        total = int(match.group(2))
        return {
            "current": current,
            "total": total,
            "label": match.group(3),
            "percent": round((current / total) * 100) if total else 0,
        }


class RosterUIHandler(BaseHTTPRequestHandler):
    server_version = "WowProfileRosterUI/1.0"

    def do_GET(self):
        parsed = urlparse(self.path)
        if parsed.path == "/":
            if ACCOUNT_SUMMARY_FILE.exists():
                self.send_text(
                    ACCOUNT_SUMMARY_FILE.read_text(encoding="utf-8"),
                    "text/html; charset=utf-8",
                )
                return
            self.send_text(HTML, "text/html; charset=utf-8")
            return
        if parsed.path == "/roster-ui":
            self.send_text(HTML, "text/html; charset=utf-8")
            return
        if parsed.path == "/api/characters":
            self.send_json(roster_payload(self.server.roster_path))
            return
        if parsed.path == "/api/discover/status":
            self.send_json(self.server.discover_state.snapshot())
            return
        if parsed.path == "/api/update/status":
            self.send_json(self.server.update_state.snapshot())
            return
        self.send_error(404, "Not found")

    def do_POST(self):
        parsed = urlparse(self.path)
        if parsed.path == "/api/characters/enabled":
            payload = self.read_json()
            identity = payload.get("identity")
            if not identity:
                self.send_error(400, "Missing identity")
                return
            try:
                data = set_character_enabled(
                    identity,
                    payload.get("enabled") is True,
                    self.server.roster_path,
                )
            except KeyError as exc:
                self.send_error(404, str(exc))
                return
            self.send_json(data)
            return
        if parsed.path == "/api/characters/enabled-all":
            payload = self.read_json()
            self.send_json(set_all_enabled(
                payload.get("enabled") is True,
                payload.get("realm"),
                self.server.roster_path,
            ))
            return
        if parsed.path == "/api/discover":
            started = self.server.discover_state.start()
            payload = self.server.discover_state.snapshot()
            payload["started"] = started
            self.send_json(payload)
            return
        if parsed.path == "/api/update":
            started = self.server.update_state.start()
            payload = self.server.update_state.snapshot()
            payload["started"] = started
            self.send_json(payload)
            return
        self.send_error(404, "Not found")

    def read_json(self):
        length = int(self.headers.get("Content-Length") or 0)
        if length <= 0:
            return {}
        return json.loads(self.rfile.read(length).decode("utf-8"))

    def send_json(self, data):
        encoded = json.dumps(data).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(encoded)))
        self.end_headers()
        self.wfile.write(encoded)

    def send_text(self, text, content_type):
        encoded = text.encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(encoded)))
        self.end_headers()
        self.wfile.write(encoded)

    def log_message(self, format, *args):
        return


def run_roster_ui(host=DEFAULT_HOST, port=DEFAULT_PORT, path=CHARACTERS_FILE):
    server = ThreadingHTTPServer((host, port), RosterUIHandler)
    server.roster_path = path
    server.discover_state = DiscoverState()
    server.update_state = UpdateState()
    url = f"http://{host}:{port}/"
    threading.Timer(0.25, lambda: webbrowser.open(url)).start()
    print(f"Roster UI running at {url}")
    print("Press Ctrl+C to stop.")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("")
    finally:
        server.server_close()
    return 0
