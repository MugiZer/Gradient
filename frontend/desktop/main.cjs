const { app, BrowserWindow, Menu, Tray, nativeImage, ipcMain, screen, dialog, shell } = require('electron');
const { spawn } = require('node:child_process');
const { join, resolve } = require('node:path');
const { existsSync, mkdirSync, writeFileSync, openSync } = require('node:fs');
const { setTimeout: delay } = require('node:timers/promises');
const { readDemo, serveDesktop } = require('./bridge.cjs');

const repo = resolve(__dirname, '../..');
const endpoint = 'http://127.0.0.1:8795';
let win, tray, backend;
let expanded = false;
let interactive = false;
let quitting = false;
let desktopUrl;
let mode = 'live';
let hiddenByUser = false;
let visibilityTimer;
// Demo takeover: sprite click types the staged lines into the window under the companion.
let takeover = false;
let takeoverAbort = false;
let takeoverPs = null;
// Timeline (tune for the room; tightened in editing): MSG1 at t=0, exhibit at
// t=MSG2_DELAY-HTML_LEAD, MSG2 (correction) at t=MSG2_DELAY, then Lesson found pops.
const DEMO_MSG2_DELAY_MS = 60000;
const DEMO_HTML_LEAD_MS = 10000;
const DEMO_MSG1 = 'in snapshot.py implement publish_snapshot(path, data) so a separate process can read it after';
const DEMO_MSG2 = 'That only returns a description. Persist the data so a fresh reader observes it. If I ask for a preview, leave the file unchanged.';
// Keep byte-identical with frontend/output/playwright/demo-takeover.ps1 ($MSG1/$MSG2).
// The exhibit pops between the two prompts so it sits in the demo before the correction.
// Codex opens it from its reply link in its side browser (never the system browser);
// this hold is the presenter's window to click that link.
const DEMO_HTML_HOLD_MS = 15000;
app.setName('Gradient');
app.setPath('userData', join(app.getPath('appData'), 'Gradient'));

if (!app.requestSingleInstanceLock()) app.quit();
else {
  app.on('second-instance', () => showGradient());
  app.whenReady().then(start).catch((error) => {
    dialog.showErrorBox('Gradient could not start', String(error));
    app.quit();
  });
}

function position() {
  const area = screen.getPrimaryDisplay().workArea;
  const width = expanded ? area.width : Math.min(380, area.width);
  const height = expanded ? area.height : Math.min(620, area.height);
  const bounds = { x: area.x + area.width - width, y: area.y + area.height - height, width, height };
  const previous = win.getBounds();
  if (Object.keys(bounds).some((key) => bounds[key] !== previous[key])) win.setBounds(bounds);
}

function keepVisible() {
  if (!win || win.isDestroyed() || hiddenByUser || quitting || takeover) return;
  if (win.isFullScreen()) win.setFullScreen(false);
  if (win.isMinimized() || win.isMaximized()) win.restore();
  position();
  win.setAlwaysOnTop(true, 'screen-saver');
  if (!win.isVisible()) win.showInactive();
  win.moveTop();
}

function showGradient() {
  hiddenByUser = false;
  keepVisible();
}

function hideGradient() {
  hiddenByUser = true;
  win.hide();
}

function controls() {
  return Menu.buildFromTemplate([
    { label: 'Teach lesson', click: () => { showGradient(); win.webContents.send('gradient:teach'); } },
    { label: 'Reset demo', click: () => { showGradient(); win.webContents.send('gradient:demo-reset'); } },
    ...[['live', 'Live'], ['demo', 'Demo']].map(([value, label]) => ({ label, type: 'radio', checked: mode === value, click: () => selectMode(value) })),
    { type: 'separator' },
    { label: 'Show Gradient', click: showGradient },
    { label: 'Hide Gradient', click: hideGradient },
    { type: 'separator' },
    { label: 'Quit Gradient', click: () => app.quit() },
  ]);
}

function selectMode(value) {
  if (!['live', 'demo'].includes(value)) return;
  mode = value;
  showGradient();
  win.webContents.send('gradient:mode', mode);
  tray?.setContextMenu(controls());
}

async function start() {
  const data = app.getPath('userData');
  mkdirSync(data, { recursive: true });
  if (!existsSync(join(repo, 'frontend/dist/index.html'))) throw new Error('Build the frontend first: npm run build');
  // Own an isolated backend so closing the companion cannot stop another Gradient workflow.
  try {
    await fetch(`${endpoint}/health`, { signal: AbortSignal.timeout(500) });
    throw new Error('Port 8795 is already in use. Close the previous companion before restarting.');
  } catch (error) { if (error.message.startsWith('Port ')) throw error; }
  const python = join(repo, '.venv', process.platform === 'win32' ? 'Scripts/python.exe' : 'bin/python');
  const log = openSync(join(data, 'backend.log'), 'a');
  backend = spawn(python, ['-m', 'gradient.main', '--port', '8795'], {
    cwd: repo, windowsHide: true, stdio: ['ignore', log, log],
    env: { ...process.env, GRADIENT_RUNS_DIR: join(repo, 'runs/desktop'), GRADIENT_API_TOKEN: '', GRADIENT_DESKTOP_COMPANION: 'true', PYTHONUNBUFFERED: '1' },
  });
  let launchError;
  backend.on('error', (error) => { launchError = error; });
  let ready = false;
  for (let attempt = 0; attempt < 60; attempt++) {
    if (launchError || backend.exitCode !== null) break;
    try {
      const response = await fetch(`${endpoint}/health`, { signal: AbortSignal.timeout(500) });
      if (response.ok) { ready = true; break; }
    } catch { /* Server startup has not bound its loopback socket yet. */ }
    await delay(250);
  }
  if (!ready) console.error(`Backend unavailable; offline walkthrough remains available. See ${join(data, 'backend.log')}`);
  writeFileSync(join(data, 'connection.json'), JSON.stringify({ endpoint, repo }));
  win = new BrowserWindow({
    title: 'Gradient', width: 380, height: 620, frame: false, transparent: true,
    backgroundColor: '#00000000', alwaysOnTop: true, skipTaskbar: true,
    resizable: false, maximizable: false, minimizable: false, fullscreenable: false, hasShadow: false, show: false,
    webPreferences: { preload: join(__dirname, 'preload.cjs'), nodeIntegration: false, contextIsolation: true, sandbox: true },
  });
  position();
  win.on('hide', () => { if (!hiddenByUser && !takeover) setImmediate(keepVisible); });
  // Renderer close buttons only collapse surfaces; an OS-level close must never kill the companion.
  win.on('close', (event) => { if (!quitting) { event.preventDefault(); showGradient(); } });
  win.on('unresponsive', () => { if (!quitting) win.webContents.reload(); });
  win.on('minimize', () => setImmediate(keepVisible));
  win.on('always-on-top-changed', (_event, top) => { if (!top) setImmediate(keepVisible); });
  win.on('closed', () => clearInterval(visibilityTimer));
  win.webContents.on('render-process-gone', () => { if (!quitting) win.webContents.reload(); });
  win.setIgnoreMouseEvents(true, { forward: true });
  win.webContents.session.setPermissionRequestHandler((_contents, _permission, callback) => callback(false));
  win.webContents.setWindowOpenHandler(({ url }) => {
    if (/^https:\/\/app\.primeintellect\.ai\/dashboard\/training(?:\/[a-zA-Z0-9_-]+)?$/.test(url)) {
      void shell.openExternal(url);
      return { action: 'deny' };
    }
    // Artifact previews stay local and never replace the ambient surface.
    if (!desktopUrl || !['/runs/', '/evidence/'].some((path) => url.startsWith(`${new URL(desktopUrl).origin}${path}`))) return { action: 'deny' };
    return { action: 'allow', overrideBrowserWindowOptions: { width: 720, height: 540, autoHideMenuBar: true, webPreferences: { nodeIntegration: false, contextIsolation: true, sandbox: true } } };
  });
  win.webContents.on('will-navigate', (event, url) => { if (url !== desktopUrl) event.preventDefault(); });
  const valid = (event) => event.sender === win.webContents && event.senderFrame === win.webContents.mainFrame;
  ipcMain.handle('gradient:demo', (event) => { if (valid(event)) return readDemo(repo); throw new Error('Invalid sender'); });
  ipcMain.handle('gradient:mode:get', (event) => { if (valid(event)) return mode; throw new Error('Invalid sender'); });
  ipcMain.on('gradient:mode', (event, value) => { if (valid(event)) selectMode(value); });
  ipcMain.on('gradient:visibility', (event, visible) => { if (valid(event)) visible === false ? hideGradient() : showGradient(); });
  ipcMain.on('gradient:pointer', (event, value) => {
    if (!valid(event) || interactive === value) return;
    interactive = value === true;
    win.setIgnoreMouseEvents(!interactive, { forward: true });
  });
  ipcMain.on('gradient:proof', (event, value) => {
    if (!valid(event) || expanded === value) return;
    expanded = value === true;
    position();
  });
  ipcMain.on('gradient:menu', (event) => { if (valid(event)) controls().popup({ window: win }); });
  ipcMain.on('gradient:demo-type', () => {
    if (takeover || !win || win.isDestroyed()) return;
    takeover = true;
    takeoverAbort = false;
    const aborted = () => takeoverAbort;
    const type = (text) => new Promise((done, failed) => {
      const script = `Add-Type -AssemblyName System.Windows.Forms;`
        + `$t='${text.replace(/'/g, "''")}';`
        + `foreach($ch in $t.ToCharArray()){$k=[string]$ch;`
        + `if($k -match '[\\+\\^%~\\(\\)\\[\\]\\{\\}]'){$k='{'+$k+'}'}`
        + `[System.Windows.Forms.SendKeys]::SendWait($k);Start-Sleep -Milliseconds 12}`;
      const ps = spawn('powershell.exe', ['-NoProfile', '-Command', script], { windowsHide: true });
      takeoverPs = ps;
      ps.on('error', failed);
      ps.on('close', (code) => { takeoverPs = null; (code === 0 && !takeoverAbort ? done() : failed(new Error(`SendKeys exited ${code}`))); });
    });
    (async () => {
      try {
        win.hide(); // focus falls back to the window under the companion (the Codex box)
        await delay(600);
        if (aborted()) return;
        await type(DEMO_MSG1);
        takeoverPs = spawn('powershell.exe', ['-NoProfile', '-Command',
          `Add-Type -AssemblyName System.Windows.Forms;[System.Windows.Forms.SendKeys]::SendWait('{ENTER}')`], { windowsHide: true });
        await new Promise((done, failed) => {
          takeoverPs.on('error', failed);
          takeoverPs.on('close', (code) => { takeoverPs = null; (code === 0 && !takeoverAbort ? done() : failed(new Error(`SendKeys exited ${code}`))); });
        });
        if (aborted()) return;
        win.showInactive(); // visible again without stealing focus
        await delay(Math.max(0, DEMO_MSG2_DELAY_MS - DEMO_HTML_HOLD_MS));
        if (aborted()) return;
        await delay(DEMO_HTML_HOLD_MS); // presenter opens the exhibit from the Codex reply link
        if (aborted()) return;
        await type(DEMO_MSG2);
        takeoverPs = spawn('powershell.exe', ['-NoProfile', '-Command',
          `Add-Type -AssemblyName System.Windows.Forms;[System.Windows.Forms.SendKeys]::SendWait('{ENTER}')`], { windowsHide: true });
        await new Promise((done, failed) => {
          takeoverPs.on('error', failed);
          takeoverPs.on('close', (code) => { takeoverPs = null; (code === 0 && !takeoverAbort ? done() : failed(new Error(`SendKeys exited ${code}`))); });
        });
        if (aborted()) return;
        await delay(10000); // let the correction settle before Lesson found pops
        if (aborted() || win.isDestroyed()) return;
        win.webContents.send('gradient:teach'); // Lesson found pops after the second prompt
      } catch (error) { if (!takeoverAbort) console.error(`Demo takeover failed: ${String(error)}`); }
      finally { takeover = false; takeoverAbort = false; takeoverPs = null; showGradient(); }
    })();
  });
  ipcMain.on('gradient:demo-abort', () => {
    if (!takeover) return;
    takeoverAbort = true;
    try { takeoverPs?.kill(); } catch { /* already exited */ }
  });
  screen.on('display-metrics-changed', position);
  screen.on('display-removed', position);
  desktopUrl = (await serveDesktop(repo, endpoint)).url;
  await win.loadURL(desktopUrl);
  showGradient();
  visibilityTimer = setInterval(keepVisible, 2000);
  const icon = nativeImage.createFromDataURL('data:image/svg+xml;base64,' + Buffer.from('<svg xmlns="http://www.w3.org/2000/svg" width="32" height="32"><path fill="#666964" d="M16 2C23 0 29 12 29 20C29 34 3 34 3 20C3 13 9 3 16 2Z"/><rect x="10" y="12" width="4" height="8" rx="2" fill="white"/><rect x="18" y="12" width="4" height="8" rx="2" fill="white"/></svg>').toString('base64'));
  // Chromium renders the same SVG if the platform's native tray decoder does not accept SVG.
  tray = new Tray(icon.isEmpty() ? (await win.webContents.capturePage({ x: 326, y: 566, width: 36, height: 36 })).resize({ width: 32, height: 32 }) : icon);
  tray.setToolTip('Gradient');
  tray.setContextMenu(controls());
  tray.on('click', showGradient);
}

app.on('before-quit', (event) => {
  if (quitting || !backend) return;
  event.preventDefault();
  quitting = true;
  clearInterval(visibilityTimer);
  fetch(`${endpoint}/native/close`, { method: 'POST', signal: AbortSignal.timeout(5000) })
    .catch(() => {}).finally(() => { backend.kill(); app.quit(); });
});
app.on('window-all-closed', () => app.quit());
