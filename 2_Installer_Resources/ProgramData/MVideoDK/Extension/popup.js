// popup.js — v8.1 (alineado + reset modo + estado servidor permanente)

const STORAGE_MODE = "MvideoDk_mode";
const STORAGE_FLOAT = "MvideoDk_float_button";   // 👈 nuevo


let CONFIG = null;
let currentMode = "video"; // siempre arranca en VIDEO
let floatEnabled = false;

let baseStatusText = "";
let baseStatusColor = "green";
let tempStatusTimer = null;

// ----------------- utilidades -----------------
function getStorage(keys) {
  return new Promise(res => chrome.storage.local.get(keys, res));
}
function setStorage(obj) {
  return new Promise(res => chrome.storage.local.set(obj, res));
}

async function getFloatEnabled() {
  const items = await getStorage([STORAGE_FLOAT]);
  // OFF por defecto
  return items[STORAGE_FLOAT] === true;
}
async function setFloatEnabled(enabled) {
  await setStorage({ [STORAGE_FLOAT]: !!enabled });
}


// estado de la etiqueta de estado
function applyStatus(text, color) {
  const el = document.getElementById("status");
  if (!el) return;
  el.textContent = text;
  el.style.color = color;
}

function setBaseStatus(text, ok = true) {
  baseStatusText = text;
  baseStatusColor = ok ? "green" : "red";
  applyStatus(baseStatusText, baseStatusColor);
}

function showTempStatus(msg, ok = true, ms = 2200) {
  if (tempStatusTimer) {
    clearTimeout(tempStatusTimer);
    tempStatusTimer = null;
  }
  applyStatus(msg, ok ? "green" : "red");
  tempStatusTimer = setTimeout(() => {
    applyStatus(baseStatusText, baseStatusColor);
  }, ms);
}


// Carga de config_ext.json + config dinámica
async function loadConfig() {
  if (CONFIG) return CONFIG;

  // 1) JSON local
  const url = chrome.runtime.getURL("config_ext.json");
  const res = await fetch(url);
  CONFIG = await res.json();

  // 2) Intentar obtener config dinámica del servidor
  try {
    const base = (CONFIG.server_url || "").replace(/\/+$/, "");
    const resp = await fetch(`${base}/api/ext/config`);
    if (resp.ok) {
      const srv = await resp.json();
      if (srv.server_url) CONFIG.server_url = srv.server_url;
      if (srv.token) CONFIG.token = srv.token;
    }
  } catch (e) {
    console.warn("[EXT] popup.js: No se pudo obtener config dinámica.");
  }

  return CONFIG;
}


// Prueba rápida de conexión al servidor (GET /api/ping)
async function testServer() {
  try {
    const cfg = await loadConfig();
    const base = (cfg.server_url || "").replace(/\/+$/, "");
    const apiPrefix = cfg.api_prefix || "/api";
    const resp = await fetch(`${base}${apiPrefix}/ping`, { method: "GET" });
    return resp.ok;
  } catch {
    return false;
  }
}

// ----------------- eventos UI -----------------
document.addEventListener("DOMContentLoaded", async () => {
  const serverUrlInput      = document.getElementById("serverUrlInput");
  const toggleServerUrlBtn  = document.getElementById("toggleServerUrlBtn");
  const copyServerUrlBtn    = document.getElementById("copyServerUrlBtn");
  const urlInput            = document.getElementById("urlInput");
  const downloadBtn         = document.getElementById("downloadBtn");
  const downloadCurrentBtn  = document.getElementById("downloadCurrentBtn");
  const downloadPlaylistBtn = document.getElementById("downloadPlaylistBtn");
  const modeSwitch          = document.getElementById("modeSwitch");
  const viewQueueBtn        = document.getElementById("viewQueueBtn");
  const openDownloadsBtn    = document.getElementById("openDownloadsBtn");
  const toggleFloatBtn      = document.getElementById("toggleFloatBtn");

  // Cargar config_ext.json
  try {
    const cfg = await loadConfig();
    const base = cfg.server_url || "";
    serverUrlInput.value = base;
    // si config carga ok, de momento no ponemos mensaje; lo hará testServer
  } catch (e) {
    serverUrlInput.value = "ERROR: config_ext.json";
    setBaseStatus("❌ No se pudo leer config_ext.json", false);
  }

  // URL oculta por defecto
  let urlHidden = true;
  serverUrlInput.classList.add("secret-hidden");

  // Modo siempre arranca en VIDEO
  currentMode = "video";
  modeSwitch.textContent = "Modo: Video";

  // Estado inicial del botón flotante
  floatEnabled = await getFloatEnabled();
  updateFloatBtnUi();

  function updateFloatBtnUi() {
    if (!toggleFloatBtn) return;
    toggleFloatBtn.textContent = `Botón flotante: [${floatEnabled ? "ON" : "OFF"}]`;
    toggleFloatBtn.style.backgroundColor = floatEnabled ? "#4caf50" : "#9e9e9e";
  }

  // Mostrar/ocultar URL sin cambiar el ancho del campo
  toggleServerUrlBtn.addEventListener("click", () => {
    urlHidden = !urlHidden;
    if (urlHidden) {
      serverUrlInput.classList.add("secret-hidden");
      toggleServerUrlBtn.textContent = "👁️";
    } else {
      serverUrlInput.classList.remove("secret-hidden");
      toggleServerUrlBtn.textContent = "🙈";
    }
  });

  // Copiar URL al portapapeles (mensaje temporal)
  copyServerUrlBtn.addEventListener("click", async () => {
    try {
      await navigator.clipboard.writeText(serverUrlInput.value);
      showTempStatus("✅ URL del servidor copiada.", true);
    } catch {
      showTempStatus("⚠️ No se pudo copiar la URL.", false);
    }
  });

  // Switch modo Video/Playlist (no se guarda; siempre es local a la apertura)
  modeSwitch.addEventListener("click", () => {
    currentMode = currentMode === "video" ? "playlist" : "video";
    modeSwitch.textContent = currentMode === "video" ? "Modo: Video" : "Modo: Playlist";
  });

  // Helper: resetear modo y limpiar URL tras un envío
  function resetAfterSend() {
    urlInput.value = "";
    currentMode = "video";
    modeSwitch.textContent = "Modo: Video";
  }

  // Toggle botón flotante
  if (toggleFloatBtn) {
    toggleFloatBtn.addEventListener("click", async () => {
      floatEnabled = !floatEnabled;
      await setFloatEnabled(floatEnabled);
      updateFloatBtnUi();

      // Avisar a la pestaña activa
      const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
      if (tab && tab.id) {
        chrome.tabs.sendMessage(tab.id, {
          type: "SET_FLOAT_BUTTON",
          enabled: floatEnabled,
        });
      }
    });
  }

  // Descargar ahora (usa URL del input o de la pestaña)
  downloadBtn.addEventListener("click", async () => {
    let url = urlInput.value.trim();
    if (!url) {
      const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
      url = tab?.url || "";
    }
    if (!url) {
      showTempStatus("❌ No se encontró una URL válida.", false);
      return;
    }

    downloadBtn.disabled = true;
    downloadBtn.textContent = "Enviando...";

    chrome.runtime.sendMessage(
      { type: "DIRECT_DOWNLOAD", url, modo: currentMode },
      () => {
        downloadBtn.disabled = false;
        downloadBtn.textContent = "⬇ Descargar ahora";
        resetAfterSend();
        showTempStatus("Solicitud enviada. Revisa la app MVideoDk.", true);
      }
    );
  });

  // Descargar video actual
  downloadCurrentBtn.addEventListener("click", async () => {
    const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
    const url = tab?.url || "";
    if (!url) {
      showTempStatus("❌ No se encontró URL activa.", false);
      return;
    }

    downloadCurrentBtn.disabled = true;
    downloadCurrentBtn.textContent = "Enviando...";

    chrome.runtime.sendMessage(
      { type: "DIRECT_DOWNLOAD", url, modo: "video" },
      () => {
        downloadCurrentBtn.disabled = false;
        downloadCurrentBtn.textContent = "🎬 Descargar video actual";
        resetAfterSend();  // también volvemos a VIDEO
        showTempStatus("Video en cola (si el servidor está activo).", true);
      }
    );
  });

  // Descargar playlist actual
  downloadPlaylistBtn.addEventListener("click", async () => {
    let url = urlInput.value.trim();
    if (!url) {
      const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
      url = tab?.url || "";
    }
    if (!url) {
      showTempStatus("❌ No se encontró una URL válida.", false);
      return;
    }

    downloadPlaylistBtn.disabled = true;
    downloadPlaylistBtn.textContent = "Enviando...";

    chrome.runtime.sendMessage(
      { type: "DIRECT_DOWNLOAD", url, modo: "playlist" },
      () => {
        downloadPlaylistBtn.disabled = false;
        downloadPlaylistBtn.textContent = "🎵 Descargar playlist actual";
        resetAfterSend();
        showTempStatus("Playlist en cola (si el servidor está activo).", true);
      }
    );
  });

  // Ver cola en el navegador
  viewQueueBtn.addEventListener("click", async () => {
    try {
      const cfg = await loadConfig();
      const base = (cfg.server_url || "").replace(/\/+$/, "");
      const url = `${base}/ext/queue`;  // endpoint que implementarás
      chrome.tabs.create({ url });
    } catch {
      showTempStatus("❌ No se pudo leer config_ext.json", false);
    }
  });

  // Abrir descargas (vía servidor)
  openDownloadsBtn.addEventListener("click", async () => {
    try {
      const cfg = await loadConfig();
      const base = (cfg.server_url || "").replace(/\/+$/, "");
      const url = `${base}/ext/open_downloads`;  // endpoint que implementarás
      chrome.tabs.create({ url });
    } catch {
      showTempStatus("❌ No se pudo leer config_ext.json", false);
    }
  });

  // Test rápido de conexión (al abrir popup) -> define el estado base
  try {
    const alive = await testServer();
    if (alive) {
      setBaseStatus("🟢 Conectado a MVideoDk.", true);
    } else {
      setBaseStatus("🔴 No se pudo conectar. Abre la app MVideoDk.", false);
    }
  } catch {
    // si ya había baseStatus (por error de config), lo dejamos
    if (!baseStatusText) {
      setBaseStatus("🔴 No se pudo comprobar el servidor.", false);
    }
  }
});
