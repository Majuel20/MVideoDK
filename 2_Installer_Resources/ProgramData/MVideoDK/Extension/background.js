let CFG = null;

// Cargar config_ext.json + intentar obtener config dinámica del servidor
async function loadConfig() {
  if (CFG) return CFG;

  // 1) Leer JSON local (valores por defecto)
  const urlLocal = chrome.runtime.getURL("config_ext.json");
  const resLocal = await fetch(urlLocal);
  CFG = await resLocal.json();

  // 2) Intentar obtener configuración real del servidor
  try {
    const base = (CFG.server_url || "").replace(/\/+$/, "");
    const extConfigUrl = `${base}/api/ext/config`;

    const res = await fetch(extConfigUrl, { method: "GET" });
    if (res.ok) {
      const srv = await res.json();

      console.log("[EXT] Config dinámica recibida:", srv);

      // Aplicar config del servidor
      if (srv.server_url) CFG.server_url = srv.server_url;
      if (srv.token) CFG.token = srv.token;
    } else {
      console.warn("[EXT] No se pudo obtener config dinámica:", res.status);
    }
  } catch (e) {
    console.warn("[EXT] Error al conectarse al servidor para obtener config:", e);
  }

  return CFG;
}

async function getServerInfo() {
  const cfg = await loadConfig();
  const base = (cfg.server_url || "").replace(/\/+$/, "");
  const apiPrefix = cfg.api_prefix || "/api";
  const token = cfg.token || "";
  return { base, apiPrefix, token };
}


async function sendDownload(url, modo = "video") {
  const { base, apiPrefix, token } = await getServerInfo();
  if (!base || !token) {
    console.warn("[MVideoDk EXT] ❌ Falta server_url o token en config_ext.json");
    notify("Error", "Falta configuración de servidor o token.");
    return;
  }

  const modeUpper = (modo || "video").toUpperCase(); // VIDEO / PLAYLIST
  const endpoint = `${base}${apiPrefix}/queue`;

  try {
    const res = await fetch(endpoint, {
      method: "POST",
      headers: {
        "Authorization": `Bearer ${token}`,
        "Content-Type": "application/json"
      },
      body: JSON.stringify({
        url,
        source: "EXT",
        mode: modeUpper
      })
    });

    let data = null;
    try { data = await res.json(); } catch {}

    if (!res.ok) {
      const msg = (data && (data.detail || data.message)) || res.statusText || "Error HTTP";
      console.warn("[MVideoDk EXT] ❌ Error al encolar:", msg);
      notify("Error al enviar URL", msg);
      return;
    }

    console.log("[MVideoDk EXT] ✅ Descarga en cola:", data);
    notify("MVideoDk", "Descarga en cola desde la extensión.");
  } catch (err) {
    console.error("[MVideoDk EXT] ⚠️ Error de red:", err);
    notify("Error de conexión", "No se pudo contactar con el servidor MVideoDk.");
  }
}

function notify(title, message) {
  if (!chrome.notifications) return;
  chrome.notifications.create({
    type: "basic",
    iconUrl: "Icons/icon48.png",
    title,
    message
  });
}

// ---------- mensajes desde popup o content_script ----------
chrome.runtime.onMessage.addListener((msg, sender, sendResponse) => {
  if (msg.type === "DIRECT_DOWNLOAD") {
    const fromFloat = msg.fromFloat === true;
    const finalUrl = msg.url || (sender.tab && sender.tab.url) || "";

    console.log("[MVideoDk EXT] DIRECT_DOWNLOAD recibido:", {
      finalUrl,
      modo: msg.modo,
      fromFloat,
      from: sender.url
    });

    if (!finalUrl) {
      console.warn("[MVideoDk EXT] No hay URL que enviar");
      sendResponse && sendResponse({ ok: false, error: "no-url" });
      return;
    }

    // ✅ SOLO filtramos mínimamente las URLs que NO vienen del botón flotante (popup, etc.)
    if (!fromFloat) {
      if (!/^https?:\/\//.test(finalUrl)) {
        console.warn("[MVideoDk EXT] URL inválida (popup):", finalUrl);
        sendResponse && sendResponse({ ok: false, error: "URL inválida" });
        return;
      }
    }

    (async () => {
      await sendDownload(finalUrl, msg.modo || "video");
      sendResponse && sendResponse({ ok: true });
    })();

    // Mantener vivo el service worker mientras se resuelve lo async (MV3)
    return true;
  }
});

chrome.runtime.onInstalled.addListener(() =>
  console.log("[MVideoDk EXT] Extensión instalada")
);
chrome.runtime.onStartup.addListener(() =>
  console.log("[MVideoDk EXT] Extensión iniciada")
);
