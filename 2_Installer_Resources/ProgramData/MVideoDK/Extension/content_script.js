// content_script.js — v9 (botón flotante pequeño, controlable y sin filtro para URL)

(() => {
    let btn = null;
    let floatEnabled = false;   // OFF por defecto
    let currentUrl = window.location.href;

    // Mantener currentUrl al día (SPA tipo YouTube/TikTok)
    const updateUrl = () => {
        currentUrl = window.location.href;
        // console.log("[MVideoDk EXT] URL actual:", currentUrl);
    };

    window.addEventListener("popstate", updateUrl);
    window.addEventListener("hashchange", updateUrl);

    const _pushState = history.pushState;
    history.pushState = function (...args) {
        const r = _pushState.apply(this, args);
        updateUrl();
        return r;
    };
    const _replaceState = history.replaceState;
    history.replaceState = function (...args) {
        const r = _replaceState.apply(this, args);
        updateUrl();
        return r;
    };

    // Backup periódico
    setInterval(updateUrl, 2000);

    function createButton() {
        if (!document.body || btn) return;

        btn = document.createElement("button");
        btn.id = "mvideoDk-btn";
        btn.textContent = "⬇";

        Object.assign(btn.style, {
            position: "fixed",
            top: "10px",
            right: "10px",
            zIndex: 999999,
            background: "#2b8af7",
            color: "white",
            border: "none",
            borderRadius: "8px",
            width: "32px",
            height: "32px",
            fontSize: "16px",
            cursor: "pointer",
            boxShadow: "0 2px 4px rgba(0,0,0,0.25)",
            opacity: "0.8",
            transition: "opacity 0.2s, transform 0.1s",
            display: "none"
        });

        btn.onmouseenter = () => {
            btn.style.opacity = "1.0";
            btn.style.transform = "scale(1.05)";
        };
        btn.onmouseleave = () => {
            btn.style.opacity = "0.8";
            btn.style.transform = "scale(1.0)";
        };

        // Siempre modo VIDEO — sin filtro, solo URL tal cual
        btn.addEventListener("click", () => {
            const url = currentUrl;
            console.log("[MVideoDk EXT] Botón flotante clicado, URL:", url);

            chrome.runtime.sendMessage(
                { type: "DIRECT_DOWNLOAD", url, modo: "video", fromFloat: true },
                (res) => {
                    if (chrome.runtime.lastError) {
                        console.error(
                          "[MVideoDk EXT] Error sendMessage:",
                          chrome.runtime.lastError.message
                        );
                        btn.textContent = "✕";
                        setTimeout(() => (btn.textContent = "⬇"), 1500);
                        return;
                    }

                    console.log("[MVideoDk EXT] Respuesta background:", res);
                    btn.textContent = (res && res.ok) ? "✓" : "✕";
                    setTimeout(() => (btn.textContent = "⬇"), 1500);
                }
            );
        });

        document.body.appendChild(btn);
        updateVisibility();
    }

    function removeButton() {
        if (btn && btn.parentNode) {
            btn.parentNode.removeChild(btn);
        }
        btn = null;
    }

    function updateVisibility() {
        if (!btn) return;
        btn.style.display = floatEnabled ? "block" : "none";
    }

    // Leer preferencia inicial desde storage (clave alineada con popup.js)
    function initFloatState() {
        chrome.storage.local.get("MvideoDk_float_button", (items) => {
            const value = items["MvideoDk_float_button"];
            // OFF por defecto si no existe
            floatEnabled = (value === true);

            if (floatEnabled) {
                createButton();
            } else {
                removeButton();
            }
        });
    }

    const addOrInit = () => {
        if (!document.body) return;
        initFloatState();
    };

    if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", addOrInit);
    } else {
        addOrInit();
    }

    // Escuchar mensajes desde popup para encender/apagar el botón
    chrome.runtime.onMessage.addListener((msg) => {
        if (msg.type === "SET_FLOAT_BUTTON") {
            floatEnabled = !!msg.enabled;
            if (floatEnabled) {
                createButton();
            } else {
                removeButton();
            }
        }
    });
})();
