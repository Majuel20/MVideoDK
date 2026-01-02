# ==========================================================
# Server/database.py  ✅ v20 — Capa de acceso a datos (SQLite)
# ==========================================================
"""
Capa de acceso a datos del servidor MVideoDK.

Proporciona:
- Esquema SQLite para cola de descargas
- Gestión segura de concurrencia con RLock
- Contadores locales por fuente (GUI, EXT, MOBILE, etc.)
- Utilidades de mantenimiento (reset, limpieza de tareas atascadas)

La ruta de la base de datos proviene de AppConfig → [paths] database_path.
"""

import sqlite3
import threading
from pathlib import Path

from Core.paths import database_path
from Core.logger import LoggerFactory
from Core.app_config import AppConfig
from Config.default_config import get_source_prefix


logger = LoggerFactory.get_logger("DATABASE")

# 🔒 Bloqueo reentrante para garantizar seguridad multihilo
lock = threading.RLock()

# ==========================================================
# 📌 CONSTANTES DE ESTADO
# ==========================================================
STATUS_PENDING = "PENDING"
STATUS_DOWNLOADING = "DOWNLOADING"
STATUS_COMPLETED = "COMPLETED"
STATUS_ERROR = "ERROR"
STATUS_CANCELLED = "CANCELLED"


# ==========================================================
# 🗄️ CLASE PRINCIPAL
# ==========================================================
class Database:
    """
    Capa principal para acceso a la base de datos SQLite.

    Funcionalidades:
        - Inicializar esquema
        - Insertar tareas
        - Actualizar estado/progreso/errores
        - Gestionar contadores locales
        - Limpieza y reinicios
    """

    def __init__(self):
        self.db_path = database_path()
        self._ensure_schema()
        logger.info(f"🧱 Base de datos inicializada en {self.db_path}")

    # ------------------------------------------------------
    # 🔗 CONEXIÓN Y ESQUEMA
    # ------------------------------------------------------
    def _connect(self) -> sqlite3.Connection:
        """Crea conexión con PRAGMAs para mejorar concurrencia y rendimiento."""
        conn = sqlite3.connect(self.db_path, check_same_thread=False)
        conn.execute("PRAGMA journal_mode=WAL;")
        conn.execute("PRAGMA synchronous=NORMAL;")
        conn.execute("PRAGMA foreign_keys=ON;")
        return conn

    def _ensure_schema(self) -> None:
        """Crea tablas e índices si no existen (idempotente)."""
        with self._connect() as conn:
            c = conn.cursor()

            c.execute(
                """
                CREATE TABLE IF NOT EXISTS tasks (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    url TEXT NOT NULL,
                    source TEXT,
                    local_id INTEGER DEFAULT 0,
                    source_prefix TEXT DEFAULT '',
                    mode TEXT DEFAULT 'VIDEO',
                    filename TEXT,
                    filepath TEXT,
                    status TEXT DEFAULT 'PENDING',
                    progress REAL DEFAULT 0.0,
                    retry_count INTEGER DEFAULT 0,
                    added_at TEXT DEFAULT (datetime('now')),
                    completed_at TEXT,
                    error_msg TEXT
                );
                """
            )

            c.execute("CREATE INDEX IF NOT EXISTS idx_tasks_status   ON tasks(status)")
            c.execute("CREATE INDEX IF NOT EXISTS idx_tasks_added_at ON tasks(added_at)")

            c.execute(
                """
                CREATE TABLE IF NOT EXISTS counters (
                    source TEXT PRIMARY KEY,
                    last_local_id INTEGER DEFAULT 0
                );
                """
            )

            conn.commit()

    # ======================================================
    # 🧩 OPERACIONES PRINCIPALES (CRUD)
    # ======================================================
    def add_task(self, url: str, source: str = "GUI", mode: str = "VIDEO"):
        """
        Inserta una nueva tarea si no existe otra PENDING o DOWNLOADING
        con la misma URL.

        Returns:
            - id nuevo
            - None si se considera duplicado
        """
        with lock:
            with self._connect() as conn:
                c = conn.cursor()

                # Evitar duplicados en cola activa
                c.execute(
                    "SELECT id FROM tasks WHERE url=? AND status IN (?, ?)",
                    (url, STATUS_PENDING, STATUS_DOWNLOADING),
                )
                if c.fetchone():
                    logger.info(f"Tarea duplicada ignorada: {url}")
                    return None

                local_id = self.get_next_local_id(source)
                prefix = get_source_prefix(source)

                c.execute(
                    """
                    INSERT INTO tasks (url, source, local_id, source_prefix, mode)
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    (url, source, local_id, prefix, mode),
                )
                conn.commit()

                task_id = c.lastrowid
                logger.info(f"Tarea agregada #{task_id}: {url}")
                return task_id

    def get_task_by_id(self, task_id: int):
        """Devuelve el registro completo de una tarea por ID."""
        with lock:
            with self._connect() as conn:
                c = conn.cursor()
                c.execute("SELECT * FROM tasks WHERE id=?", (task_id,))
                return c.fetchone()

    def get_next_pending(self):
        """Devuelve la siguiente tarea pendiente (orden ascendente por ID)."""
        with lock:
            with self._connect() as conn:
                c = conn.cursor()
                c.execute(
                    "SELECT * FROM tasks WHERE status=? ORDER BY id ASC LIMIT 1",
                    (STATUS_PENDING,),
                )
                return c.fetchone()

    def update_status(
        self,
        task_id: int,
        status: str,
        progress: float | None = None,
        error: str | None = None,
        filename: str | None = None,
        filepath: str | None = None,
        completed_at: str | None = None,
    ) -> None:
        """
        Actualiza múltiples campos de manera segura.
        Solo se aplican los valores que no son None.
        """
        with lock:
            with self._connect() as conn:
                c = conn.cursor()

                fields = {"status": status}
                if progress is not None:
                    fields["progress"] = progress
                if error is not None:
                    fields["error_msg"] = error
                if filename is not None:
                    fields["filename"] = filename
                if filepath is not None:
                    fields["filepath"] = filepath
                if completed_at is not None:
                    fields["completed_at"] = completed_at

                set_clause = ", ".join(f"{k}=?" for k in fields.keys())
                params = list(fields.values()) + [task_id]

                c.execute(f"UPDATE tasks SET {set_clause} WHERE id=?", params)
                conn.commit()

    def bump_retry(self, task_id: int) -> None:
        """Aumenta en 1 el contador de reintentos de una tarea."""
        with lock:
            with self._connect() as conn:
                conn.execute(
                    "UPDATE tasks SET retry_count=retry_count+1 WHERE id=?",
                    (task_id,),
                )
                conn.commit()

    def reset_task(self, task_id: int) -> None:
        """Reinicia una tarea PENDING borrando progreso y errores."""
        with lock:
            with self._connect() as conn:
                conn.execute(
                    """
                    UPDATE tasks
                    SET status=?,
                        progress=0,
                        error_msg=NULL,
                        completed_at=NULL
                    WHERE id=?
                    """,
                    (STATUS_PENDING, task_id),
                )
                conn.commit()

    def delete_task(self, task_id: int) -> None:
        """Elimina una tarea por ID."""
        with lock:
            with self._connect() as conn:
                conn.execute("DELETE FROM tasks WHERE id=?", (task_id,))
                conn.commit()

    def list_tasks(self, limit: int = 50, offset: int = 0):
        """
        Lista tareas de forma paginada (orden DESC por id).
        """
        with lock:
            with self._connect() as conn:
                c = conn.cursor()
                c.execute(
                    """
                    SELECT
                        id, url, status, progress, source, added_at, error_msg,
                        retry_count, completed_at, filename, filepath,
                        local_id, source_prefix, mode
                    FROM tasks
                    ORDER BY id DESC
                    LIMIT ? OFFSET ?
                    """,
                    (limit, offset),
                )
                return c.fetchall()

    def get_next_local_id(self, source: str) -> int:
        """
        Devuelve el próximo ID incremental por fuente.
        Si no existe registro para esa fuente, se crea comenzando en 1.
        """
        with lock:
            with self._connect() as conn:
                c = conn.cursor()
                source = source or "UNKNOWN"

                c.execute("SELECT last_local_id FROM counters WHERE source=?", (source,))
                row = c.fetchone()

                if row:
                    new_id = row[0] + 1
                    c.execute(
                        "UPDATE counters SET last_local_id=? WHERE source=?",
                        (new_id, source),
                    )
                else:
                    new_id = 1
                    c.execute(
                        "INSERT INTO counters (source, last_local_id) VALUES (?, ?)",
                        (source, new_id),
                    )

                conn.commit()
                return new_id

    # ======================================================
    # 🧹 MANTENIMIENTO / LIMPIEZA
    # ======================================================
    def reset_counters(self) -> None:
        """Elimina todos los contadores locales."""
        with lock:
            with self._connect() as conn:
                conn.execute("DELETE FROM counters")
                conn.commit()

        logger.info("🔁 Contadores de fuentes reiniciados.")

    def reset_tasks_and_ids(self) -> None:
        """
        Elimina todas las tareas y reinicia el AUTOINCREMENT.
        Utilizado por funciones de reinicio general.
        """
        with lock:
            with self._connect() as conn:
                conn.execute("DELETE FROM tasks")
                conn.execute("DELETE FROM sqlite_sequence WHERE name='tasks'")
                conn.commit()
                conn.execute("VACUUM")

        logger.info("🧨 Tabla 'tasks' vaciada y autoincrement reiniciado.")

    def clear_all(self) -> None:
        """Elimina todas las tareas (para mantenimiento manual)."""
        with lock:
            with self._connect() as conn:
                conn.execute("DELETE FROM tasks")
                conn.commit()

        logger.warning("🧨 Todas las tareas han sido eliminadas de la base de datos.")

    def clean_stuck_tasks(self) -> None:
        """
        Marca como PENDING todas las tareas que quedaron en DOWNLOADING
        después de cierres inesperados del servidor.
        """
        with lock:
            with self._connect() as conn:
                c = conn.cursor()
                c.execute(
                    "UPDATE tasks SET status=? WHERE status=?",
                    (STATUS_PENDING, STATUS_DOWNLOADING),
                )
                affected = c.rowcount or 0
                conn.commit()

        if affected > 0:
            logger.info(f"♻️ {affected} tarea(s) recuperadas de estado DOWNLOADING.")
        else:
            logger.info("✅ No había tareas atascadas.")
