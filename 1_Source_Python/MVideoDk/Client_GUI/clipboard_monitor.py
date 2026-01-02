# ==========================================================
# Client_GUI/clipboard_monitor.py  ✅ v20 — Monitor del portapapeles
# ==========================================================
"""
Monitor de portapapeles para la GUI de MVideoDk.

Mejoras v20:
- Limpieza de comentarios y estructura.
- Encabezado unificado y actualizado.
- Mantiene exactamente la misma lógica y funcionamiento.

Funcionalidad:
- Detecta automáticamente URLs copiadas al portapapeles.
- Encola descargas vía API (source=CLIPBOARD).
- Evita duplicados mediante caché interna.
- No bloquea la GUI (usa hilos + QTimer).
- Lee intervalos y opciones desde config.ini ([clipboard]).
"""

from __future__ import annotations
import re
import threading
from PyQt6.QtCore import QObject, pyqtSignal, QTimer

from Core.logger import LoggerFactory
from Core.app_config import AppConfig
from Core.utils import is_valid_url
from Client_GUI import api_client

logger = LoggerFactory.get_logger("CLIPBOARD")


class ClipboardMonitor(QObject):
    """
    Monitor periódico del QClipboard.

    Señales:
        urlDetected(str)  → Se encoló correctamente una URL.
        errorSignal(str)  → Error al encolar.
        statusSignal(str) → Estado textual ("Activado", "Desactivado", etc.).
    """

    urlDetected = pyqtSignal(str)
    errorSignal = pyqtSignal(str)
    statusSignal = pyqtSignal(str)

    def __init__(
        self,
        clipboard,
        interval_ms: int | None = None,
        parent: QObject | None = None,
    ):
        """
        Args:
            clipboard: instancia de QClipboard (QApplication.clipboard()).
            interval_ms: intervalo de chequeo en ms. Si es None, se lee de AppConfig.
        """
        super().__init__(parent)

        self.cfg = AppConfig()
        self.clipboard = clipboard

        # Configuración dinámica desde config.ini
        self.interval_ms = interval_ms or self.cfg.getint(
            "clipboard", "interval_ms", fallback=3000
        )
        self.enabled = self.cfg.getboolean("clipboard", "enabled", fallback=True)
        self.auto_start = self.cfg.getboolean("clipboard", "auto_start", fallback=True)

        # Cachés internas
        self.last_text: str = ""
        self.seen_urls: set[str] = set()
        self.pattern = re.compile(r"https?://[^\s]+", re.IGNORECASE)

        # Timer de comprobación
        self.timer = QTimer()
        self.timer.timeout.connect(self._check_clipboard)

        logger.info(
            f"📋 ClipboardMonitor inicializado (intervalo={self.interval_ms}ms, enabled={self.enabled})"
        )

        # Listener de configuración
        self.cfg.add_listener(self._on_config_changed)

        # Auto-inicio opcional
        if self.enabled and self.auto_start:
            self.start()

    # ==========================================================
    # 🔧 Config dinámica
    # ==========================================================
    def _on_config_changed(self, section: str, key: str, value: str):
        """Reacciona a cambios en la sección [clipboard] de AppConfig."""
        if section != "clipboard":
            return

        if key == "enabled":
            self.toggle(value.lower() == "true")

        elif key == "interval_ms":
            try:
                new_interval = int(value)
                if self.timer.isActive():
                    self.timer.setInterval(new_interval)
                    logger.info(
                        f"🔁 Intervalo del ClipboardMonitor actualizado a {new_interval}ms"
                    )
            except ValueError:
                logger.warning(f"⚠️ Valor inválido para interval_ms: {value}")

    # ==========================================================
    # ▶️ Control de estado
    # ==========================================================
    def start(self):
        """Activa el monitor y descarta el texto previo del portapapeles."""
        if self.enabled and self.timer.isActive():
            return

        try:
            self.last_text = (self.clipboard.text() or "").strip()
        except Exception:
            self.last_text = ""

        self.enabled = True
        self.timer.start(self.interval_ms)
        self.statusSignal.emit("Activado")
        logger.info("📋 ClipboardMonitor activado correctamente.")

    def stop(self):
        """Detiene el monitor; no volverá a leer hasta que se llame start()."""
        if self.timer.isActive():
            self.timer.stop()

        self.enabled = False
        self.statusSignal.emit("Desactivado")
        logger.info("📋 ClipboardMonitor detenido.")

    def toggle(self, state: bool):
        """Atajo para encender/apagar según `state`."""
        if state:
            self.start()
        else:
            self.stop()

    def reset(self):
        """Reinicia monitor y caché; el monitor queda apagado."""
        try:
            self.stop()
            self.seen_urls.clear()
            self.last_text = ""
            self.statusSignal.emit("Reiniciado (apagado)")
            logger.info("♻️ ClipboardMonitor reiniciado (estado limpio).")
        except Exception as e:
            logger.warning(f"⚠️ Error al resetear ClipboardMonitor: {e}")

    def reset_cache(self):
        """Limpia solo la caché interna de URLs detectadas."""
        try:
            self.last_text = ""
            self.seen_urls.clear()
            logger.info("♻️ Caché de ClipboardMonitor limpiada.")
        except Exception as e:
            logger.warning(f"⚠️ Error limpiando caché: {e}")

    # ==========================================================
    # 🔍 Comprobación periódica
    # ==========================================================
    def _check_clipboard(self):
        """Revisa el portapapeles en busca de nuevas URLs válidas."""
        if not self.enabled:
            return

        try:
            text = (self.clipboard.text() or "").strip()
        except Exception as e:
            logger.warning(f"No se pudo leer el portapapeles: {e}")
            return

        # Sin cambios → no procesar
        if not text or text == self.last_text:
            return

        self.last_text = text
        urls = re.findall(self.pattern, text)

        if not urls:
            logger.debug("📋 Cambio detectado sin URLs.")
            return

        # Procesar cada URL individualmente
        for url in urls:
            url = url.strip().strip(".,);]")
            if not is_valid_url(url):
                continue

            if url in self.seen_urls:
                logger.debug(f"🔁 URL duplicada omitida: {url}")
                continue

            self.seen_urls.add(url)
            logger.info(f"🔗 Nueva URL detectada: {url}")
            self._process_url(url)

    # ==========================================================
    # 🧵 Envío en hilo separado
    # ==========================================================
    def _process_url(self, url: str):
        """Lanza un hilo para procesar la URL sin bloquear la GUI."""
        threading.Thread(
            target=self._send_url_thread, args=(url,), daemon=True
        ).start()

    def _send_url_thread(self, url: str):
        """Comunicación real con el servidor (ejecutada en hilo de fondo)."""
        try:
            ok, msg = api_client.api_queue(url, "CLIPBOARD", "VIDEO")

            if ok:
                logger.info(f"✅ URL encolada correctamente: {url}")
                self.urlDetected.emit(url)
            else:
                logger.warning(f"⚠️ Error encolando URL: {msg}")
                self.errorSignal.emit(msg)

        except Exception as e:
            logger.error(f"❌ Excepción al enviar URL ({url}): {e}")
            self.errorSignal.emit(str(e))
