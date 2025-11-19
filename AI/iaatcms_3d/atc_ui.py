# atc_ui.py
# -------------------------------------------------------------------
# Non-blocking Tkinter popup for ATC landing approval dialog.
# The 3D OpenGL window keeps running while this popup appears.
# -------------------------------------------------------------------

import tkinter as tk
from tkinter import ttk
import threading
import queue


class ATCOverlay:
    """
    Shows a Grant / Hold / Divert popup using Tkinter,
    in a separate thread, so it does NOT freeze the 3D simulation.
    """

    def __init__(self):
        self.queue = queue.Queue()
        self.root = None

    # Ensure we have a Tk root window (hidden)
    def _ensure_root(self):
        if self.root is None:
            self.root = tk.Tk()
            self.root.withdraw()

    # ------------- BLOCKING VERSION (unused) -------------
    def ask_decision(self, flight_id, info):
        """Blocking version (not used in main.py)."""
        self._ensure_root()

        result = queue.Queue()

        def show():
            dlg = tk.Toplevel(self.root)
            dlg.title(f"ATC — {flight_id}")
            dlg.attributes("-topmost", True)

            ttk.Label(
                dlg,
                text=info,
                wraplength=360,
                justify="left"
            ).pack(padx=10, pady=8)

            def choose(dec):
                result.put(dec)
                dlg.destroy()

            frm = ttk.Frame(dlg)
            frm.pack(pady=10)

            ttk.Button(frm, text="Grant", command=lambda: choose("grant")).pack(side="left", padx=5)
            ttk.Button(frm, text="Hold", command=lambda: choose("hold")).pack(side="left", padx=5)
            ttk.Button(frm, text="Divert", command=lambda: choose("divert")).pack(side="left", padx=5)

            dlg.update_idletasks()
            w, h = dlg.winfo_width(), dlg.winfo_height()
            sw, sh = dlg.winfo_screenwidth(), dlg.winfo_screenheight()
            dlg.geometry(f"+{(sw-w)//2}+{(sh-h)//2}")

            self.root.wait_window(dlg)

        show()
        return result.get()

    # ------------- NON-BLOCKING VERSION (used in main.py) -------------
    def ask_decision_nonblocking(self, flight_id, info, callback):
        """
        Opens the dialog on a new thread.
        When user selects, callback(decision) is called.
        """

        def ui_thread():
            self._ensure_root()

            dlg = tk.Toplevel(self.root)
            dlg.title(f"ATC — {flight_id}")
            dlg.attributes("-topmost", True)

            ttk.Label(
                dlg,
                text=info,
                wraplength=360,
                justify="left"
            ).pack(padx=10, pady=8)

            def choose(dec):
                dlg.destroy()
                callback(dec)

            frm = ttk.Frame(dlg)
            frm.pack(pady=10)

            ttk.Button(frm, text="Grant", command=lambda: choose("grant")).pack(side="left", padx=5)
            ttk.Button(frm, text="Hold", command=lambda: choose("hold")).pack(side="left", padx=5)
            ttk.Button(frm, text="Divert", command=lambda: choose("divert")).pack(side="left", padx=5)

            # center the dialog
            dlg.update_idletasks()
            w, h = dlg.winfo_width(), dlg.winfo_height()
            sw, sh = dlg.winfo_screenwidth(), dlg.winfo_screenheight()
            dlg.geometry(f"+{(sw-w)//2}+{(sh-h)//2}")

            # we need a mini-loop so Tk stays responsive
            while True:
                try:
                    self.root.update()
                except:
                    break

        threading.Thread(target=ui_thread, daemon=True).start()

