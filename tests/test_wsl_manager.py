"""Testes da lógica pura de wsl_manager.py (sem subprocess/winreg).

Roda em qualquer SO: só exercita _parse_distro_list e
_decode_console_table, que não dependem de wsl.exe nem do registro do
Windows.
"""
from __future__ import annotations

import unittest

from wsl_manager import Distro, _decode_console_table, _parse_distro_list


class ParseDistroListTests(unittest.TestCase):
    def test_marca_distro_padrao(self) -> None:
        output = "NAME      STATE     VERSION\n" "* Ubuntu   Running   2\n"
        distros = _parse_distro_list(output)
        self.assertEqual(distros, [Distro(name="Ubuntu", state="Running", version="2", is_default=True)])

    def test_distro_nao_padrao(self) -> None:
        output = "NAME      STATE     VERSION\n" "  Debian  Stopped   1\n"
        distros = _parse_distro_list(output)
        self.assertEqual(distros, [Distro(name="Debian", state="Stopped", version="1", is_default=False)])

    def test_varias_distros(self) -> None:
        output = (
            "NAME       STATE     VERSION\n"
            "* Ubuntu   Running   2\n"
            "  Debian   Stopped   1\n"
            "  Alpine   Stopped   2\n"
        )
        distros = _parse_distro_list(output)
        self.assertEqual(len(distros), 3)
        self.assertEqual([d.name for d in distros], ["Ubuntu", "Debian", "Alpine"])
        self.assertTrue(distros[0].is_default)
        self.assertFalse(distros[1].is_default)

    def test_linha_curta_e_descartada(self) -> None:
        output = "NAME      STATE     VERSION\n" "  incompleta\n" "  Ubuntu  Running   2\n"
        distros = _parse_distro_list(output)
        self.assertEqual(len(distros), 1)
        self.assertEqual(distros[0].name, "Ubuntu")

    def test_saida_so_com_cabecalho(self) -> None:
        self.assertEqual(_parse_distro_list("NAME      STATE     VERSION\n"), [])

    def test_saida_vazia(self) -> None:
        self.assertEqual(_parse_distro_list(""), [])


class DecodeConsoleTableTests(unittest.TestCase):
    def test_utf16_com_bom(self) -> None:
        raw = "NAME\tSTATE\n".encode("utf-16")  # inclui BOM
        self.assertEqual(_decode_console_table(raw), "NAME\tSTATE\n")

    def test_utf16le_sem_bom(self) -> None:
        raw = "NAME\tSTATE\n".encode("utf-16-le")  # sem BOM
        self.assertEqual(_decode_console_table(raw), "NAME\tSTATE\n")

    def test_fallback_utf8(self) -> None:
        # Tamanho ímpar de bytes força UnicodeDecodeError ao tentar utf-16
        # (que exige número par de bytes) — só assim o fallback é exercitado
        # de fato. Um número par de bytes UTF-8 raramente falha o decode
        # utf-16 (produz só texto ilegível em vez de levantar exceção), que é
        # justamente a causa raiz do bug histórico da coluna S.O. deste projeto.
        raw = "erro!".encode("utf-8")
        self.assertEqual(len(raw) % 2, 1)
        self.assertEqual(_decode_console_table(raw), "erro!")


if __name__ == "__main__":
    unittest.main()
