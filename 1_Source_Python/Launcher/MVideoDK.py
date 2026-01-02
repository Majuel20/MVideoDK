import subprocess
import os
import sys
import threading
import time
import tkinter as tk
from tkinter import ttk
from PIL import Image, ImageTk


def resource_path(relative_path: str) -> str:
    """
    Devuelve la ruta correcta tanto en modo desarrollo como en PyInstaller ONEFILE.
    - En ONEFILE: usa sys._MEIPASS (carpeta temporal donde PyInstaller extrae datas).
    - En dev: usa la carpeta del script.
    """
    base_path = getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base_path, relative_path)


def start_core_app():
    """Inicia el CORE (ONEDIR) que vive junto al launcher exe."""
    core_exe = os.path.join(os.path.dirname(sys.executable), "MVideoDK_core.exe")

    # Si no existe, aborta silencioso (o podrías mostrar un mensaje)
    if not os.path.exists(core_exe):
        return

    subprocess.Popen(
        [core_exe],
        creationflags=subprocess.CREATE_NO_WINDOW,
        shell=False
    )


def animate_progress(bar, root):
    """Animación suave de la barra de progreso."""
    for i in range(100):
        bar["value"] = i
        time.sleep(0.02)
        try:
            root.update_idletasks()
        except tk.TclError:
            return
    try:
        root.destroy()
    except tk.TclError:
        pass


def show_splash():
    """Crea y muestra la pantalla de carga."""
    root = tk.Tk()
    root.overrideredirect(True)
    root.attributes("-topmost", True)

    # Imagen (desde Iconos/)
    splash_path = resource_path(os.path.join("Iconos", "splash_clean_600x282.png"))
    img = Image.open(splash_path)
    splash_img = ImageTk.PhotoImage(img)

    w, h = img.width, img.height

    canvas = tk.Canvas(root, width=w, height=h, highlightthickness=0, bg="#000000")
    canvas.pack()
    canvas.create_image(0, 0, anchor="nw", image=splash_img)

    # Estilo barra
    style = ttk.Style()
    style.theme_use("clam")

    style.configure(
        "MVideo.Horizontal.TProgressbar",
        troughcolor="#222222",
        background="#00f9ff",
        bordercolor="#333333",
        lightcolor="#00f9ff",
        darkcolor="#00f9ff",
        borderwidth=1,
        thickness=8
    )

    bar = ttk.Progressbar(
        root,
        orient="horizontal",
        length=w - 40,
        mode="determinate",
        style="MVideo.Horizontal.TProgressbar"
    )
    bar.place(x=20, y=h - 35)

    label = tk.Label(
        root,
        text="Iniciando MVideoDK...",
        bg="#000000",
        fg="#ffffff",
        font=("Segoe UI", 11)
    )
    label.place(x=20, y=h - 60)

    # Centrado
    root.update_idletasks()
    screen_w = root.winfo_screenwidth()
    screen_h = root.winfo_screenheight()
    x = (screen_w // 2) - (w // 2)
    y = (screen_h // 2) - (h // 2)
    root.geometry(f"{w}x{h}+{x}+{y}")

    # Hilos
    threading.Thread(target=start_core_app, daemon=True).start()
    threading.Thread(target=animate_progress, args=(bar, root), daemon=True).start()

    root.mainloop()


if __name__ == "__main__":
    show_splash()
