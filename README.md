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
pyinstaller --onedir --windowed --name wslView main.py
```

O executável e seus arquivos de suporte são gerados em `dist\wslView\`
(use `--onedir`, não `--onefile`: inicia mais rápido, pois não precisa
se auto-extrair para uma pasta temporária a cada execução, e reduz o
risco de falso-positivo em antivírus). Para distribuir, compacte a pasta
`dist\wslView\` inteira em um `.zip`.

## Changelog

Veja as [Releases do GitHub](https://github.com/thaus03/wslView/releases) para o changelog detalhado de cada versão.
