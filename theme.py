"""Tokens de design do wslView: espaçamento, dimensões, cores e fontes.

Não substitui o tema de fábrica do CustomTkinter (`set_default_color_theme("blue")`,
ver gui.py) — apenas nomeia os valores que hoje escapam dele: destrutivo,
seleção de linha, borda/texto usados nos botões "outline" e o divisor de grupos.
"""
from __future__ import annotations

import tkinter.font as tkfont

import customtkinter as ctk

SPACING = {
    "xs": 4,
    "sm": 8,
    "md": 12,
    "lg": 16,
    "xl": 24,
    "xxl": 32,
}

DIMENSIONS = {
    "control_height": 28,
    "divider_width": 1,
    "divider_height": 20,
    "corner_radius": 6,
}

COLORS = {
    "danger": "#B3261E",
    "danger_hover": "#8C1D17",
    "selected": ("gray80", "gray25"),
    "border": ("#979DA2", "#565B5E"),
    "on_surface": ("gray10", "#DCE4EE"),
    "surface_alt": ("gray86", "gray17"),
}

_BODY_FAMILY_CANDIDATES = ("Segoe UI Variable", "Segoe UI", "Tahoma")


def _resolve_family(candidates: tuple[str, ...]) -> str:
    available = set(tkfont.families())
    for name in candidates:
        if name in available:
            return name
    return "TkDefaultFont"


def header_font() -> ctk.CTkFont:
    """Fonte do cabeçalho da tabela de distros. Chamar só após criar o CTk root."""
    return ctk.CTkFont(family=_resolve_family(_BODY_FAMILY_CANDIDATES), size=13, weight="bold")
