"""Interface gráfica (tkinter) do wslView."""
from __future__ import annotations

import tkinter as tk
from tkinter import messagebox, ttk

from wsl_manager import Distro, WslNotFoundError, list_distros, shutdown_all, start_distro, stop_distro

WINDOW_TITLE = "wslView"
WINDOW_SIZE = "480x320"
COLUMNS = ("name", "state", "version")


class WslViewApp(tk.Tk):
    """Janela principal do gerenciador de distros WSL."""

    def __init__(self) -> None:
        super().__init__()
        self.title(WINDOW_TITLE)
        self.geometry(WINDOW_SIZE)
        self.minsize(420, 280)

        self._build_widgets()
        self.refresh()

    def _build_widgets(self) -> None:
        tree_frame = ttk.Frame(self)
        tree_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        self.tree = ttk.Treeview(tree_frame, columns=COLUMNS, show="headings", selectmode="browse")
        self.tree.heading("name", text="Distro")
        self.tree.heading("state", text="Status")
        self.tree.heading("version", text="WSL")
        self.tree.column("name", width=220)
        self.tree.column("state", width=120, anchor=tk.CENTER)
        self.tree.column("version", width=60, anchor=tk.CENTER)
        self.tree.pack(fill=tk.BOTH, expand=True, side=tk.LEFT)

        scrollbar = ttk.Scrollbar(tree_frame, orient=tk.VERTICAL, command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(fill=tk.Y, side=tk.RIGHT)

        button_frame = ttk.Frame(self)
        button_frame.pack(fill=tk.X, padx=10, pady=(0, 10))

        ttk.Button(button_frame, text="Refresh", command=self.refresh).pack(side=tk.LEFT)
        ttk.Button(button_frame, text="Start", command=self._on_start).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Stop", command=self._on_stop).pack(side=tk.LEFT)
        ttk.Button(button_frame, text="Shutdown All", command=self._on_shutdown_all).pack(side=tk.RIGHT)

        self.status_var = tk.StringVar(value="")
        ttk.Label(self, textvariable=self.status_var, anchor=tk.W).pack(fill=tk.X, padx=10, pady=(0, 5))

    def refresh(self) -> None:
        self.tree.delete(*self.tree.get_children())
        try:
            distros = list_distros()
        except WslNotFoundError:
            self.status_var.set("wsl.exe não encontrado. O WSL está instalado?")
            return

        if not distros:
            self.status_var.set("Nenhuma distro WSL instalada.")
            return

        for distro in distros:
            label = f"{distro.name} *" if distro.is_default else distro.name
            self.tree.insert("", tk.END, iid=distro.name, values=(label, distro.state, distro.version))

        self.status_var.set(f"{len(distros)} distro(s) encontrada(s).")

    def _selected_distro(self) -> str | None:
        selection = self.tree.selection()
        if not selection:
            messagebox.showinfo(WINDOW_TITLE, "Selecione uma distro na lista.")
            return None
        return selection[0]

    def _on_start(self) -> None:
        name = self._selected_distro()
        if name is None:
            return
        try:
            start_distro(name)
        except WslNotFoundError as exc:
            messagebox.showerror(WINDOW_TITLE, str(exc))
            return
        self.refresh()

    def _on_stop(self) -> None:
        name = self._selected_distro()
        if name is None:
            return
        try:
            stop_distro(name)
        except WslNotFoundError as exc:
            messagebox.showerror(WINDOW_TITLE, str(exc))
            return
        self.refresh()

    def _on_shutdown_all(self) -> None:
        try:
            shutdown_all()
        except WslNotFoundError as exc:
            messagebox.showerror(WINDOW_TITLE, str(exc))
            return
        self.refresh()
