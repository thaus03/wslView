# wslView

Aplicativo desktop leve em Python para gerenciar distribuições WSL no Windows.

## Requisitos

- Windows 10/11 com WSL instalado
- Python 3.11+
- Nenhuma dependência externa (usa apenas a biblioteca padrão / tkinter)

## Instalação e execução

```bash
git clone https://github.com/thaus03/wslView.git
cd wslView
python main.py
```

## Funcionalidades

- Listar todas as distros WSL instaladas com status (Running/Stopped)
- Iniciar uma distro selecionada
- Parar uma distro selecionada
- Encerrar todas as distros de uma vez ("Shutdown All")
- Atualização de status via botão "Refresh" (sem polling automático)

## Gerando o executável (.exe)

O `.exe` precisa ser compilado no próprio Windows (o PyInstaller não faz
cross-compile a partir de Linux/WSL). Rode os comandos abaixo em um
PowerShell/CMD no Windows, dentro da pasta do projeto:

```powershell
py -3 -m venv .venv
.venv\Scripts\activate
pip install pyinstaller
pyinstaller --onefile --windowed --name wslView main.py
```

O executável é gerado em `dist\wslView.exe`.

## Changelog

Veja as [Releases do GitHub](https://github.com/thaus03/wslView/releases) para o changelog detalhado de cada versão.
