"""Interface gráfica (CustomTkinter) do wslView.

CustomTkinter não tem um widget de tabela equivalente ao ttk.Treeview,
então a lista de distros é montada como linhas dentro de um
CTkScrollableFrame. Diálogos (messagebox) continuam do tkinter puro,
pois o CustomTkinter não oferece substituto tematizado para eles.
"""
from __future__ import annotations

import tkinter as tk
from tkinter import messagebox

import customtkinter as ctk

from wsl_manager import (
    Distro,
    WslNotFoundError,
    get_os_pretty_name,
    list_distros,
    shutdown_all,
    start_distro,
    stop_distro,
)

WINDOW_TITLE = "wslView"
WINDOW_SIZE = "620x360"
COLUMN_WIDTHS = (200, 100, 50, 190)
SELECTED_COLOR = ("gray80", "gray25")

ctk.set_appearance_mode("System")
ctk.set_default_color_theme("blue")


class WslViewApp(ctk.CTk):
    """Janela principal do gerenciador de distros WSL."""

    def __init__(self) -> None:
        super().__init__()
        self.title(WINDOW_TITLE)
        self.geometry(WINDOW_SIZE)
        self.minsize(480, 320)

        self._selected_name: str | None = None
        self._row_frames: dict[str, ctk.CTkFrame] = {}

        self._build_widgets()
        self.refresh()

    def _build_widgets(self) -> None:
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.pack(fill="x", padx=10, pady=(10, 0))
        for text, width in zip(("Distro", "Status", "WSL", "S.O."), COLUMN_WIDTHS):
            ctk.CTkLabel(
                header, text=text, width=width, anchor="w", font=ctk.CTkFont(weight="bold")
            ).pack(side="left", padx=4)

        self.list_frame = ctk.CTkScrollableFrame(self)
        self.list_frame.pack(fill="both", expand=True, padx=10, pady=10)

        button_frame = ctk.CTkFrame(self, fg_color="transparent")
        button_frame.pack(fill="x", padx=10, pady=(0, 10))

        ctk.CTkButton(button_frame, text="Refresh", command=self.refresh, width=90).pack(side="left")
        ctk.CTkButton(button_frame, text="Start", command=self._on_start, width=90).pack(
            side="left", padx=5
        )
        ctk.CTkButton(button_frame, text="Stop", command=self._on_stop, width=90).pack(side="left")
        ctk.CTkButton(
            button_frame,
            text="Shutdown All",
            command=self._on_shutdown_all,
            width=120,
            fg_color="#b3261e",
            hover_color="#8c1d17",
        ).pack(side="right")

        self.status_var = tk.StringVar(value="")
        ctk.CTkLabel(self, textvariable=self.status_var, anchor="w").pack(
            fill="x", padx=10, pady=(0, 5)
        )

    def refresh(self) -> None:
        for frame in self._row_frames.values():
            frame.destroy()
        self._row_frames.clear()
        self._selected_name = None

        try:
            distros = list_distros()
        except WslNotFoundError:
            self.status_var.set("wsl.exe não encontrado. O WSL está instalado?")
            return

        if not distros:
            self.status_var.set("Nenhuma distro WSL instalada.")
            return

        for distro in distros:
            self._add_row(distro)

        self.status_var.set(f"{len(distros)} distro(s) encontrada(s).")

    def _add_row(self, distro: Distro) -> None:
        os_name = get_os_pretty_name(distro.name) if distro.state == "Running" else None
        label = f"{distro.name} *" if distro.is_default else distro.name
        values = (label, distro.state, distro.version, os_name or "—")

        row = ctk.CTkFrame(self.list_frame, fg_color="transparent")
        row.pack(fill="x", pady=2)
        row.bind("<Button-1>", lambda _e, n=distro.name: self._select(n))

        for text, width in zip(values, COLUMN_WIDTHS):
            widget = ctk.CTkLabel(row, text=text, width=width, anchor="w")
            widget.pack(side="left", padx=4)
            widget.bind("<Button-1>", lambda _e, n=distro.name: self._select(n))

        self._row_frames[distro.name] = row

    def _select(self, name: str) -> None:
        if self._selected_name is not None and self._selected_name in self._row_frames:
            self._row_frames[self._selected_name].configure(fg_color="transparent")
        self._selected_name = name
        self._row_frames[name].configure(fg_color=SELECTED_COLOR)

    def _selected_distro(self) -> str | None:
        if self._selected_name is None:
            messagebox.showinfo(WINDOW_TITLE, "Selecione uma distro na lista.")
            return None
        return self._selected_name

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
