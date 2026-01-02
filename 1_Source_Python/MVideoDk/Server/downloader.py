# ==========================================================
# Server/downloader.py  — v20 Orquestador de descarga (multi-driver)
# ==========================================================
"""
Orquestador central de descargas para MVideoDK.

Responsabilidades:
- Elegir el downloader adecuado según la URL.
- DouyinDownloader tiene prioridad absoluta.
- Si ningún driver reconoce la URL: marcar la tarea como error.
- Compatible con cancelación por Event (worker).

Drivers incluidos:
    • DouyinDownloader  → URLs de Douyin / IESDouyin
    • YTDownloader      → Fallback para todo lo demás (yt-dlp)
"""

from threading import Event
from Server.downloaders.ytdlp_downloader import YTDownloader
from Server.downloaders.douyin_downloader import DouyinDownloader
from Server.database import Database, STATUS_ERROR

# Instancia global de DB (segura para uso multihilo en tu implementación)
db = Database()


class Downloader:
    """
    Selecciona automáticamente el downloader correcto según la URL.
    La prioridad es:
        1) DouyinDownloader
        2) YTDownloader (fallback universal)
    """

    def __init__(self):
        # Lista ordenada de drivers disponibles
        self.drivers = [
            DouyinDownloader(),  # prioridad 1
            YTDownloader(),      # fallback universal
        ]

    # ------------------------------------------------------
    # 🔽 EJECUCIÓN DE UNA TAREA
    # ------------------------------------------------------
    def run(self, task_row, cancel_event: Event | None = None) -> None:
        """
        Ejecuta la descarga con el driver adecuado.

        Args:
            task_row: fila SQLite completa de la tarea.
            cancel_event: Event opcional para abortar la descarga.

        Si ningún driver soporta la URL → estado ERROR.
        """
        if not task_row:
            return

        url = task_row[1]

        # Buscar el primer driver que soporte esta URL
        for driver in self.drivers:
            if driver.supports(url):
                return driver.run(task_row, cancel_event)

        # Si ningún driver reconoce la URL, registrar error
        task_id = task_row[0]
        db.update_status(task_id, STATUS_ERROR, error="No downloader available for this URL.")
