"""Interface gráfica (CustomTkinter) do wslView.

CustomTkinter não tem um widget de tabela equivalente ao ttk.Treeview,
então a lista de distros é montada como linhas dentro de um
CTkScrollableFrame. Diálogos (messagebox) continuam do tkinter puro,
pois o CustomTkinter não oferece substituto tematizado para eles.
"""
from __future__ import annotations

import sys
import tkinter as tk
from dataclasses import dataclass
from pathlib import Path
from tkinter import messagebox

import customtkinter as ctk

import theme
from theme import COLORS, DIMENSIONS, SPACING
from wsl_manager import (
    Distro,
    WslError,
    WslNotFoundError,
    format_size,
    get_os_pretty_name,
    get_vhdx_size_bytes,
    list_distros,
    shutdown_all,
    start_distro,
    stop_distro,
)

WINDOW_TITLE = "wslView"
WINDOW_SIZE = "760x360"
SCROLLBAR_RESERVE_FALLBACK = 16
ICON_PATH = Path(getattr(sys, "_MEIPASS", Path(__file__).parent)) / "assets" / "icon.ico"


@dataclass(frozen=True)
class ColumnSpec:
    label: str
    minsize: int
    weight: int


COLUMN_SPECS: tuple[ColumnSpec, ...] = (
    ColumnSpec("Distro", 200, 3),
    ColumnSpec("Status", 100, 0),
    ColumnSpec("WSL", 50, 0),
    ColumnSpec("S.O.", 190, 2),
    ColumnSpec("VHDX", 90, 0),
)

ctk.set_appearance_mode("System")
ctk.set_default_color_theme("blue")


def _configure_columns(container: ctk.CTkBaseClass) -> None:
    for index, spec in enumerate(COLUMN_SPECS):
        container.grid_columnconfigure(index, weight=spec.weight, minsize=spec.minsize)


class WslViewApp(ctk.CTk):
    """Janela principal do gerenciador de distros WSL."""

    def __init__(self) -> None:
        super().__init__()
        self.title(WINDOW_TITLE)
        self.geometry(WINDOW_SIZE)
        self.minsize(680, 320)
        self.iconbitmap(str(ICON_PATH))

        self._selected_name: str | None = None
        self._row_frames: dict[str, ctk.CTkFrame] = {}

        self._build_widgets()
        self.refresh()

    def _build_widgets(self) -> None:
        self.header = ctk.CTkFrame(self, fg_color="transparent")
        self.header.pack(fill="x", padx=SPACING["md"], pady=(SPACING["md"], 0))
        _configure_columns(self.header)
        for index, spec in enumerate(COLUMN_SPECS):
            ctk.CTkLabel(
                self.header, text=spec.label, anchor="w", font=theme.header_font()
            ).grid(row=0, column=index, sticky="ew", padx=SPACING["xs"])
        self.header.grid_columnconfigure(
            len(COLUMN_SPECS), weight=0, minsize=SCROLLBAR_RESERVE_FALLBACK
        )

        self.list_frame = ctk.CTkScrollableFrame(self)
        self.list_frame.pack(fill="both", expand=True, padx=SPACING["md"], pady=SPACING["md"])

        self._build_button_bar()

        self.status_var = tk.StringVar(value="")
        ctk.CTkLabel(self, textvariable=self.status_var, anchor="w").pack(
            fill="x", padx=SPACING["md"], pady=(0, SPACING["xs"])
        )

        self.after_idle(self._sync_header_spacer)

    def _build_button_bar(self) -> None:
        button_frame = ctk.CTkFrame(self, fg_color="transparent")
        button_frame.pack(fill="x", padx=SPACING["md"], pady=(0, SPACING["md"]))

        primary_group = ctk.CTkFrame(button_frame, fg_color="transparent")
        primary_group.pack(side="left")

        ctk.CTkButton(
            primary_group,
            text="Refresh",
            command=self.refresh,
            width=90,
            height=DIMENSIONS["control_height"],
            corner_radius=DIMENSIONS["corner_radius"],
            fg_color="transparent",
            border_width=1,
            border_color=COLORS["border"],
            text_color=COLORS["on_surface"],
            hover_color=COLORS["surface_alt"],
        ).pack(side="left", padx=(0, SPACING["xs"]))

        ctk.CTkButton(
            primary_group,
            text="Start",
            command=self._on_start,
            width=90,
            height=DIMENSIONS["control_height"],
            corner_radius=DIMENSIONS["corner_radius"],
        ).pack(side="left", padx=(0, SPACING["xs"]))

        ctk.CTkButton(
            primary_group,
            text="Stop",
            command=self._on_stop,
            width=90,
            height=DIMENSIONS["control_height"],
            corner_radius=DIMENSIONS["corner_radius"],
            fg_color="transparent",
            border_width=1,
            border_color=COLORS["border"],
            text_color=COLORS["on_surface"],
            hover_color=COLORS["surface_alt"],
        ).pack(side="left")

        danger_group = ctk.CTkFrame(button_frame, fg_color="transparent")
        danger_group.pack(side="right")

        ctk.CTkFrame(
            danger_group,
            width=DIMENSIONS["divider_width"],
            height=DIMENSIONS["divider_height"],
            fg_color=COLORS["border"],
        ).pack(side="left", padx=SPACING["xl"])

        ctk.CTkButton(
            danger_group,
            text="Shutdown All",
            command=self._on_shutdown_all,
            width=120,
            height=DIMENSIONS["control_height"],
            corner_radius=DIMENSIONS["corner_radius"],
            fg_color=COLORS["danger"],
            hover_color=COLORS["danger_hover"],
        ).pack(side="left")

    def _sync_header_spacer(self) -> None:
        """Ajusta a coluna-espaçadora do cabeçalho para o tamanho real da
        scrollbar do CTkScrollableFrame, medida após o primeiro layout."""
        width = SCROLLBAR_RESERVE_FALLBACK
        try:
            measured = self.list_frame._scrollbar.winfo_width()
            if measured > 1:
                width = measured
        except AttributeError:
            pass
        self.header.grid_columnconfigure(len(COLUMN_SPECS), minsize=width)

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
        except WslError as exc:
            self.status_var.set(str(exc))
            return

        if not distros:
            self.status_var.set("Nenhuma distro WSL instalada.")
            return

        for distro in distros:
            self._add_row(distro)

        self.status_var.set(f"{len(distros)} distro(s) encontrada(s).")

    def _add_row(self, distro: Distro) -> None:
        os_name = get_os_pretty_name(distro.name) if distro.state == "Running" else None
        vhdx_bytes = get_vhdx_size_bytes(distro.name) if distro.version == "2" else None
        vhdx_size = format_size(vhdx_bytes) if vhdx_bytes is not None else "—"
        label = f"{distro.name} *" if distro.is_default else distro.name
        values = (label, distro.state, distro.version, os_name or "—", vhdx_size)

        row = ctk.CTkFrame(self.list_frame, fg_color="transparent")
        row.pack(fill="x", pady=SPACING["xs"])
        _configure_columns(row)
        row.bind("<Button-1>", lambda _e, n=distro.name: self._select(n))

        for index, text in enumerate(values):
            widget = ctk.CTkLabel(row, text=text, anchor="w")
            widget.grid(row=0, column=index, sticky="ew", padx=SPACING["xs"])
            widget.bind("<Button-1>", lambda _e, n=distro.name: self._select(n))

        self._row_frames[distro.name] = row

    def _select(self, name: str) -> None:
        if self._selected_name is not None and self._selected_name in self._row_frames:
            self._row_frames[self._selected_name].configure(fg_color="transparent")
        self._selected_name = name
        self._row_frames[name].configure(fg_color=COLORS["selected"])

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
        except WslError as exc:
            messagebox.showerror(WINDOW_TITLE, str(exc))
            return
        self.refresh()

    def _on_stop(self) -> None:
        name = self._selected_distro()
        if name is None:
            return
        try:
            stop_distro(name)
        except WslError as exc:
            messagebox.showerror(WINDOW_TITLE, str(exc))
            return
        self.refresh()

    def _on_shutdown_all(self) -> None:
        if not messagebox.askyesno(
            WINDOW_TITLE,
            "Isso vai encerrar TODAS as distros WSL em execução. Continuar?",
            icon="warning",
        ):
            return
        try:
            shutdown_all()
        except WslError as exc:
            messagebox.showerror(WINDOW_TITLE, str(exc))
            return
        self.refresh()
