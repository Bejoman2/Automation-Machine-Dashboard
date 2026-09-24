const { app, BrowserWindow, dialog, ipcMain } = require('electron');
const { spawn, execFileSync } = require('child_process');
const path = require('path');
const http = require('http');

let backendProcess = null;
const BACKEND_PORT = Number(process.env.BACKEND_PORT || 8000);
const BACKEND_URL = `http://127.0.0.1:${BACKEND_PORT}`;

function backendExecutable() {
  if (app.isPackaged) {
    return path.join(process.resourcesPath, 'backend', 'automation-dashboard-backend.exe');
  }
  return path.join(__dirname, '..', 'backend', 'dist', 'automation-dashboard-backend.exe');
}

function waitForBackend(timeoutMs = 30000) {
  const started = Date.now();
  return new Promise((resolve, reject) => {
    const check = () => {
      const req = http.get(`${BACKEND_URL}/api/health`, (res) => {
        res.resume();
        if (res.statusCode === 200) return resolve();
        retry();
      });
      req.on('error', retry);
      req.setTimeout(1000, () => { req.destroy(); retry(); });
    };
    const retry = () => {
      if (Date.now() - started > timeoutMs) {
        reject(new Error(`Backend did not start within ${timeoutMs / 1000}s`));
        return;
      }
      setTimeout(check, 250);
    };
    check();
  });
}

function startBackend() {
  const exe = backendExecutable();
  const appData = path.join(app.getPath('appData'), 'WIK', 'AutomationMachineDashboard');
  const fs = require('fs');
  fs.mkdirSync(appData, { recursive: true });
  const logPath = path.join(appData, 'backend.log');
  const log = fs.createWriteStream(logPath, { flags: 'a' });

  backendProcess = spawn(exe, [], {
    windowsHide: true,
    stdio: ['ignore', 'pipe', 'pipe'],
    env: {
      ...process.env,
      BACKEND_PORT: String(BACKEND_PORT),
      DASHBOARD_APP_DATA: appData,
    },
  });

  backendProcess.stdout.pipe(log);
  backendProcess.stderr.pipe(log);

  backendProcess.on('error', (err) => {
    log.write(`\n[Electron] Backend spawn error: ${err.stack || err}\n`);
    dialog.showErrorBox('Backend startup failed', `${err.message}\n\nExpected backend:\n${exe}\n\nLog:\n${logPath}`);
  });

  backendProcess.on('exit', (code, signal) => {
    log.write(`\n[Electron] Backend exited. code=${code}, signal=${signal}\n`);
  });
}

function stopBackend() {
  if (!backendProcess) return;

  const pid = backendProcess.pid;
  if (!pid) {
    backendProcess = null;
    return;
  }

  console.log(`[Electron] Terminating backend process tree PID ${pid}...`);

  // On Windows, child_process.kill() is not reliable for terminating the
  // complete PyInstaller/uvicorn process tree. Use taskkill /T /F so the
  // listener on port 8000 is actually released when Electron closes.
  if (process.platform === 'win32') {
    try {
      execFileSync('taskkill', ['/PID', String(pid), '/T', '/F'], {
        windowsHide: true,
        stdio: 'ignore',
      });
      console.log(`[Electron] Backend process tree ${pid} terminated.`);
    } catch (err) {
      // Process may already have exited. Do not block Electron shutdown.
      console.log(`[Electron] taskkill for PID ${pid} returned: ${err.message}`);
    }
  } else {
    try { backendProcess.kill('SIGTERM'); } catch (_) {}
  }

  backendProcess = null;
}

async function createWindow() {
  const win = new BrowserWindow({
    width: 1440,
    height: 900,
    minWidth: 1100,
    minHeight: 700,
    backgroundColor: '#0a0f0e',
    webPreferences: {
      preload: path.join(__dirname, 'preload.cjs'),
      contextIsolation: true,
      nodeIntegration: false,
    },
  });

  const devUrl = process.env.VITE_DEV_SERVER_URL;
  if (devUrl) {
    await win.loadURL(devUrl);
    return;
  }

  await waitForBackend();
  await win.loadFile(path.join(__dirname, 'dist', 'index.html'));
}

ipcMain.handle('select-folder', async () => {
  const result = await dialog.showOpenDialog({
    properties: ['openDirectory'],
    title: 'Select Hikrobot CSV Folder',
  });
  if (result.canceled || !result.filePaths.length) return { cancelled: true };
  return { cancelled: false, path: result.filePaths[0] };
});

app.whenReady().then(async () => {
  if (!process.env.VITE_DEV_SERVER_URL || app.isPackaged) startBackend();
  try {
    await createWindow();
  } catch (err) {
    dialog.showErrorBox('Application startup failed', err.stack || String(err));
    app.quit();
  }

  app.on('activate', () => {
    if (BrowserWindow.getAllWindows().length === 0) createWindow();
  });
});

app.on('before-quit', stopBackend);
app.on('will-quit', stopBackend);
app.on('window-all-closed', () => {
  stopBackend();
  if (process.platform !== 'darwin') app.quit();
});
