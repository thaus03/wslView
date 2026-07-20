"""Funções de baixo nível para interagir com o WSL via wsl.exe."""
from __future__ import annotations

import subprocess
from dataclasses import dataclass

CREATE_NO_WINDOW = 0x08000000
WSL_EXE = "wsl.exe"


@dataclass
class Distro:
    name: str
    state: str
    version: str
    is_default: bool


class WslNotFoundError(RuntimeError):
    """Levantado quando wsl.exe não está disponível no sistema."""


def _run_wsl(args: list[str]) -> subprocess.CompletedProcess:
    try:
        return subprocess.run(
            [WSL_EXE, *args],
            capture_output=True,
            creationflags=CREATE_NO_WINDOW,
            timeout=15,
        )
    except FileNotFoundError as exc:
        raise WslNotFoundError("wsl.exe não encontrado neste sistema") from exc


def _decode(raw: bytes) -> str:
    for encoding in ("utf-16-le", "utf-8"):
        try:
            return raw.decode(encoding)
        except UnicodeDecodeError:
            continue
    return raw.decode("utf-8", errors="replace")


def list_distros() -> list[Distro]:
    """Lista as distros WSL instaladas com nome, estado e versão."""
    result = _run_wsl(["--list", "--verbose"])
    output = _decode(result.stdout)

    distros: list[Distro] = []
    lines = [line for line in output.splitlines() if line.strip()]
    for line in lines[1:]:
        is_default = line.strip().startswith("*")
        cleaned = line.replace("*", "", 1).strip()
        parts = cleaned.split()
        if len(parts) < 3:
            continue
        name, state, version = parts[0], parts[1], parts[2]
        distros.append(Distro(name=name, state=state, version=version, is_default=is_default))
    return distros


def start_distro(name: str) -> None:
    """Inicia (ou 'acorda') a distro informada."""
    _run_wsl(["-d", name, "-e", "true"])


def stop_distro(name: str) -> None:
    """Termina a distro informada."""
    _run_wsl(["--terminate", name])


def shutdown_all() -> None:
    """Encerra todas as distros WSL em execução."""
    _run_wsl(["--shutdown"])


def get_os_pretty_name(name: str) -> str | None:
    """Lê o PRETTY_NAME de /etc/os-release de uma distro em execução.

    Só deve ser chamada para distros já "Running": rodar em uma distro
    parada a iniciaria como efeito colateral, o que contraria o refresh
    manual e sem custo extra pedido pelo projeto.
    """
    result = _run_wsl(["-d", name, "-e", "cat", "/etc/os-release"])
    if result.returncode != 0:
        return None
    for line in _decode(result.stdout).splitlines():
        if line.startswith("PRETTY_NAME="):
            return line.split("=", 1)[1].strip().strip('"')
    return None
