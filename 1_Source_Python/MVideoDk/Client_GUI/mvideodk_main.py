# ==========================================================
# Client_GUI/mvideodk_main.py   ✅ v20 —  GUI dinámica con AppConfig centralizado
# ==========================================================

from __future__ import annotations
import sys, os, re, time, requests
from pathlib import Path

from PyQt6.QtCore import Qt, QTimer

from PyQt6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QLineEdit, QTextEdit, QCheckBox, QComboBox, QGroupBox, QGridLayout,
    QSizePolicy, QMessageBox, QScrollArea,
    QDialog, QDialogButtonBox, QFormLayout,
    QTabWidget, QSpinBox, QFileDialog,
)

# ========= Core / Utilidades =========
from Core.logger import LoggerFactory
from Core.app_config import AppConfig
from Core.paths import data_dir, downloads_dir

from Core.utils import build_friendly_title, sanitize_filename

from Client_GUI import api_client
from Client_GUI.clipboard_monitor import ClipboardMonitor
from Client_GUI.download_queue_widgets import QueueItem, DownloadItemWidget

from tunnel_cf import start_cloudflare_tunnel, stop_cloudflare_tunnel

# ---------- System Tray ----------
from pathlib import Path

from PyQt6.QtGui import QIcon, QAction
from PyQt6.QtWidgets import QSystemTrayIcon, QMenu, QApplication

from PyQt6.QtGui import QCursor

from Core.resource import resource_path

logger = LoggerFactory.get_logger("GUI")


# ---------------------------------------------------------
# 🌍 Configuración dinámica (AppConfig)
# ---------------------------------------------------------
app_config = AppConfig()
app_config.initialize()     # crea config.ini si no existe
app_config.ensure_dirs()    # crea carpetas principales

API_BASE = app_config.get_server_url()
TOKEN_PATH = app_config.get_token_path()

logger.info(f"🌐 Servidor base: {API_BASE}")
logger.info(f"🔑 Token path: {TOKEN_PATH}")

def _read_token() -> str:
    try:
        t = TOKEN_PATH.read_text(encoding="utf-8").strip()
        if not t:
            raise ValueError("token.key vacío")
        return t
    except Exception as e:
        logger.warning(f"Token no disponible: {e}")
        return ""

def _headers() -> dict:
    tok = _read_token()
    return {"Authorization": f"Bearer {tok}"} if tok else {}


# ========= Estilos y widgets =========
def crear_boton(texto, color="#4caf50", texto_color="#fff", expand=True):
    btn = QPushButton(texto)
    btn.setStyleSheet(f"""
        QPushButton {{
            background-color: {color};
            color: {texto_color};
            border-radius: 6px;
            padding: 6px 12px;
            font-weight: bold;
        }}
    """)
    if expand:
        btn.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
    else:
        btn.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Preferred)
    return btn


class ConfigDialog(QDialog):
    """
    Ventana de configuración ligada a AppConfig.
    - Pestaña Servidor (scheme / host / port)
    - Pestaña Portapapeles
    - Pestaña Extensión
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        
        # 🔥 ICONO DE CONFIGURACIÓN
        self.setWindowIcon(QIcon(resource_path("icons/main/icon_32.ico")))

        self.setWindowTitle("Configuración MVideoDk")
        self.setModal(True)
        self.cfg = AppConfig()

        main = QVBoxLayout(self)
        tabs = QTabWidget()
        main.addWidget(tabs)

        # ---------- TAB SERVIDOR ----------
        tab_srv = QWidget()
        form_srv = QFormLayout(tab_srv)

        self.cmb_scheme = QComboBox()
        self.cmb_scheme.addItems(["http", "https"])
        self.cmb_scheme.setCurrentText(
            self.cfg.get("server", "scheme", fallback="http")
        )

        self.ed_host = QLineEdit(
            self.cfg.get("server", "host", fallback="127.0.0.1")
        )

        self.spn_port = QSpinBox()
        self.spn_port.setRange(1, 65535)
        self.spn_port.setValue(
            self.cfg.getint("server", "port", fallback=8000)
        )

        form_srv.addRow("Protocolo (scheme):", self.cmb_scheme)
        form_srv.addRow("Host:", self.ed_host)
        form_srv.addRow("Puerto:", self.spn_port)

        tabs.addTab(tab_srv, "Servidor")

        # ---------- TAB PORTAPAPELES ----------
        tab_clip = QWidget()
        form_clip = QFormLayout(tab_clip)

        clip_conf = self.cfg.get_clipboard_config()
        self.chk_clip_enabled = QCheckBox("Habilitar monitor de portapapeles")
        self.chk_clip_enabled.setChecked(clip_conf.get("enabled", True))

        self.chk_clip_auto = QCheckBox("Iniciar automáticamente con la GUI")
        self.chk_clip_auto.setChecked(clip_conf.get("auto_start", False))

        self.spn_clip_interval = QSpinBox()
        self.spn_clip_interval.setRange(500, 30000)
        self.spn_clip_interval.setSingleStep(500)
        self.spn_clip_interval.setValue(clip_conf.get("interval_ms", 3000))

        form_clip.addRow(self.chk_clip_enabled)
        form_clip.addRow(self.chk_clip_auto)
        form_clip.addRow("Intervalo (ms):", self.spn_clip_interval)

        tabs.addTab(tab_clip, "Portapapeles")

        # ---------- TAB EXTENSIÓN ----------
        tab_ext = QWidget()
        form_ext = QFormLayout(tab_ext)

        self.ed_ext_dir = QLineEdit(
            self.cfg.get("extension", "dir",
                         fallback=AppConfig.DEFAULTS["extension"]["dir"])
        )
        btn_ext_browse = QPushButton("Examinar...")

        row_ext = QHBoxLayout()
        row_ext.addWidget(self.ed_ext_dir)
        row_ext.addWidget(btn_ext_browse)

        form_ext.addRow("Carpeta de la extensión:", row_ext)

        tabs.addTab(tab_ext, "Extensión")

        btn_ext_browse.clicked.connect(self._browse_extension_dir)
        
        # ---------- TAB POST-PROCESADO ----------
        tab_post = QWidget()
        form_post = QFormLayout(tab_post)

        # Cargar valores actuales desde AppConfig
        post_enabled = self.cfg.getboolean("postprocess", "enabled", fallback=False)
        post_action = self.cfg.get("postprocess", "action", fallback="audio")
        post_format = self.cfg.get("postprocess", "audio_format", fallback="mp3")
        post_bitrate = self.cfg.get("postprocess", "audio_bitrate", fallback="320k")

        # Checkbox activar/desactivar
        self.chk_post_enabled = QCheckBox("Activar post-procesado (FFmpeg)")
        self.chk_post_enabled.setChecked(post_enabled)
        form_post.addRow(self.chk_post_enabled)
        
        self.chk_post_enabled.toggled.connect(self._update_post_style)
        self._update_post_style(self.chk_post_enabled.isChecked())

        # ==========================
        # ⭐ ACCIÓN RESTAURADA ⭐
        # ==========================
        self.cmb_post_action = QComboBox()
        self.cmb_post_action.addItem("Audio (extraer mp3)", "audio")
        self.cmb_post_action.addItem("Both (video + mp3)", "both")

        # Seleccionar el valor actual
        idx = self.cmb_post_action.findData(post_action)
        if idx != -1:
            self.cmb_post_action.setCurrentIndex(idx)

        form_post.addRow("Acción:", self.cmb_post_action)

        # Formato de salida (solo mp3)
        self.cmb_post_format = QComboBox()
        self.cmb_post_format.addItems(["mp3"])
        self.cmb_post_format.setCurrentText(post_format)
        form_post.addRow("Formato de audio:", self.cmb_post_format)

        # Bitrate MP3
        self.cmb_post_bitrate = QComboBox()
        self.cmb_post_bitrate.addItems(["320k", "256k"])
        self.cmb_post_bitrate.setCurrentText(post_bitrate)
        form_post.addRow("Bitrate:", self.cmb_post_bitrate)

        tabs.addTab(tab_post, "Post-Procesado")

        # ---------- BOTONES INFERIORES ----------
        buttons_layout = QHBoxLayout()
        buttons_layout.addStretch(1)
        btn_save = QPushButton("Guardar")
        btn_cancel = QPushButton("Cancelar")
        buttons_layout.addWidget(btn_save)
        buttons_layout.addWidget(btn_cancel)
        main.addLayout(buttons_layout)

        btn_save.clicked.connect(self._apply_and_close)
        btn_cancel.clicked.connect(self.reject)

    def _browse_extension_dir(self):
        path = QFileDialog.getExistingDirectory(
            self, "Seleccionar carpeta de la extensión",
            self.ed_ext_dir.text() or ""
        )
        if path:
            self.ed_ext_dir.setText(path)
    
    def _update_post_style(self, active: bool):
        if active:
            self.chk_post_enabled.setStyleSheet("""
                QCheckBox {
                    color: #aaffaa;
                    font-weight: bold;
                }
                QCheckBox::indicator {
                    width: 16px;
                    height: 16px;
                    border-radius: 4px;
                    border: 1px solid #55ff55;
                    background: #55ff55;
                }
            """)
        else:
            self.chk_post_enabled.setStyleSheet("""
                QCheckBox {
                    color: #dddddd;
                }
                QCheckBox::indicator {
                    width: 16px;
                    height: 16px;
                    border-radius: 4px;
                    border: 1px solid #888;
                    background: #333;
                }
            """)


    def _apply_and_close(self):
        # Servidor
        self.cfg.set("server", "scheme", self.cmb_scheme.currentText().strip() or "http")
        self.cfg.set("server", "host", self.ed_host.text().strip() or "127.0.0.1")
        self.cfg.set("server", "port", str(self.spn_port.value()))

        # Portapapeles
        self.cfg.set("clipboard", "enabled", "true" if self.chk_clip_enabled.isChecked() else "false")
        self.cfg.set("clipboard", "auto_start", "true" if self.chk_clip_auto.isChecked() else "false")
        self.cfg.set("clipboard", "interval_ms", str(self.spn_clip_interval.value()))

        # Extensión
        ext_dir = self.ed_ext_dir.text().strip() or AppConfig.DEFAULTS["extension"]["dir"]
        self.cfg.set("extension", "dir", ext_dir)
        
        # Post-procesado
        self.cfg.set(
            "postprocess", "enabled",
            "true" if self.chk_post_enabled.isChecked() else "false"
        )
        self.cfg.set("postprocess", "action", self.cmb_post_action.currentData())
        self.cfg.set("postprocess", "audio_format", self.cmb_post_format.currentText())
        self.cfg.set("postprocess", "audio_bitrate", self.cmb_post_bitrate.currentText())

        self.accept()


# ========= Interfaz principal =========
class MVideoDkApp(QWidget):
    def __init__(self):
        super().__init__()
        
        # 🔥 ICONO DE LA VENTANA PRINCIPAL
        self.setWindowIcon(QIcon(resource_path("icons/main/icon_64.ico")))

        self.setWindowTitle("MVideoDk – Gestor de Descargas Global | By Majuel20")
        self.resize(1080, 720)
        self.setStyleSheet("""
            QWidget { background-color: #2f2f2f; color: #fff; font-family: 'Segoe UI'; }
            QLineEdit, QComboBox, QTextEdit {
                background-color: #262626; border: 1px solid #555; border-radius: 4px;
                color: #fff; selection-background-color: #444;
            }
            QLabel { font-size: 10pt; }
            QGroupBox {
                font-weight: bold; color: #ccc; border: 1px solid #444;
                border-radius: 6px; margin-top: 8px; padding-top: 10px;
            }
            QGroupBox::title { subcontrol-origin: margin; left: 8px; padding: 0 3px; }
        """)

        # ---------- FLAGS INTERNOS ----------
        self._alive = False
        self._clip_active = False
        self._worker_paused = False
        self._compact_mode = False
        
        self.tunnel_process = None
        self.tunnel_active = False
        
        self.tunnel_url = ""

        self.queue_items = []
        self.queue_widgets = []
        self._progress_state = {}

        # ---------- CONSTRUIR UI ----------
        self._build_ui()
        logger.info("Interfaz inicializada")

        # ---------- DEFINIR ICONOS DEL TRAY (ANTES DE CREAR TRAY) ----------
        self.tray_icons = {
            "green": resource_path("icons/tray/tray_green.ico"),
            "yellow": resource_path("icons/tray/tray_yellow.ico"),
            "red": resource_path("icons/tray/tray_red.ico"),
            "blue": resource_path("icons/tray/tray_blue.ico"),
        }

        # ---------- CREAR ICONO EN BANDEJA ----------
        self._create_tray_icon()

        # ---------- TIMER DE REFRESCO ----------
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_status)
        self.timer.start(3000)

        # ---------- ACTUALIZAR ESTADO INICIAL ----------
        self.update_server_led(initial=True)

        # → AHORA SÍ: YA EXISTE self.act_pause
        self.sync_worker_state()

        # ---------- LISTENER DE CONFIG ----------
        app_config.add_listener(self._on_config_change)

        # ---------- PRIMER UPDATE COMPLETO ----------
        self.update_status()


    def _create_tray_icon(self):
        self.tray = QSystemTrayIcon(self)
        self.tray.setIcon(QIcon(self.tray_icons["blue"]))
        self.tray.setToolTip("MVideoDk – Ejecutando")

        # --- MENÚ: guardar referencia o NO funciona ---
        # ---------- MENÚ ----------
        self.tray_menu = QMenu()

        act_open = QAction("Abrir ventana", self)
        act_open.triggered.connect(self._show_window)
        self.tray_menu.addAction(act_open)

        self.tray_menu.addSeparator()

        # 🔄 PAUSAR / REANUDAR (dinámico)
        self.act_pause = QAction("Pausar cola", self)
        self.act_pause.triggered.connect(self.toggle_worker_pause)
        self.tray_menu.addAction(self.act_pause)

        act_cancel = QAction("Cancelar descarga actual", self)
        act_cancel.triggered.connect(self.cancel_current_task)
        self.tray_menu.addAction(act_cancel)

        act_restart = QAction("Reiniciar cola", self)
        act_restart.triggered.connect(self.restart_all)
        self.tray_menu.addAction(act_restart)

        self.tray_menu.addSeparator()

        act_copy_token = QAction("Copiar token", self)
        act_copy_token.triggered.connect(self.copy_token)
        self.tray_menu.addAction(act_copy_token)

        act_copy_url = QAction("Copiar URL pública", self)
        act_copy_url.triggered.connect(self.copy_tunnel_url)
        self.tray_menu.addAction(act_copy_url)

        self.tray_menu.addSeparator()

        self.act_clipboard = QAction("Monitorear portapapeles", self, checkable=True)
        self.act_clipboard.setChecked(self._clip_active)
        self.act_clipboard.triggered.connect(lambda st: self.toggle_clipboard(st))
        self.tray_menu.addAction(self.act_clipboard)

        self.tray_menu.addSeparator()

        act_exit = QAction("Cerrar aplicación", self)
        act_exit.triggered.connect(self._exit_app)
        self.tray_menu.addAction(act_exit)

        # Asociar menú persistente
        self.tray.setContextMenu(self.tray_menu)

        # SOLO clic izquierdo
        self.tray.activated.connect(self._tray_clicked)

        self.tray.show()


    def _tray_clicked(self, reason):
        print("TRAY EVENT:", reason)

        if reason == QSystemTrayIcon.ActivationReason.Trigger:
            print(" → Clic izquierdo detectado")
            self._show_window()



    def closeEvent(self, event):
        event.ignore()
        self.hide()
        self.tray.showMessage(
            "MVideoDk",
            "La aplicación sigue ejecutándose en segundo plano.",
            QSystemTrayIcon.MessageIcon.Information,
            2000
        )
    
    
    def _show_window(self):
        self.show()
        self.activateWindow()
    
    
    def _exit_app(self):
        try:
            stop_cloudflare_tunnel(self.tunnel_process)
        except:
            pass

        self.tray.hide()
        QApplication.quit()
        os._exit(0)



    # --------- UI ----------
    def _build_ui(self):
        layout_main = QVBoxLayout(self)
        layout_main.setContentsMargins(10, 10, 10, 10)
        layout_main.setSpacing(8)

        # Estado del sistema
        grp_sys = QGroupBox("🧠 Estado del Sistema")
        lay_sys = QVBoxLayout(grp_sys)

        row1 = QHBoxLayout()
        self.lbl_token = QLabel("🔑 Token: —")
        self.lbl_token.setStyleSheet("color: #ffc107; font-weight: bold;")
        
        
        # === NUEVO: Botón copiar URL del túnel ===
        self.btn_copy_tunnel = crear_boton("📡 Copiar", "#455a64", expand=False)



        # Botón 1: cancelar descarga actual
        self.btn_stop = crear_boton("🛑 Cancelar actual", "#ff9800", expand=False)
        # Botón 2: pausar / continuar cola (toggle)
        self.btn_continue = crear_boton("⏸️ Pausar cola", "#00bcd4", expand=False)
        # Botón 3: reinicio fuerte de cola
        self.btn_restart = crear_boton("🔁 Reiniciar cola", "#f44336", expand=False)

        self.btn_copy = crear_boton("📋 Copiar", "#607d8b", expand=False)

        row1.addWidget(self.lbl_token, 1)
        row1.addWidget(self.btn_copy, 0)
        
        # === NUEVO ===
        row1.addWidget(self.btn_copy_tunnel, 0)
        
        # === LED del túnel (clickeable) ===
        self.led_tunnel = QLabel("●")
        self.led_tunnel.setStyleSheet(
            "color: red; font-size:22px; font-weight:bold; padding-left:6px; padding-right:6px;"
        )
        self.led_tunnel.setCursor(Qt.CursorShape.PointingHandCursor)
        self.led_tunnel.mousePressEvent = self.toggle_tunnel_led

        row1.addWidget(self.led_tunnel, 0)


        row1.addWidget(self.btn_stop, 0)
        row1.addWidget(self.btn_continue, 0)
        row1.addWidget(self.btn_restart, 0)
        lay_sys.addLayout(row1)

        # Handlers
        self.btn_copy.clicked.connect(self.copy_token)
        
        # Nuevo TUNEL
        self.btn_copy_tunnel.clicked.connect(self.copy_tunnel_url)

        self.btn_stop.clicked.connect(self.cancel_current_task)
        self.btn_continue.clicked.connect(self.toggle_worker_pause)
        self.btn_restart.clicked.connect(self.restart_all)

        row2 = QHBoxLayout()
        self.lbl_srv_status = QLabel("● Servidor: —")
        self.lbl_tunnel_status = QLabel("🌐 Túnel: —")
        self.lbl_mob_status = QLabel("📱 Móvil: Esperando...")
        self.lbl_ext_status = QLabel("🧩 Extensión: Desconectada")
        for lbl, color in [
            (self.lbl_srv_status, "#8bc34a"),
            (self.lbl_tunnel_status, "#00bcd4"),   # ← NUEVO
            (self.lbl_mob_status, "#ffc107"),
            (self.lbl_ext_status, "#f44336")
        ]:
            lbl.setStyleSheet(f"color:{color}; font-weight:bold;")
            lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            lbl.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
            row2.addWidget(lbl)
        lay_sys.addLayout(row2)
        
        
        row3 = QHBoxLayout()
        self.btn_view_mobile = crear_boton("🌐 URLs del Móvil", "#2196f3")
        self.btn_view_ext = crear_boton("🧩 URLs de la Extensión", "#00bcd4")
        self.btn_view_all = crear_boton("✅ Todas las URLs", "#4caf50")   # 👈 NUEVO
        self.btn_settings = crear_boton("⚙️ Configuración", "#9c27b0", expand=False)
        
        row3.addWidget(self.btn_view_mobile, 1)
        row3.addWidget(self.btn_view_ext, 1)
        row3.addWidget(self.btn_view_all, 1)                              # 👈 NUEVO
        row3.addStretch(1)
        row3.addWidget(self.btn_settings, 0)
        
        # Handlers de filtros rápidos
        self.btn_view_mobile.clicked.connect(lambda: self._set_origin_filter("MOBILE"))
        self.btn_view_ext.clicked.connect(lambda: self._set_origin_filter("EXT"))
        self.btn_view_all.clicked.connect(lambda: self._set_origin_filter("Todos"))  # 👈 NUEVO
        self.btn_settings.clicked.connect(self.open_settings_dialog)

        
        lay_sys.addLayout(row3)
        
        layout_main.addWidget(grp_sys)
        
        # Opciones globales
        grp_opts = QGroupBox("⚙️ Opciones Globales")
        lay_opts = QHBoxLayout(grp_opts)
        lay_opts.setSpacing(10)
        lay_clip = QHBoxLayout()
        lay_clip.setContentsMargins(0, 0, 0, 0)
        lay_clip.setSpacing(6)
        self.btn_clip_monitor = crear_boton("📋 Monitorear Portapapeles", "#607d8b")
        self.lbl_clip_status = QLabel("●")
        self.lbl_clip_status.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_clip_status.setStyleSheet("QLabel { color: red; font-size:14pt; font-weight:bold; padding-left:4px; }")
        lay_clip.addWidget(self.btn_clip_monitor, 9)
        lay_clip.addWidget(self.lbl_clip_status, 1)
        self.btn_load_file = crear_boton("🧾 Cargar Archivo", "#ff9800")
        lay_opts.addLayout(lay_clip, 9)
        lay_opts.addWidget(self.btn_load_file, 10)
        layout_main.addWidget(grp_opts)
        
        self.btn_load_file.clicked.connect(self.cargar_archivo_urls)
        
        self.btn_clip_monitor.setCheckable(True)
        self.btn_clip_monitor.toggled.connect(self.toggle_clipboard)
        
        # Nueva descarga
        grp_dl = QGroupBox("📥 Nueva Descarga")
        lay_dl = QGridLayout(grp_dl)
        self.txt_url = QLineEdit()
        self.txt_url.setPlaceholderText("Pega una URL de YouTube o TikTok...")
        self.cmb_modo = QComboBox()
        self.cmb_modo.addItems(["Video", "Playlist"])
        self.chk_confirm = QCheckBox("Confirmar antes de encolar")
        self.btn_add = crear_boton("Enviar a Cola", "#4caf50", expand=False)
        self.btn_add.clicked.connect(self.enviar_manual)
        lay_dl.addWidget(QLabel("URL:"), 0, 0)
        lay_dl.addWidget(self.txt_url, 0, 1, 1, 3)
        lay_dl.addWidget(QLabel("Modo:"), 1, 0)
        lay_dl.addWidget(self.cmb_modo, 1, 1)
        lay_dl.addWidget(self.chk_confirm, 1, 2)
        lay_dl.addWidget(self.btn_add, 1, 3)
        layout_main.addWidget(grp_dl)
        
        # Botones secundarios
        lay_btns = QHBoxLayout()
        self.btn_open_folder = crear_boton("📂 Abrir Descargas", "#9c27b0")
        self.btn_logs = crear_boton("📜 Logs", "#795548")
        self.btn_logs.setCheckable(True)
        self.btn_refresh = crear_boton("🔄 Actualizar", "#00bcd4")
        lay_btns.addWidget(self.btn_open_folder)
        lay_btns.addWidget(self.btn_logs)
        lay_btns.addWidget(self.btn_refresh)
        layout_main.addLayout(lay_btns)
        
        # 👇 franja negra entre botones y zona blanca de la cola
        layout_main.addSpacing(6)
        
        self.btn_open_folder.clicked.connect(self.open_downloads)
        self.btn_logs.clicked.connect(self.toggle_logs)
        self.btn_refresh.clicked.connect(self.update_status)
        
        # Cola de descargas
        grp_queue = QGroupBox("📦 Cola de Descargas")
        grp_queue.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        
        # 👇 AÑADE ESTA LÍNEA
        grp_queue.setObjectName("queueGroup")
        
        grp_queue.setStyleSheet("""
            /* Caja de la cola */
            #queueGroup {
                background-color: #f5f5f5;
                border: 1px solid #cccccc;
                border-radius: 6px;
                color: #333333;
                margin-top: 0px;
                padding-top: 10px;
            }
            
            #queueGroup::title {
                subcontrol-origin: margin;
                left: 8px;
                padding: 0 3px;
            }
            
            /* Etiquetas dentro de la cola */
            #queueGroup QLabel {
                color: #222222;
                background: transparent;
            }
            
            /* COMBOS */
            #queueGroup QComboBox {
                background-color: #ffffff;
                color: #333333;
                border: 1px solid #b0b0b0;
                border-radius: 4px;
                padding: 2px 6px;
                min-width: 80px;
            }
            #queueGroup QComboBox::drop-down {
                border: none;
                width: 16px;
            }
            #queueGroup QComboBox QAbstractItemView {
                background-color: #ffffff;
                color: #333333;
                selection-background-color: #e0f0ff;
                selection-color: #000000;
            }
            
            /* Texto del checkbox */
            #queueGroup QCheckBox {
                background: transparent;
                color: #333333;
                padding: 0 4px;
                border: none;
            }
            
            /* Cuadradito del checkbox */
            #queueGroup QCheckBox::indicator {
                width: 16px;
                height: 16px;
                border-radius: 4px;
                border: 1px solid #777777;
                background: #ffffff;
                margin-right: 4px;
            }
            
            #queueGroup QCheckBox::indicator:unchecked {
                image: none;
            }
            
            #queueGroup QCheckBox::indicator:checked {
                border: 1px solid #0078d7;
                background: #0078d7;
                image: url(:/icons/check_white.png);   /* ✔ blanco */
            }
        """)


        lay_queue = QVBoxLayout(grp_queue)

        # Fila de filtros y opciones (como la demo)
        filters_layout = QHBoxLayout()
        filters_layout.setSpacing(10)

        # Estado
        filters_layout.addWidget(QLabel("Estado:"))
        self.cmbEstado = QComboBox()
        self.cmbEstado.addItems(["Todos", "Completado", "Descargando", "Pendiente", "Error", "Cancelado"])
        self.cmbEstado.currentIndexChanged.connect(self.apply_filters)
        filters_layout.addWidget(self.cmbEstado)

        # Origen
        filters_layout.addWidget(QLabel("Origen:"))
        self.cmbOrigen = QComboBox()
        self.cmbOrigen.addItems([
            "Todos",
            "CLIPBOARD",
            "GUI",
            "FILE",
            "EXT",
            "MOBILE",
            "API",
            "OTROS",
        ])
        self.cmbOrigen.currentIndexChanged.connect(self.apply_filters)
        filters_layout.addWidget(self.cmbOrigen)

        # Tipo
        filters_layout.addWidget(QLabel("Tipo:"))
        self.cmbTipo = QComboBox()
        self.cmbTipo.addItems(["Todos", "Video", "Audio", "Playlist"])
        self.cmbTipo.currentIndexChanged.connect(self.apply_filters)
        filters_layout.addWidget(self.cmbTipo)

        filters_layout.addStretch(1)

        # Checkboxes de visibilidad
        self.chkShowOrigin = QCheckBox("Mostrar origen")
        self.chkShowOrigin.setChecked(True)
        self.chkShowOrigin.toggled.connect(self.update_visibility_options)
        filters_layout.addWidget(self.chkShowOrigin)

        self.chkShowType = QCheckBox("Mostrar tipo")
        self.chkShowType.setChecked(True)
        self.chkShowType.toggled.connect(self.update_visibility_options)
        filters_layout.addWidget(self.chkShowType)

        self.chkShowLocalId = QCheckBox("Mostrar ID")
        self.chkShowLocalId.setChecked(True)
        self.chkShowLocalId.toggled.connect(self.update_visibility_options)
        filters_layout.addWidget(self.chkShowLocalId)

        # Botón compactar playlists
        self.btnToggleCompact = QPushButton("⇣ Compactar playlists")
        self.btnToggleCompact.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btnToggleCompact.setStyleSheet(
            "QPushButton { border-radius:10px; padding:4px 10px; "
            "background:#444444; }"
            "QPushButton:hover { background:#555555; }"
        )
        self.btnToggleCompact.clicked.connect(self.toggle_compact_all)
        filters_layout.addWidget(self.btnToggleCompact)

        lay_queue.addLayout(filters_layout)

        # Contenedor scrollable de tarjetas
        self.scroll_queue = QScrollArea()
        self.scroll_queue.setWidgetResizable(True)
        self.scrollContent = QWidget()
        self.scrollLayout = QVBoxLayout(self.scrollContent)
        self.scrollLayout.setContentsMargins(4, 4, 4, 4)
        self.scrollLayout.setSpacing(6)
        self.scrollLayout.setAlignment(Qt.AlignmentFlag.AlignTop)
        
        self.scroll_queue.setStyleSheet(
            "QScrollArea { background-color: #f5f5f5; border: none; }"
        )
        self.scrollContent.setStyleSheet("background-color: #f5f5f5;")

        self.scroll_queue.setWidget(self.scrollContent)
        lay_queue.addWidget(self.scroll_queue)

        layout_main.addWidget(grp_queue, stretch=3)


        # Logs
        grp_logs = QGroupBox("📋 Registros / Logs")
        lay_logs = QVBoxLayout(grp_logs)
        self.txt_logs = QTextEdit()
        self.txt_logs.setReadOnly(True)
        lay_logs.addWidget(self.txt_logs)
        layout_main.addWidget(grp_logs, stretch=1)
        self.grp_logs = grp_logs
        self.grp_logs.setVisible(False)
        self.btn_logs.setChecked(False)
        self.btn_logs.setText("📜 Mostrar Logs")


        # ✅ Clipboard monitor (nuevo con señales Qt)
        self.clip = ClipboardMonitor(QApplication.instance().clipboard())

        # Conectar señales del monitor a métodos GUI
        self.clip.urlDetected.connect(self._on_clipboard_url)
        self.clip.errorSignal.connect(lambda msg: self.add_log_entry(f"⚠️ {msg}"))
        self.clip.statusSignal.connect(self._on_clipboard_status)


        # Mostrar token actual
        self.refresh_token_label()
        self._refresh_pause_button_ui()

    # ---------- Acciones de control ----------
    def copy_token(self):
        tok = _read_token()
        if not tok:
            self.add_log_entry("⚠️ No hay token disponible.")
            return
        QApplication.clipboard().setText(tok)
        self.add_log_entry("📋 Token copiado al portapapeles.")
        
    
    def copy_tunnel_url(self):
        url = self.tunnel_url

        if not url:
            self.add_log_entry("⚠️ No hay URL pública del túnel disponible.")
            return

        QApplication.clipboard().setText(url)
        self.add_log_entry("📡 URL del túnel copiada al portapapeles.")

        
    def toggle_tunnel_led(self, event):
        """
        Activar o desactivar el túnel desde el LED clickeable.
        NO se guarda nada en AppConfig.
        Todo es temporal hasta cerrar la GUI.
        """

        # ENCENDER TÚNEL
        if not self.tunnel_active:
            url, proc = start_cloudflare_tunnel()

            if url and proc:
                self.tunnel_process = proc
                self.tunnel_active = True
                self.tunnel_url = url 

                # LED verde
                self.led_tunnel.setStyleSheet(
                    "color: #00ff00; font-size:22px; font-weight:bold; padding:0 6px;"
                )

                self.add_log_entry(f"🌐 Túnel iniciado: {url}")

            else:
                self.add_log_entry("❌ No se pudo iniciar el túnel.")

            return

        # APAGAR TÚNEL
        stop_cloudflare_tunnel(self.tunnel_process)

        self.tunnel_process = None
        self.tunnel_active = False

        # LED rojo
        self.led_tunnel.setStyleSheet(
            "color: red; font-size:22px; font-weight:bold; padding:0 6px;"
        )
        
        self.tunnel_url = ""

        self.add_log_entry("🌐 Túnel detenido.")





    def refresh_token_label(self):
        tok = _read_token()
        if not tok:
            self.lbl_token.setText("🔑 Token: —")
            return

        # Mostrar siempre enmascarado en la GUI
        shown = "XXXXX - XXXXX - XXXXX - XXXXX - XXXXX - XXXXX - XXXXX - XXXXX"
        self.lbl_token.setText(f"🔑 Token: {shown}")

    
    def open_settings_dialog(self):
        """Abre la ventana de configuración basada en AppConfig."""
        dlg = ConfigDialog(self)
        if dlg.exec():
            # Tras guardar, ya se encargarán los listeners de refrescar.
            # Aquí podemos forzar un update visual rápido:
            self.refresh_token_label()
            self.update_server_led()
            self.update_status()

        
    # ---------------------------------------------------------
    # 🧩 Reacción a cambios en AppConfig
    # ---------------------------------------------------------
    def _on_config_change(self, section, key, value):
        """
        Callback automático cuando AppConfig detecta cambios.
        Permite refrescar dinámicamente el servidor, token o ajustes GUI.
        """
        if section == "server" and key in ("scheme", "host", "port"):
            global API_BASE
            API_BASE = app_config.get_server_url()
            self.add_log_entry(f"🌍 Configuración del servidor actualizada: {API_BASE}")
            self.update_server_led()

        elif section == "security" and key == "token_path":
            global TOKEN_PATH
            TOKEN_PATH = app_config.get_token_path()
            self.add_log_entry(f"🔑 Nueva ruta de token: {TOKEN_PATH}")
            self.refresh_token_label()

        elif section == "gui" and key == "theme":
            self.add_log_entry(f"🎨 Tema actualizado: {value}")


    def _control_action(self, action: str, ok_msg: str):
        """
        Envia una acción de control simple y registra el resultado.
        """
        try:
            ok, msg = api_client.api_control(action)
        except Exception as e:
            self.add_log_entry(f"❌ Error al contactar con el servidor: {e}")
            return

        if ok:
            self.add_log_entry(ok_msg)
        else:
            self.add_log_entry(f"⚠️ {msg}")

        QTimer.singleShot(800, self.update_status)

    def cancel_current_task(self):
        """
        Botón 1:
        Cancela únicamente la descarga actual (si existe).
        """
        try:
            ok, msg = api_client.api_control("cancel_current")
        except Exception as e:
            self.add_log_entry(f"❌ Error al contactar con el servidor: {e}")
            return

        if ok:
            self.add_log_entry("🛑 Descarga actual cancelada (si había alguna).")
        else:
            self.add_log_entry(f"⚠️ {msg}")
        QTimer.singleShot(800, self.update_status)

    def toggle_worker_pause(self):
        """
        Botón 2:
        Toggle Pausar / Continuar cola.
        Usa el flag local _worker_paused y el endpoint /api/control.
        """
        if not self._alive:
            self.add_log_entry("⚠️ Servidor no disponible; no se puede pausar/reanudar.")
            return

        if self._worker_paused:
            # Reanudar
            try:
                ok, msg = api_client.api_control("resume_worker")
            except Exception as e:
                self.add_log_entry(f"❌ Error al contactar con el servidor: {e}")
                return
            if ok:
                self._worker_paused = False
                self.add_log_entry("🔵 Cola reanudada.")
            else:
                self.add_log_entry(f"⚠️ {msg}")
        else:
            # Pausar
            try:
                ok, msg = api_client.api_control("pause_worker")
            except Exception as e:
                self.add_log_entry(f"❌ Error al contactar con el servidor: {e}")
                return
            if ok:
                self._worker_paused = True
                self.add_log_entry("🟠 Cola pausada (no se tomarán nuevas tareas).")
            else:
                self.add_log_entry(f"⚠️ {msg}")

        self._refresh_pause_button_ui()
        self._refresh_pause_menu_ui()
        QTimer.singleShot(800, self.update_status)


    def restart_all(self):
        """
        Botón 3:
        Reinicio fuerte de cola (restart_all).
        Limpia todas las tareas y genera un dump JSON.
        El monitor del portapapeles se apaga y no se reactiva automáticamente.
        """
        if self.chk_confirm.isChecked():
            ans = QMessageBox.question(
                self,
                "Confirmar reinicio de cola",
                "¿Seguro que quieres limpiar TODA la cola de descargas?\n"
                "Se guardará un dump en logs, pero la tabla quedará vacía.",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            )
            if ans != QMessageBox.StandardButton.Yes:
                return

        # 🔴 Paso 1: detener completamente el monitor (si está activo)
        if self._clip_active or self.btn_clip_monitor.isChecked():
            try:
                self.clip.stop()
                self.clip.reset_cache()  # limpia texto y URLs detectadas
                self._clip_active = False
                self.btn_clip_monitor.setChecked(False)
                self._on_clipboard_status("Desactivado")
                self.add_log_entry("📋 Monitor del portapapeles detenido y cache limpiada antes de reiniciar.")
            except Exception as e:
                self.add_log_entry(f"⚠️ Error al detener/limpiar monitor: {e}")

        # 🧨 Paso 2: enviar orden al servidor
        try:
            ok, msg = api_client.api_control("restart_all")
        except Exception as e:
            self.add_log_entry(f"❌ Error al contactar con el servidor: {e}")
            return

        if ok:
            self.add_log_entry("🧨 Cola limpiada por completo (ver logs para el dump).")
        else:
            self.add_log_entry(f"⚠️ {msg}")

        # 🔄 Paso 3: refrescar tabla
        QTimer.singleShot(1000, self.update_status)

        # 📋 No se reinicia el monitor automáticamente
        self.add_log_entry("📋 El monitor del portapapeles permanece apagado tras el reinicio.")


    def _refresh_pause_button_ui(self):
        """
        Actualiza el texto/estilo del botón de pausa/continuar
        según self._worker_paused.
        """
        if self._worker_paused:
            # Cola pausada → ofrecer "Continuar"
            self.btn_continue.setText("▶️ Continuar cola")
            self.btn_continue.setStyleSheet(
                "QPushButton { background-color:#2196f3; color:#fff; border-radius:6px; padding:6px 12px; font-weight:bold; }"
            )
        else:
            # Cola activa → ofrecer "Pausar"
            self.btn_continue.setText("⏸️ Pausar cola")
            self.btn_continue.setStyleSheet(
                "QPushButton { background-color:#00bcd4; color:#fff; border-radius:6px; padding:6px 12px; font-weight:bold; }"
            )
            
    
    def _refresh_pause_menu_ui(self):
        """Actualiza el texto del menú de pausa según estado del worker."""
        if self._worker_paused:
            self.act_pause.setText("Reanudar cola")
        else:
            self.act_pause.setText("Pausar cola")


    def sync_worker_state(self):
        """
        Llama a /api/worker_state y sincroniza el flag _worker_paused
        y el botón de toggle.
        """
        if not self._alive:
            return
        try:
            ok, data = api_client.api_worker_state()
        except Exception as e:
            self.add_log_entry(f"⚠️ No se pudo leer estado del worker: {e}")
            return

        if not ok:
            # data contiene mensaje
            self.add_log_entry(f"⚠️ No se pudo leer estado del worker: {data}")
            return

        paused = bool(data.get("worker_paused", False))
        self._worker_paused = paused
        self._refresh_pause_button_ui()
        self._refresh_pause_menu_ui()

    

    def _confirm_enqueue(self, url: str, mode: str) -> bool:
        """
        Diálogo propio con botones centrados.
        Devuelve True si el usuario acepta.
        """
        dlg = QDialog(self)
        dlg.setWindowTitle("Confirmar")

        # 🎨 Estilo más legible
        dlg.setStyleSheet("""
        QDialog {
            background-color: #2f2f2f;
        }
        QLabel {
            color: #ffffff;
            font-size: 10pt;
        }
        QDialogButtonBox QPushButton {
            min-width: 80px;
            padding: 4px 12px;
            border-radius: 6px;
            background-color: #00bcd4;
            color: #ffffff;
            font-weight: bold;
        }
        QDialogButtonBox QPushButton:hover {
            background-color: #26c6da;
        }
        QDialogButtonBox QPushButton:disabled {
            background-color: #555555;
        }
        """)

        layout = QVBoxLayout(dlg)
        layout.setContentsMargins(20, 15, 20, 15)
        layout.setSpacing(10)

        text = f"¿Enviar a cola?\n\n{url}\n(Modo: {mode})"
        lbl = QLabel(text)
        lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(lbl)

        btn_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Yes |
            QDialogButtonBox.StandardButton.No
        )
        btn_box.button(QDialogButtonBox.StandardButton.Yes).setText("Sí")
        btn_box.button(QDialogButtonBox.StandardButton.No).setText("No")

        layout.addWidget(btn_box, alignment=Qt.AlignmentFlag.AlignCenter)

        btn_box.accepted.connect(dlg.accept)
        btn_box.rejected.connect(dlg.reject)

        return dlg.exec() == QDialog.DialogCode.Accepted


    # ---------- Envío manual ----------
    def enviar_manual(self):
        """
        Envía la URL de la caja de texto a la cola del servidor.
        - Si el modo es VIDEO y el usuario confirma, se desactiva
          automáticamente "Confirmar antes de encolar".
        - Si el modo es PLAYLIST, la confirmación permanece activa.
        """
        url = self.txt_url.text().strip()
        if not url:
            self.add_log_entry("⚠️ Ingresa una URL.")
            return

        # Leer el modo actual del combo
        mode = self.cmb_modo.currentText().strip().upper()

        if self.chk_confirm.isChecked():
            confirmado = self._confirm_enqueue(url, mode)
            if not confirmado:
                return
            # 👇 si era VIDEO y sí confirmó, apagamos la casilla
            if mode == "VIDEO":
                self.chk_confirm.setChecked(False)

        try:
            ok, msg = api_client.api_queue(url, "GUI", mode)
        except Exception as e:
            self.add_log_entry(f"❌ Error al contactar con el servidor: {e}")
            return

        # Log
        self.add_log_entry(("✅ " if ok else "⚠️ ") + msg)

        # Si era PLAYLIST, volvemos a VIDEO (pero sin tocar chk_confirm)
        if mode == "PLAYLIST":
            self.cmb_modo.setCurrentText("Video")

        # Limpiar y refrescar
        if ok:
            self.txt_url.clear()
            self.update_status()


    def open_downloads(self):
        dl = downloads_dir()
        try:
            if sys.platform.startswith("win"):
                os.startfile(dl)
            elif sys.platform == "darwin":
                os.system(f'open "{dl}"')
            else:
                os.system(f'xdg-open "{dl}"')
            self.add_log_entry("📂 Carpeta de descargas abierta.")
        except Exception as e:
            self.add_log_entry(f"❌ Error al abrir descargas: {e}")


    
    def _abrir_ubicacion(self, path: str, source: str = ""):
        """
        Abre la ubicación de la descarga.

        - Si `path` apunta a un archivo/carpeta existente:
            * Si es archivo → abre la carpeta y lo selecciona (cuando es posible).
            * Si es carpeta → abre esa carpeta.
        - Si `path` está vacío:
            * Intenta abrir la subcarpeta según `source`
              (CLIPBOARD / GUI / FILE) dentro de get_project_downloads_dir().
            * Si no existe, abre solo la carpeta general de descargas.
        """
        try:
            base_folder = downloads_dir()

            # 1) Sin path → usar origen
            if not path:
                if source in ("CLIPBOARD", "GUI", "FILE", "EXT", "MOBILE", "API"):
                    folder = os.path.join(base_folder, source)
                else:
                    folder = base_folder

                if sys.platform.startswith("win"):
                    os.startfile(folder)
                elif sys.platform == "darwin":
                    os.system(f'open "{folder}"')
                else:
                    os.system(f'xdg-open "{folder}"')

                self.add_log_entry(f"📂 Abriendo carpeta de origen: {folder}")
                return

            # 2) Con path → archivo o carpeta concreta
            if not os.path.exists(path):
                self.add_log_entry(f"⚠️ Ruta no encontrada: {path}")
                return

            if os.path.isdir(path):
                folder = path
                select_cmd = None
            else:
                folder = os.path.dirname(path)
                select_cmd = path

            if sys.platform.startswith("win"):
                if select_cmd:
                    os.system(f'explorer /select,"{select_cmd}"')
                else:
                    os.startfile(folder)
            elif sys.platform == "darwin":
                if select_cmd:
                    os.system(f'open -R "{select_cmd}"')
                else:
                    os.system(f'open "{folder}"')
            else:
                os.system(f'xdg-open "{folder}"')

            self.add_log_entry(f"📂 Abriendo ubicación: {folder}")
        except Exception as e:
            self.add_log_entry(f"❌ Error al abrir ubicación: {e}")


    def toggle_logs(self):
        visible = not self.grp_logs.isVisible()
        self.grp_logs.setVisible(visible)
        self.btn_logs.setText("📜 Ocultar Logs" if visible else "📜 Mostrar Logs")
        self.btn_logs.setChecked(visible)



    def blink_clipboard_led(self, color: str = "cyan"):
        color_map = {
            "green": "#00ff00", "yellow": "#ffeb3b",
            "red": "#f44336", "cyan": "#00ffff"
        }
        if color not in color_map:
            color = "cyan"
        self.lbl_clip_status.setStyleSheet(
            f"color: {color_map[color]}; font-size:14pt; font-weight:bold;"
        )
        QTimer.singleShot(500, lambda: self.lbl_clip_status.setStyleSheet(
            f"color: {'lime' if self._clip_active else 'red'}; font-size:14pt; font-weight:bold;"
        ))
    
    
    # ---------------------------------------------------------
    # 📋 Integración del ClipboardMonitor moderno
    # ---------------------------------------------------------
    def _on_clipboard_url(self, url: str):
        """Señal: se detectó y envió una URL desde el portapapeles."""
        self.add_log_entry(f"📋 URL detectada desde portapapeles: {url}")
        self.blink_clipboard_led("green")

    
    def _on_clipboard_status(self, status: str):
        """Señal: el monitor fue activado o desactivado."""
        self._clip_active = (status == "Activado")
        color = "lime" if self._clip_active else "red"
        self.lbl_clip_status.setStyleSheet(
            f"color:{color}; font-size:14pt; font-weight:bold;"
        )
        self.add_log_entry(f"📋 Monitoreo portapapeles: {status}")
            
            
    def toggle_clipboard(self, checked: bool):
        """
        Activa/desactiva el monitor del portapapeles.
        Se sincroniza con el botón del tray (act_clipboard).
        """

        # ---- ACTIVAR ----
        if checked:
            self._clip_active = True
            self.clip.start()

            self.btn_clip_monitor.setStyleSheet(
                "background-color:#4caf50; color:#fff; border-radius:6px; padding:6px 12px; font-weight:bold;"
            )
            self.btn_clip_monitor.setText("📋 Monitoreo Activo")

            # 🔥 SINCRONIZAR TRAY
            if hasattr(self, "act_clipboard"):
                self.act_clipboard.setChecked(True)

        # ---- DESACTIVAR ----
        else:
            self._clip_active = False
            self.clip.stop()

            self.btn_clip_monitor.setStyleSheet(
                "background-color:#607d8b; color:#fff; border-radius:6px; padding:6px 12px; font-weight:bold;"
            )
            self.btn_clip_monitor.setText("📋 Monitorear Portapapeles")

            # 🔥 SINCRONIZAR TRAY
            if hasattr(self, "act_clipboard"):
                self.act_clipboard.setChecked(False)



    # ---------------------------------------------------------
    # 🧾 Cargar URLs desde archivo
    # ---------------------------------------------------------
    def cargar_archivo_urls(self):
        """
        Abre un diálogo para seleccionar un archivo .txt con texto variado.
        Detecta TODAS las URLs (http/https) dentro del contenido y las envía
        al servidor como modo VIDEO por defecto.
        """
        from PyQt6.QtWidgets import QFileDialog

        ruta, _ = QFileDialog.getOpenFileName(
            self,
            "Seleccionar archivo de URLs o texto",
            "",
            "Archivos de texto (*.txt);;Todos los archivos (*)",
        )

        if not ruta:
            self.add_log_entry("⚠️ No se seleccionó ningún archivo.")
            return

        try:
            with open(ruta, "r", encoding="utf-8") as f:
                contenido = f.read()
        except Exception as e:
            self.add_log_entry(f"❌ Error al leer archivo: {e}")
            return

        # 🧩 Buscar todas las URLs dentro del texto (incluso mezcladas)
        urls = re.findall(r"https?://[^\s]+", contenido, flags=re.IGNORECASE)
        if not urls:
            self.add_log_entry("⚠️ No se encontraron URLs en el archivo.")
            return

        enviadas = 0
        for url in urls:
            url = url.strip().strip(".,);]")  # limpia bordes extraños

            try:
                ok, msg = api_client.api_queue(url, "FILE", "VIDEO")
            except Exception as e:
                self.add_log_entry(f"❌ Error enviando {url}: {e}")
                continue

            if ok:
                self.add_log_entry(f"✅ URL agregada desde archivo: {url}")
                enviadas += 1
            else:
                self.add_log_entry(f"⚠️ No se pudo encolar: {msg}")

        self.add_log_entry(f"🧾 Carga completada ({enviadas} URLs enviadas).")


    # ---------- Estado / Cola ----------
    def update_server_led(self, initial: bool = False):
        """
        Actualiza el indicador de estado del servidor.
        """
        alive = api_client.api_ping()
        self._alive = alive
        self.lbl_srv_status.setText("🟢 Servidor Activo" if alive else "🔴 Servidor Inaccesible")
        if initial:
            self.add_log_entry("Servidor: activo ✅" if alive else "Servidor: inaccesible ❌")


    def _clear_queue_widgets(self):
        """Elimina todos los widgets de descarga actuales del layout."""
        while self.scrollLayout.count():
            item = self.scrollLayout.takeAt(0)
            w = item.widget()
            if w is not None:
                w.deleteLater()


    def _smooth_progress(self, task_id: int, raw_progress: float, status: str) -> float:
        """
        Suaviza el progreso que viene del servidor para evitar saltos bruscos.

        Reglas:
        - PENDING -> 0% (sin suavizado)
        - Al pasar a DOWNLOADING -> 1% inmediato
        - Mientras DOWNLOADING y raw<100: avanza la mitad del tramo (no retrocede)
        - Si el primer valor de DOWNLOADING es 100%: 0 -> 1 -> 50 -> 100
        - Si ya había progreso visible (>1%) y raw llega a 100: salto directo a 100
        - Si raw baja (yt-dlp reinicia partes): se permite retroceder
        - COMPLETED -> 100% y se limpia el estado interno
        """
        status = (status or "").upper()
        raw = max(0.0, min(100.0, float(raw_progress or 0.0)))

        # Estados no-descargando: devolver real y limpiar estado
        if status != "DOWNLOADING":
            if status == "COMPLETED":
                # final: 100 y limpiar
                self._progress_state.pop(task_id, None)
                return 100.0
            # PENDING/ERROR/CANCELLED... (mostrar real y limpiar)
            self._progress_state.pop(task_id, None)
            return raw

        # ---- DOWNLOADING ----
        st = self._progress_state.get(task_id)

        # Primera vez en DOWNLOADING
        if st is None:
            # Ultra-rápido: primer raw ya es 100 → 1% ahora, 50% en el siguiente ciclo
            if raw >= 100.0:
                self._progress_state[task_id] = {
                    "shown": 1.0,
                    "raw": raw,
                    "fast_phase": 1,   # fase rápida: próximo ciclo = 50%
                }
                return 1.0
            # Caso normal: empezamos en 1% si raw>0, si raw==0 también forzamos 1% para que “encienda”
            start_shown = 1.0
            self._progress_state[task_id] = {
                "shown": start_shown,
                "raw": raw,
            }
            return start_shown

        prev_shown = float(st.get("shown", 0.0))
        prev_raw = float(st.get("raw", 0.0))
        fast_phase = int(st.get("fast_phase", 0))

        # --- Secuencia ultra-rápida (primer raw=100) ---
        if fast_phase == 1:
            # Segundo ciclo: mantener en 50% hasta que el servidor marque COMPLETED
            st["shown"] = 50.0
            st["raw"] = raw
            st["fast_phase"] = 2
            self._progress_state[task_id] = st
            return 50.0
        elif fast_phase >= 2:
            # Seguir en 50% mientras siga DOWNLOADING; al pasar a COMPLETED se mostrará 100
            st["shown"] = 50.0
            st["raw"] = raw
            self._progress_state[task_id] = st
            return 50.0

        # --- Caso normal de DOWNLOADING ---

        # Si el servidor “retrocede” (p.ej. recomienza un fragmento), permitimos bajar
        if raw < prev_raw:
            st["shown"] = raw
            st["raw"] = raw
            self._progress_state[task_id] = st
            return raw

        # Si llega raw=100 y ya mostrábamos más que el 1% inicial -> salto directo a 100
        if raw >= 100.0 and prev_shown > 1.0:
            st["shown"] = 100.0
            st["raw"] = raw
            self._progress_state[task_id] = st
            return 100.0

        # Mientras raw<100 y aumenta: avanzar mitad del tramo hacia el nuevo raw
        target = max(prev_shown, raw)
        shown = prev_shown + (target - prev_shown) / 2.0

        # Nunca retroceder por redondeos
        if shown < prev_shown:
            shown = prev_shown

        # Limitar a <100 mientras no llegue el COMPLETED
        shown = min(shown, 99.9)

        st["shown"] = shown
        st["raw"] = raw
        self._progress_state[task_id] = st
        return shown


    def _rebuild_queue_widgets(self, rows: list[dict]):
        """Reconstruye la lista de tarjetas a partir de los dicts devueltos por la API."""
        self._clear_queue_widgets()
        self.queue_items = []
        self.queue_widgets = []

        for it in rows:
            task_id = int(it.get("id", 0) or 0)

            # Mapear dict del servidor -> QueueItem
            source = it.get("source", "") or ""
            prefix = it.get("source_prefix", "") or ""
            local_raw = str(it.get("local_id", "") or "")
            local_id = f"{prefix}{local_raw}" if prefix and local_raw else ""

            url = it.get("url", "") or ""

            # Estado crudo
            status_raw = (it.get("status") or "").upper()

            # --- Rutas y nombre de archivo ---
            filepath = it.get("filepath") or ""
            filename = it.get("filename") or ""

            # 🔁 Fallback: si está COMPLETED pero no hay filepath/filename,
            # buscamos el archivo por [IDx] en la carpeta de origen.
            if status_raw == "COMPLETED" and not filepath:
                try:
                    # Carpeta base/origen como en Downloader
                    base_dir = Path(downloads_dir())
                    origin_label = sanitize_filename(source.upper()) or "OTHER"
                    task_dir = base_dir / origin_label

                    display_id = local_raw or str(task_id or "")
                    if display_id:
                        candidates = list(task_dir.glob(f"* [ID{display_id}].*"))
                        if candidates:
                            # El más reciente
                            candidate = max(candidates, key=lambda p: p.stat().st_mtime)
                            filepath = str(candidate)
                            if not filename:
                                filename = candidate.name
                except Exception:
                    # Si falla, simplemente seguimos sin filename/filepath
                    pass


            # Modo original del servidor
            mode_raw = (it.get("mode") or "").upper()
            
            # ---------- DETECTAR FORMATO REAL DEL ARCHIVO FINAL ----------
            ext = Path(filename).suffix.lower()

            if ext in [".mp3", ".m4a", ".aac", ".flac", ".wav"]:
                mode = "Audio"
            else:
                # usar modo original si no es audio
                if mode_raw == "VIDEO":
                    mode = "Video"
                elif mode_raw == "PLAYLIST":
                    mode = "Playlist"
                else:
                    mode = mode_raw.capitalize()


            # Título amigable
            title = build_friendly_title(url=url, filename=filename, mode=mode)

            # Progreso suave
            raw_progress = float(it.get("progress") or 0.0)
            progress = self._smooth_progress(task_id, raw_progress, status_raw)

            msg = it.get("error_msg") or ""
            playlist_videos = it.get("playlist_videos") or []

            q_item = QueueItem(
                id=task_id,
                source=source,
                local_id=local_id,
                url=url,
                title=title,
                mode=mode,
                progress=progress,
                status=status_raw,
                msg=msg,
                filepath=filepath,
                playlist_videos=playlist_videos,
            )

            w = DownloadItemWidget(q_item)
            w.folderClicked.connect(
                lambda path, src=q_item.source: self._abrir_ubicacion(path, src)
            )

            self.scrollLayout.addWidget(w)
            self.queue_items.append(q_item)
            self.queue_widgets.append(w)

        self.scrollLayout.addStretch(1)

        # Aplicar opciones de visibilidad y filtros actuales
        self.update_visibility_options()
        self.apply_filters()

        # Estado compacto actual
        if self._compact_mode:
            for w in self.queue_widgets:
                w.set_playlist_expanded(False)



    def apply_filters(self):
        """Aplica filtros de Estado / Origen / Tipo sobre las tarjetas."""
        estado_map = {
            "Todos": None,
            "Completado": "COMPLETED",
            "Descargando": "DOWNLOADING",
            "Pendiente": "PENDING",
            "Error": "ERROR",
            "Cancelado": "CANCELLED",
        }
        estado_f = estado_map.get(self.cmbEstado.currentText(), None)
        origen_f = self.cmbOrigen.currentText()
        tipo_f = self.cmbTipo.currentText()

        known_sources = {"CLIPBOARD", "GUI", "FILE", "EXT", "MOBILE", "API"}

        for item, widget in zip(self.queue_items, self.queue_widgets):
            visible = True

            # Filtro por estado
            if estado_f is not None and item.status != estado_f:
                visible = False

            # Filtro por origen
            if origen_f != "Todos":
                if origen_f == "OTROS":
                    # Solo mostrar los que NO son de las fuentes conocidas
                    if (item.source or "").upper() in known_sources:
                        visible = False
                else:
                    if (item.source or "").upper() != origen_f:
                        visible = False

            # Filtro por tipo (Video / Playlist / ...)
            if tipo_f != "Todos" and item.mode.lower() != tipo_f.lower():
                visible = False

            widget.setVisible(visible)

 
    def _set_origin_filter(self, source_name: str):
        """
        Cambia el combo de Origen al valor indicado
        (MOBILE, EXT, etc.), si existe.
        """
        idx = self.cmbOrigen.findText(source_name)
        if idx != -1:
            self.cmbOrigen.setCurrentIndex(idx)


    def update_visibility_options(self):
        show_origin = self.chkShowOrigin.isChecked()
        show_type = self.chkShowType.isChecked()
        show_local = self.chkShowLocalId.isChecked()
        for w in self.queue_widgets:
            w.apply_visibility_options(show_origin, show_type, show_local)



    def _update_clients_status(self, rows: list[dict]):
        """
        Actualiza los labels de estado de Móvil y Extensión
        según si hay tareas con esas fuentes en la lista.
        """
        has_ext = any((it.get("source") or "").upper() == "EXT" for it in rows)
        has_mobile = any((it.get("source") or "").upper() == "MOBILE" for it in rows)

        # Extensión
        if has_ext:
            self.lbl_ext_status.setText("🧩 Extensión: Conectada")
            self.lbl_ext_status.setStyleSheet("color:#4caf50; font-weight:bold;")
        else:
            self.lbl_ext_status.setText("🧩 Extensión: Sin actividad")
            self.lbl_ext_status.setStyleSheet("color:#f44336; font-weight:bold;")

        # Móvil
        if has_mobile:
            self.lbl_mob_status.setText("📱 Móvil: Conectado")
            self.lbl_mob_status.setStyleSheet("color:#4caf50; font-weight:bold;")
        else:
            self.lbl_mob_status.setText("📱 Móvil: Esperando...")
            self.lbl_mob_status.setStyleSheet("color:#ffc107; font-weight:bold;")


    def toggle_compact_all(self):
        self._compact_mode = not self._compact_mode
        expand = not self._compact_mode
        for w in self.queue_widgets:
            w.set_playlist_expanded(expand)
        if self._compact_mode:
            self.btnToggleCompact.setText("⇡ Expandir playlists")
        else:
            self.btnToggleCompact.setText("⇣ Compactar playlists")
            
            
 
    def update_status(self):
        """
        Actualiza el estado general (cola, servidor, worker, túnel, tray).
        """

        # 1) Estado del servidor
        self.update_server_led()

        # Si el servidor está caído → icono rojo y salimos
        if not self._alive:
            if hasattr(self, "tray"):
                self.tray.setIcon(QIcon(self.tray_icons["red"]))
            return

        # 2) Estado del worker
        self.sync_worker_state()
        self._refresh_pause_menu_ui()

        # 3) Solicitar estado al servidor
        try:
            ok, data = api_client.api_status(limit=100)
        except Exception as e:
            self.add_log_entry(f"❌ Error al obtener estado del servidor: {e}")
            return

        if not ok:
            self.add_log_entry(f"⚠️ {data}")
            return

        # 4) Reconstruir widgets UNA sola vez (estaba duplicado)
        self._rebuild_queue_widgets(data)

        # 5) Actualizar estados de móvil y extensión
        self._update_clients_status(data)

        # 6) Estado del túnel
        # Mostrar estado del túnel según la variable interna
        if self.tunnel_active:
            self.lbl_tunnel_status.setText("🌐 Túnel: Activo")
            self.lbl_tunnel_status.setStyleSheet("color:#4caf50; font-weight:bold;")
            self.led_tunnel.setStyleSheet(
                "color:#00ff00; font-size:22px; font-weight:bold;"
            )
        else:
            self.lbl_tunnel_status.setText("🌐 Túnel: Inactivo")
            self.lbl_tunnel_status.setStyleSheet("color:#f44336; font-weight:bold;")
            self.led_tunnel.setStyleSheet(
                "color:red; font-size:22px; font-weight:bold;"
            )


        # 7) Icono del tray según estado actual
        if not self._alive:
            self.tray.setIcon(QIcon(self.tray_icons["red"]))
        elif self._worker_paused:
            self.tray.setIcon(QIcon(self.tray_icons["yellow"]))
        else:
            self.tray.setIcon(QIcon(self.tray_icons["green"]))

    # ---------- Logs ----------
    def add_log_entry(self, msg: str):
        self.txt_logs.append(msg)
        self.txt_logs.ensureCursorVisible()
        logger.info(msg)


# ---------- Run ----------
def run_gui():
    app = QApplication(sys.argv)

    # 🔥 ICONO GLOBAL DEL PROGRAMA (Taskbar, Alt+Tab, Thumbnail)
    app.setWindowIcon(QIcon(resource_path("icons/main/icon_128.ico")))


    w = MVideoDkApp()
    w.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    run_gui()

