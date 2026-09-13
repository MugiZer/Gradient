const { contextBridge, ipcRenderer } = require('electron');

contextBridge.exposeInMainWorld('gradientDesktop', {
  pointer: (interactive) => ipcRenderer.send('gradient:pointer', interactive === true),
  proof: (expanded) => ipcRenderer.send('gradient:proof', expanded === true),
  menu: () => ipcRenderer.send('gradient:menu'),
  demoSnapshot: () => ipcRenderer.invoke('gradient:demo'),
  mode: (value) => ipcRenderer.send('gradient:mode', value),
  visibility: (visible) => ipcRenderer.send('gradient:visibility', visible === true),
  onMode: (callback) => {
    const listener = (_event, mode) => callback(mode);
    ipcRenderer.on('gradient:mode', listener);
    return () => ipcRenderer.removeListener('gradient:mode', listener);
  },
  onTeach: (callback) => {
    const listener = () => callback();
    ipcRenderer.on('gradient:teach', listener);
    return () => ipcRenderer.removeListener('gradient:teach', listener);
  },
});
