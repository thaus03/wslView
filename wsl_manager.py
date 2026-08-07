"""Funções de baixo nível para interagir com o WSL via wsl.exe."""
from __future__ import annotations

import subprocess
from dataclasses import dataclass
from pathlib import Path

CREATE_NO_WINDOW = 0x08000000
WSL_EXE = "wsl.exe"
LXSS_REGISTRY_PATH = r"Software\Microsoft\Windows\CurrentVersion\Lxss"


@dataclass
class Distro:
    name: str
    state: str
    version: str
    is_default: bool


class WslError(RuntimeError):
    """Classe base para erros ao interagir com o wsl.exe."""


class WslNotFoundError(WslError):
    """Levantado quando wsl.exe não está disponível no sistema."""


class WslCommandError(WslError):
    """Levantado quando wsl.exe roda mas retorna um erro (returncode != 0)."""

    def __init__(self, message: str, returncode: int, stderr: str) -> None:
        super().__init__(message)
        self.returncode = returncode
        self.stderr = stderr


class WslTimeoutError(WslError):
    """Levantado quando wsl.exe não responde dentro do tempo limite."""


def _run_wsl(args: list[str], timeout: float | None = 15) -> subprocess.CompletedProcess:
    try:
        return subprocess.run(
            [WSL_EXE, *args],
            capture_output=True,
            creationflags=CREATE_NO_WINDOW,
            timeout=timeout,
        )
    except FileNotFoundError as exc:
        raise WslNotFoundError("wsl.exe não encontrado neste sistema") from exc
    except subprocess.TimeoutExpired as exc:
        raise WslTimeoutError(
            f"wsl.exe não respondeu a tempo (comando: {' '.join(args)})"
        ) from exc


def _decode_console_table(raw: bytes) -> str:
    """Decodifica texto tabular impresso pelo próprio wsl.exe (UTF-16LE nativo do Windows)."""
    for encoding in ("utf-16-le", "utf-8"):
        try:
            return raw.decode(encoding)
        except UnicodeDecodeError:
            continue
    return raw.decode("utf-8", errors="replace")


def _decode_linux_output(raw: bytes) -> str:
    """Decodifica a saída repassada por um programa Linux rodado via `wsl -e` (UTF-8)."""
    return raw.decode("utf-8", errors="replace")


def list_distros() -> list[Distro]:
    """Lista as distros WSL instaladas com nome, estado e versão."""
    result = _run_wsl(["--list", "--verbose"])
    if result.returncode != 0:
        stderr_text = _decode_console_table(result.stderr).strip()
        raise WslCommandError(
            stderr_text or "wsl.exe retornou um erro ao listar as distros.",
            result.returncode,
            stderr_text,
        )
    output = _decode_console_table(result.stdout)

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
    for line in _decode_linux_output(result.stdout).splitlines():
        if line.startswith("PRETTY_NAME="):
            return line.split("=", 1)[1].strip().strip('"')
    return None


def _find_vhdx_path(name: str) -> Path | None:
    """Localiza o arquivo .vhdx de uma distro lendo o registro do Windows.

    Percorre as subchaves de HKCU\\...\\Lxss (uma por distro registrada,
    indexada por GUID) até achar a que tem `DistributionName` igual a
    `name`, lê o valor `BasePath` dela e busca o primeiro `*.vhdx` na
    pasta. Retorna None em qualquer etapa que falhe: chave/valor ausente,
    permissão negada, distro não encontrada, ou nenhum .vhdx na pasta.
    """
    import winreg  # import local: mantém o módulo importável fora do Windows

    try:
        lxss_key_cm = winreg.OpenKey(winreg.HKEY_CURRENT_USER, LXSS_REGISTRY_PATH)
    except OSError:
        return None

    with lxss_key_cm as lxss_key:
        index = 0
        while True:
            try:
                subkey_name = winreg.EnumKey(lxss_key, index)
            except OSError:
                return None  # fim da enumeração sem achar a distro
            index += 1
            try:
                with winreg.OpenKey(lxss_key, subkey_name) as subkey:
                    distro_name, _ = winreg.QueryValueEx(subkey, "DistributionName")
                    if distro_name != name:
                        continue
                    base_path, _ = winreg.QueryValueEx(subkey, "BasePath")
            except OSError:
                continue
            try:
                return next(Path(base_path).glob("*.vhdx"))
            except (StopIteration, OSError):
                return None


def get_vhdx_size_bytes(name: str) -> int | None:
    """Tamanho em bytes do arquivo .vhdx da distro informada.

    Só faz sentido para distros WSL2 (Distro.version == "2"); WSL1 usa
    uma árvore de diretórios real, sem VHDX algum — o chamador deve
    checar a versão antes de chamar esta função.
    """
    vhdx_path = _find_vhdx_path(name)
    if vhdx_path is None:
        return None
    try:
        return vhdx_path.stat().st_size
    except OSError:
        return None


def format_size(size_bytes: int) -> str:
    """Formata um tamanho em bytes como string legível (B/KB/MB/GB/TB)."""
    if size_bytes < 1024:
        return f"{size_bytes} B"
    size = float(size_bytes)
    for unit in ("KB", "MB", "GB", "TB"):
        size /= 1024
        if round(size, 1) < 1024 or unit == "TB":
            return f"{size:.1f} {unit}"
    return f"{size:.1f} TB"
