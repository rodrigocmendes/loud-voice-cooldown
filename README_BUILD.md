# Gerar Executável (.exe) com PyInstaller

Instruções para gerar um arquivo `.exe` standalone que roda no Windows sem precisar de Python instalado.

## Pré-requisitos

1. Python 3.11+ instalado no Windows
2. Projeto com dependências instaladas (ver [README.md](README.md))

## Passos

### 1. Instalar PyInstaller

```bash
pip install pyinstaller
```

### 2. Gerar o .exe

No diretório raiz do projeto, execute:

```bash
pyinstaller --name "LoudVoiceCooldown" ^
    --onefile ^
    --windowed ^
    --add-data "src;src" ^
    --hidden-import sounddevice ^
    --hidden-import numpy ^
    --hidden-import PySide6.QtWidgets ^
    --hidden-import PySide6.QtCore ^
    --hidden-import PySide6.QtGui ^
    main.py
```

**Explicação dos parâmetros:**
- `--name`: Nome do executável gerado
- `--onefile`: Gera um único arquivo .exe
- `--windowed`: Não mostra console (aplicação GUI)
- `--add-data`: Inclui o diretório `src` no pacote
- `--hidden-import`: Garante que módulos são incluídos

### 3. Localizar o executável

Após a compilação, o arquivo estará em:

```
dist/LoudVoiceCooldown.exe
```

### 4. Distribuir

Copie o arquivo `LoudVoiceCooldown.exe` para qualquer computador com Windows 10/11. Não precisa de instalação adicional.

## Alternativa: Diretório (mais rápido para compilar)

Se preferir um diretório em vez de arquivo único:

```bash
pyinstaller --name "LoudVoiceCooldown" ^
    --windowed ^
    --add-data "src;src" ^
    --hidden-import sounddevice ^
    --hidden-import numpy ^
    main.py
```

O resultado estará em `dist/LoudVoiceCooldown/` com o .exe e DLLs necessárias.

## Solução de Problemas

### Erro: "No module named sounddevice"
Certifique-se de que `sounddevice` está instalado no mesmo ambiente Python usado pelo PyInstaller:
```bash
pip install sounddevice
```

### Erro: "Failed to execute script"
Execute sem `--windowed` para ver erros no console:
```bash
pyinstaller --name "LoudVoiceCooldown" --onefile --add-data "src;src" main.py
```

### Tamanho do executável muito grande
PySide6 inclui muitas DLLs. Para reduzir, use `--exclude-module` para módulos não utilizados:
```bash
pyinstaller --name "LoudVoiceCooldown" ^
    --onefile --windowed ^
    --add-data "src;src" ^
    --exclude-module PySide6.QtWebEngine ^
    --exclude-module PySide6.Qt3D ^
    --exclude-module PySide6.QtMultimedia ^
    main.py
```

### Antivírus bloqueando o .exe
Alguns antivírus marcam executáveis do PyInstaller como suspeitos. Adicione uma exceção ou assine o executável com um certificado digital.

## Criar atalho com inicialização automática

Para iniciar automaticamente com o Windows:

1. Copie `LoudVoiceCooldown.exe` para uma pasta permanente (ex: `C:\Programas\LoudVoiceCooldown\`)
2. Crie um atalho do .exe
3. Pressione `Win+R`, digite `shell:startup` e pressione Enter
4. Cole o atalho na pasta Startup que abrir

O aplicativo iniciará automaticamente com o Windows e ficará na bandeja do sistema.
