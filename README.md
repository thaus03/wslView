![Uploading image.png…]()


# wslView

Aplicativo desktop leve em Python para gerenciar distribuições WSL no Windows.

## Requisitos

- Windows 10/11 com WSL instalado
- Python 3.11+
- [CustomTkinter](https://github.com/TomSchimansky/CustomTkinter) para a
  interface (única dependência externa do projeto — desvio deliberado da
  ideia original de usar só a stdlib, em troca de um visual mais moderno)

## Instalação e execução

```bash
git clone https://github.com/thaus03/wslView.git
cd wslView
pip install -r requirements.txt
python main.py
```

## Funcionalidades

- Listar todas as distros WSL instaladas com status (Running/Stopped)
- Iniciar uma distro selecionada
- Parar uma distro selecionada
- Encerrar todas as distros de uma vez ("Shutdown All")
- Atualização de status via botão "Refresh" (sem polling automático)

## Gerando o executável (.exe)

Um `.exe` pronto é gerado automaticamente a cada push/PR pela CI — veja o
artifact `wslView-windows` na aba [Actions](https://github.com/thaus03/wslView/actions).
Para compilar localmente, o passo a passo está na
[Wiki](https://github.com/thaus03/wslView/wiki/Gerando-o-executavel).

## Changelog

Veja as [Releases do GitHub](https://github.com/thaus03/wslView/releases) para o changelog detalhado de cada versão.
