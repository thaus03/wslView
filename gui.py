"""Interface gráfica (CustomTkinter) do wslView.

CustomTkinter não tem um widget de tabela equivalente ao ttk.Treeview,
então a lista de distros é montada como linhas dentro de um
CTkScrollableFrame. Diálogos (messagebox) continuam do tkinter puro,
pois o CustomTkinter não oferece substituto tematizado para eles.
"""
from __future__ import annotations

import sys
import threading
import tkinter as tk
from collections.abc import Callable
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
        self._menus: dict[str, tk.Menu] = {}
        self._busy = False

        self._build_menubar()
        self._build_widgets()
        self.refresh()

    def _build_menubar(self) -> None:
        """Menu nativo do Windows (tkinter.Menu — o CustomTkinter não tem
        substituto temático, mesma limitação já aceita pelos diálogos do
        tkinter.messagebox usados no resto do app).

        Guarda os submenus em self._menus pra próximas funcionalidades só
        precisarem de um add_command/add_separator, sem redecidir estrutura.
        O menu "Arquivo" só é criado quando a primeira ação que não depende
        de seleção (Importar/Instalar) existir — um cascade vazio é pior
        experiência que não ter o menu ainda.
        """
        menubar = tk.Menu(self)

        distro_menu = tk.Menu(menubar, tearoff=False)
        distro_menu.add_command(label="Atualizar", command=self.refresh)
        distro_menu.add_command(label="Iniciar", command=self._on_start)
        distro_menu.add_command(label="Parar", command=self._on_stop)
        distro_menu.add_separator()
        distro_menu.add_command(label="Encerrar todas...", command=self._on_shutdown_all)
        menubar.add_cascade(label="Distro", menu=distro_menu)

        ajuda_menu = tk.Menu(menubar, tearoff=False)
        menubar.add_cascade(label="Ajuda", menu=ajuda_menu)

        self.config(menu=menubar)
        self._menus = {"distro": distro_menu, "ajuda": ajuda_menu}

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

        self.btn_refresh = ctk.CTkButton(
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
        )
        self.btn_refresh.pack(side="left", padx=(0, SPACING["xs"]))

        self.btn_start = ctk.CTkButton(
            primary_group,
            text="Start",
            command=self._on_start,
            width=90,
            height=DIMENSIONS["control_height"],
            corner_radius=DIMENSIONS["corner_radius"],
        )
        self.btn_start.pack(side="left", padx=(0, SPACING["xs"]))

        self.btn_stop = ctk.CTkButton(
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
        )
        self.btn_stop.pack(side="left")

        danger_group = ctk.CTkFrame(button_frame, fg_color="transparent")
        danger_group.pack(side="right")

        ctk.CTkFrame(
            danger_group,
            width=DIMENSIONS["divider_width"],
            height=DIMENSIONS["divider_height"],
            fg_color=COLORS["border"],
        ).pack(side="left", padx=SPACING["xl"])

        self.btn_shutdown_all = ctk.CTkButton(
            danger_group,
            text="Shutdown All",
            command=self._on_shutdown_all,
            width=120,
            height=DIMENSIONS["control_height"],
            corner_radius=DIMENSIONS["corner_radius"],
            fg_color=COLORS["danger"],
            hover_color=COLORS["danger_hover"],
        )
        self.btn_shutdown_all.pack(side="left")

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

    def _run_async(
        self,
        work: Callable[[], object],
        on_done: Callable[[object, Exception | None], None],
        busy_message: str = "Aguarde...",
    ) -> None:
        """Roda `work` numa thread separada e chama `on_done(valor, erro)` de
        volta na thread principal (via `self.after`), a única thread em que
        widgets Tk podem ser tocados com segurança.
        """
        self.status_var.set(busy_message)
        self._set_busy(True)
        box: dict[str, object] = {}

        def _worker() -> None:
            try:
                box["value"] = work()
            except Exception as exc:  # noqa: BLE001 - repassado como valor, não relançado
                box["error"] = exc
            self.after(0, _finish)

        def _finish() -> None:
            self._set_busy(False)
            on_done(box.get("value"), box.get("error"))

        threading.Thread(target=_worker, daemon=True).start()

    def _set_busy(self, busy: bool) -> None:
        self._busy = busy
        state = "disabled" if busy else "normal"
        for button in (self.btn_refresh, self.btn_start, self.btn_stop, self.btn_shutdown_all):
            button.configure(state=state)

    def _after_command(self, error: Exception | None, success_message: str | None = None) -> None:
        """Callback compartilhado por ações que só precisam de erro/sucesso
        genéricos (start/stop/shutdown all, e as próximas ações do backlog)."""
        if error is not None:
            message = str(error) if isinstance(error, WslError) else "Erro inesperado."
            messagebox.showerror(WINDOW_TITLE, message)
            return
        if success_message:
            messagebox.showinfo(WINDOW_TITLE, success_message)
        self.refresh()

    def refresh(self) -> None:
        if self._busy:
            return
        self._run_async(self._collect_distro_rows, self._on_refresh_done, busy_message="Atualizando...")

    def _collect_distro_rows(self) -> list[tuple[Distro, str | None, int | None]]:
        """Busca os dados de cada distro (chamadas a wsl.exe) — roda na
        thread de fundo, nunca toca widgets."""
        distros = list_distros()
        rows: list[tuple[Distro, str | None, int | None]] = []
        for distro in distros:
            os_name = get_os_pretty_name(distro.name) if distro.state == "Running" else None
            vhdx_bytes = get_vhdx_size_bytes(distro.name) if distro.version == "2" else None
            rows.append((distro, os_name, vhdx_bytes))
        return rows

    def _on_refresh_done(self, rows: object, error: Exception | None) -> None:
        for frame in self._row_frames.values():
            frame.destroy()
        self._row_frames.clear()
        self._selected_name = None

        if error is not None:
            if isinstance(error, WslNotFoundError):
                self.status_var.set("wsl.exe não encontrado. O WSL está instalado?")
            elif isinstance(error, WslError):
                self.status_var.set(str(error))
            else:
                self.status_var.set("Erro inesperado ao atualizar a lista.")
            return

        assert isinstance(rows, list)
        if not rows:
            self.status_var.set("Nenhuma distro WSL instalada.")
            return

        for distro, os_name, vhdx_bytes in rows:
            self._add_row(distro, os_name, vhdx_bytes)

        self.status_var.set(f"{len(rows)} distro(s) encontrada(s).")

    def _add_row(self, distro: Distro, os_name: str | None, vhdx_bytes: int | None) -> None:
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
        if self._busy:
            return
        name = self._selected_distro()
        if name is None:
            return
        self._run_async(lambda: start_distro(name), lambda _r, err: self._after_command(err))

    def _on_stop(self) -> None:
        if self._busy:
            return
        name = self._selected_distro()
        if name is None:
            return
        self._run_async(lambda: stop_distro(name), lambda _r, err: self._after_command(err))

    def _on_shutdown_all(self) -> None:
        if self._busy:
            return
        if not messagebox.askyesno(
            WINDOW_TITLE,
            "Isso vai encerrar TODAS as distros WSL em execução. Continuar?",
            icon="warning",
        ):
            return
        self._run_async(shutdown_all, lambda _r, err: self._after_command(err))
