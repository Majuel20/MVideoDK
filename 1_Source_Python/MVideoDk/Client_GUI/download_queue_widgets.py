# ==========================================================
# Client_GUI/download_queue_widgets.py  ✅ v20 — Tarjetas de cola de descargas
# ==========================================================
"""
Widgets visuales y modelo de datos para la cola de descargas de MVideoDk.

Mejoras v20:
- Comentarios más claros y consistentes.
- Estructura visual organizada sin modificar la lógica.
- Limpieza general y estandarización de estilos.

Incluye:
- QueueItem → modelo de datos de cada tarea.
- DownloadItemWidget → tarjeta visual para tareas individuales.

Funciones principales:
- Colores dinámicos por estado.
- Chips de origen (CLIPBOARD / GUI / FILE / EXT / MOBILE / API…).
- Barra de progreso estilizada (0–100%).
- Manejo interno de playlists (vista colapsable).
- Botón 📂 para abrir ubicación del archivo descargado.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Optional

from PyQt6.QtCore import Qt, pyqtSignal, QSize
from PyQt6.QtGui import QIcon
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame,
    QPushButton, QSizePolicy, QToolButton
)


# ==========================================================
# 🧱 Modelo de datos
# ==========================================================

@dataclass
class QueueItem:
    id: int
    source: str                 # CLIPBOARD / GUI / FILE / EXT / MOBILE / API / ...
    local_id: str               # C7, G1, F1...
    url: str
    title: str
    mode: str                   # Video / Playlist / Audio
    progress: float             # 0–100
    status: str                 # PENDING / DOWNLOADING / COMPLETED / ERROR / CANCELLED
    msg: str = ""
    filepath: str = ""
    playlist_videos: List[str] = field(default_factory=list)


# ==========================================================
# 🎨 Colores y estilos
# ==========================================================

PROGRESS_COLORS = {
    "DOWNLOADING": "#6fdc82",
    "COMPLETED":   "#28a745",
}

STATE_COLORS = {
    "COMPLETED":   {"bg": "#d1ecf1", "border": "#92cfd7", "chip": "#0c5460"},
    "DOWNLOADING": {"bg": "#d4edda", "border": "#a8d5a2", "chip": "#155724"},
    "PENDING":     {"bg": "#fff7da", "border": "#ffe8a1", "chip": "#856404"},
    "ERROR":       {"bg": "#f8d7da", "border": "#f5c0c4", "chip": "#721c24"},
    "CANCELLED":   {"bg": "#f0f0f0", "border": "#d6d6d6", "chip": "#555555"},
}

MSG_COLORS = {
    "COMPLETED":   "#0c5460",
    "DOWNLOADING": "#155724",
    "PENDING":     "#856404",
    "ERROR":       "#721c24",
    "CANCELLED":   "#555555",
}

SOURCE_COLORS = {
    "CLIPBOARD": "#0275d8",
    "GUI":       "#5cb85c",
    "FILE":      "#f0ad4e",
    "EXT":       "#00bcd4",
    "MOBILE":    "#9c27b0",
    "API":       "#8bc34a",
    "SYSTEM":    "#795548",
}


# ==========================================================
# 🎴 Widget visual para cada tarea
# ==========================================================

class DownloadItemWidget(QWidget):
    """
    Tarjeta que representa una tarea de descarga en la GUI.

    Señales:
        folderClicked(str):
            Emite la ruta del archivo o carpeta cuando el usuario pulsa 📂.
            La GUI decide el comportamiento si está vacío.
    """

    folderClicked = pyqtSignal(str)

    def __init__(
        self,
        item: QueueItem,
        show_origin: bool = True,
        show_type: bool = True,
        show_local_id: bool = True,
    ):
        super().__init__()
        self.item = item
        self.show_origin = show_origin
        self.show_type = show_type
        self.show_local_id = show_local_id

        # Área playlist (si aplica)
        self.playlistFrame: Optional[QFrame] = None
        self.playlistListWidget: Optional[QFrame] = None
        self.btnPlaylistToggle: Optional[QPushButton] = None
        self.userPlaylistExpanded: bool = True

        self._build_ui()
        self.apply_data()
        self.apply_visibility_options(show_origin, show_type, show_local_id)

    # ------------------------------------------------------
    # 🧱 Construcción de la tarjeta
    # ------------------------------------------------------
    def _build_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)

        self.container = QFrame()
        self.container.setFrameShape(QFrame.Shape.NoFrame)
        self.container.setObjectName("cardFrame")

        card_layout = QVBoxLayout(self.container)
        card_layout.setContentsMargins(10, 6, 10, 6)
        card_layout.setSpacing(4)

        # ---------- Encabezado ----------
        header_layout = QHBoxLayout()
        header_layout.setSpacing(6)

        self.lblIndex = QLabel()
        self.lblIndex.setStyleSheet(
            "font-weight:bold; color:#000000; background:transparent;"
        )

        self.lblOrigin = QLabel()
        self.lblOrigin.setObjectName("originChip")
        self.lblOrigin.setStyleSheet(
            "border-radius:8px; padding:2px 6px; font-size:9px; "
            "color:white; background:transparent;"
        )

        self.lblLocalId = QLabel()
        self.lblLocalId.setStyleSheet("color:#666; font-size:9px; background:transparent;")

        self.lblType = QLabel()
        self.lblType.setStyleSheet("color:#666; font-size:9px; background:transparent;")

        header_layout.addWidget(self.lblIndex)
        header_layout.addSpacing(4)
        header_layout.addWidget(self.lblOrigin)
        header_layout.addWidget(self.lblLocalId)
        header_layout.addWidget(self.lblType)
        header_layout.addStretch(1)

        # ---------- Chip de estado ----------
        self.lblStatusChip = QLabel()
        self.lblStatusChip.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lblStatusChip.setMinimumWidth(90)
        self.lblStatusChip.setStyleSheet(
            "border-radius:12px; padding:2px 10px; font-weight:bold; "
            "font-size:9px; color:white;"
        )
        header_layout.addWidget(self.lblStatusChip)

        # ---------- Botón carpeta ----------
        self.btnFolder = QToolButton()
        self.btnFolder.setAutoRaise(True)
        self.btnFolder.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btnFolder.setToolTip("Abrir carpeta de descarga")
        self.btnFolder.setIconSize(QSize(18, 18))

        folder_icon = QIcon.fromTheme("folder-open")
        if folder_icon.isNull():
            self.btnFolder.setText("📂")
            self.btnFolder.setStyleSheet(
                "QToolButton { border:none; background:transparent; "
                "font-size:16px; color:#444; }"
                "QToolButton:hover:enabled { background:rgba(0,0,0,0.08); border-radius:6px; }"
            )
            self.btnFolder.setFixedSize(28, 22)
        else:
            self.btnFolder.setIcon(folder_icon)
            self.btnFolder.setStyleSheet(
                "QToolButton { border:none; background:transparent; }"
                "QToolButton:hover:enabled { background:rgba(0,0,0,0.08); border-radius:6px; }"
            )

        self.btnFolder.clicked.connect(self._on_folder_clicked)
        header_layout.addWidget(self.btnFolder)

        card_layout.addLayout(header_layout)

        # ---------- URL ----------
        self.lblUrl = QLabel()
        self.lblUrl.setStyleSheet("color:#888; font-size:9px; background:transparent;")
        card_layout.addWidget(self.lblUrl)

        # ---------- Título ----------
        self.lblTitle = QLabel()
        self.lblTitle.setStyleSheet(
            "font-weight:bold; font-size:11px; background:transparent; color:#000000;"
        )
        card_layout.addWidget(self.lblTitle)

        # ---------- Barra de progreso ----------
        self.progressBar = QFrame()
        self.progressBar.setObjectName("progressBarBg")
        self.progressBar.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.progressBar.setFixedHeight(6)

        progress_layout = QHBoxLayout(self.progressBar)
        progress_layout.setContentsMargins(0, 0, 0, 0)
        progress_layout.setSpacing(0)

        self.progressFill = QFrame()
        self.progressFill.setObjectName("progressFill")

        self.progressEmpty = QFrame()
        self.progressEmpty.setObjectName("progressEmpty")

        progress_layout.addWidget(self.progressFill)
        progress_layout.addWidget(self.progressEmpty)
        self.progressLayout = progress_layout

        self.progressLabel = QLabel()
        self.progressLabel.setStyleSheet(
            "color:#444; font-size:10px; font-weight:bold; margin-left:4px; background:transparent;"
        )
        self.progressLabel.setAlignment(Qt.AlignmentFlag.AlignRight)

        progress_row = QHBoxLayout()
        progress_row.setContentsMargins(0, 0, 0, 0)
        progress_row.addWidget(self.progressBar, 4)
        progress_row.addWidget(self.progressLabel)

        card_layout.addLayout(progress_row)

        # ---------- Mensaje ----------
        self.lblMsg = QLabel()
        self.lblMsg.setStyleSheet("font-size:9px; font-style:italic; margin-top:2px; background:transparent;")
        self.lblMsg.setVisible(False)
        card_layout.addWidget(self.lblMsg)

        # ---------- Playlist (si aplica) ----------
        if self.item.mode.lower() == "playlist" and self.item.playlist_videos:
            self._build_playlist_area(card_layout)

        main_layout.addWidget(self.container)

        # ---------- Estilo base ----------
        self.setStyleSheet("""
        #cardFrame {
            border-radius: 10px;
            border: 2px solid #cccccc;
        }
        #progressBarBg {
            background-color: #e5e5e5;
            border-radius: 4px;
        }
        #progressFill {
            background-color: #28a745;
            border-radius: 4px;
        }
        #progressEmpty {
            background-color: transparent;
        }
        """)

    # ------------------------------------------------------
    # 📜 Playlist
    # ------------------------------------------------------
    def _build_playlist_area(self, parent_layout: QVBoxLayout):
        self.playlistFrame = QFrame()
        self.playlistFrame.setObjectName("playlistFrame")

        pl_layout = QVBoxLayout(self.playlistFrame)
        pl_layout.setContentsMargins(6, 4, 6, 4)
        pl_layout.setSpacing(3)

        # Botón desplegable
        self.btnPlaylistToggle = QPushButton()
        self.btnPlaylistToggle.setCheckable(True)
        self.btnPlaylistToggle.setChecked(True)
        self.btnPlaylistToggle.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btnPlaylistToggle.setStyleSheet(
            "QPushButton { border:none; background:transparent; font-size:9px; "
            "font-weight:bold; color:#444; text-align:left; }"
        )
        self.btnPlaylistToggle.clicked.connect(self._toggle_playlist)
        pl_layout.addWidget(self.btnPlaylistToggle)

        # Lista de vídeos
        self.playlistListWidget = QFrame()
        inner_layout = QVBoxLayout(self.playlistListWidget)
        inner_layout.setContentsMargins(8, 4, 8, 4)
        inner_layout.setSpacing(2)

        max_show = 4
        for title in self.item.playlist_videos[:max_show]:
            lbl = QLabel(f"• {title}")
            lbl.setStyleSheet("font-size:9px; color:#555; background:transparent;")
            inner_layout.addWidget(lbl)

        if len(self.item.playlist_videos) > max_show:
            rest = len(self.item.playlist_videos) - max_show
            plus = QLabel(f"... y {rest} más")
            plus.setStyleSheet(
                "font-size:9px; color:#888; font-style:italic; background:transparent;"
            )
            inner_layout.addWidget(plus)

        pl_layout.addWidget(self.playlistListWidget)
        parent_layout.addWidget(self.playlistFrame)

        self.userPlaylistExpanded = True
        self._update_playlist_header(True)

    def _update_playlist_header(self, expanded: bool):
        arrow = "▼" if expanded else "►"
        count = len(self.item.playlist_videos)
        if self.btnPlaylistToggle:
            self.btnPlaylistToggle.setText(
                f"{arrow} Videos de la playlist ({count})"
            )

    def _toggle_playlist(self):
        if not self.playlistListWidget:
            return
        self.userPlaylistExpanded = not self.userPlaylistExpanded
        self.playlistListWidget.setVisible(self.userPlaylistExpanded)
        self.btnPlaylistToggle.setChecked(self.userPlaylistExpanded)
        self._update_playlist_header(self.userPlaylistExpanded)

    def set_playlist_expanded(self, expanded: bool):
        """Permite expandir/colapsar desde controles globales."""
        if not (self.playlistListWidget and self.btnPlaylistToggle):
            return
        self.userPlaylistExpanded = expanded
        self.playlistListWidget.setVisible(expanded)
        self.btnPlaylistToggle.setChecked(expanded)
        self._update_playlist_header(expanded)

    # ======================================================
    # 🔄 Actualización visual
    # ======================================================
    def apply_data(self):
        """Actualiza todo el contenido visual desde self.item."""
        self.lblIndex.setText(f"#{self.item.id}")
        self.lblOrigin.setText(self.item.source)
        self.lblLocalId.setText(self.item.local_id)
        self.lblType.setText(self.item.mode)

        # Color del chip de origen
        src_color = SOURCE_COLORS.get(self.item.source, "#777777")
        self.lblOrigin.setStyleSheet(
            f"border-radius:8px; padding:2px 6px; font-size:9px; color:white; "
            f"background-color:{src_color};"
        )

        self.lblUrl.setText(self.item.url)
        self.lblTitle.setText(self.item.title)

        self.set_status(self.item.status)
        self.set_progress(self.item.progress)
        self._apply_message()

        completed = (self.item.status.upper() == "COMPLETED")
        self.btnFolder.setEnabled(completed)

        if completed and self.item.filepath:
            self.btnFolder.setToolTip("Abrir carpeta de la descarga")
        elif completed:
            self.btnFolder.setToolTip("Abrir carpeta del origen")
        else:
            self.btnFolder.setToolTip("Disponible cuando la descarga esté completada")

    def _apply_message(self):
        msg = (self.item.msg or "").strip()

        if not msg and self.item.status.upper() == "CANCELLED":
            msg = "Cancelado por usuario."

        self.lblMsg.setText(msg)
        self.lblMsg.setVisible(bool(msg))

        if msg:
            color = MSG_COLORS.get(self.item.status.upper(), "#555555")
            self.lblMsg.setStyleSheet(
                f"font-size:9px; font-style:italic; margin-top:2px; "
                f"color:{color}; background:transparent;"
            )

    def set_status(self, status: str):
        """Aplica colores y chip de estado."""
        status = status.upper()
        self.item.status = status

        colors = STATE_COLORS.get(status, STATE_COLORS["PENDING"])

        self.container.setStyleSheet(
            f"#cardFrame {{ background-color:{colors['bg']}; "
            f"border:2px solid {colors['border']}; border-radius:10px; }}"
        )
        self.lblStatusChip.setText(status)
        self.lblStatusChip.setStyleSheet(
            f"border-radius:12px; padding:2px 10px; font-weight:bold; font-size:9px; "
            f"color:white; background-color:{colors['chip']};"
        )

        # Color de barra de progreso según estado
        progress_color = PROGRESS_COLORS.get(status, "#28a745")
        self.progressFill.setStyleSheet(
            f"background-color:{progress_color}; border-radius:4px;"
        )

        self._apply_message()

        completed = (self.item.status == "COMPLETED")
        self.btnFolder.setEnabled(completed)

    def set_progress(self, value: float):
        """Actualiza la barra de progreso con proporciones reales."""
        self.item.progress = value
        pct = max(0.0, min(100.0, value))
        self.progressLabel.setText(f"{pct:.1f}%")

        if pct <= 0.0:
            # Solo gris
            self.progressFill.setVisible(False)
            self.progressEmpty.setVisible(True)
            self.progressLayout.setStretch(0, 0)
            self.progressLayout.setStretch(1, 1)

        elif pct >= 100.0:
            # Todo verde
            self.progressFill.setVisible(True)
            self.progressEmpty.setVisible(False)
            self.progressLayout.setStretch(0, 1)
            self.progressLayout.setStretch(1, 0)

        else:
            # Mixto proporcional
            self.progressFill.setVisible(True)
            self.progressEmpty.setVisible(True)
            left = int(pct)
            right = max(1, 100 - left)
            self.progressLayout.setStretch(0, left)
            self.progressLayout.setStretch(1, right)

    def apply_visibility_options(self, show_origin: bool, show_type: bool, show_local_id: bool):
        """Controla visibilidad de chips según preferencias globales."""
        self.lblOrigin.setVisible(show_origin)
        self.lblType.setVisible(show_type)
        self.lblLocalId.setVisible(show_local_id)

    # ======================================================
    # 🖱️ Eventos
    # ======================================================
    def _on_folder_clicked(self):
        """Emite folderClicked solo si la tarea está COMPLETED."""
        if self.item.status.upper() != "COMPLETED":
            return
        self.folderClicked.emit(self.item.filepath or "")
