# Loud Voice Cooldown

Aplicação para Windows 11 que monitora o volume do microfone em tempo real e ajuda uma criança a falar mais baixo enquanto joga online com fone de ouvido.

## Características

- **Privacidade total**: Não grava áudio, não transcreve fala, não envia nada para a internet
- **Monitoramento em tempo real**: Captura do microfone com cálculo de volume RMS
- **Detecção inteligente**: Evita falsos positivos com janela deslizante (2s acumulados em 5s)
- **Alertas progressivos**: 3 níveis (aviso, overlay, tela escura)
- **Cooldown**: Evita punições repetidas (padrão 45s)
- **Overlay fullscreen**: Bloqueia visualmente a tela com mensagem calma e contador regressivo
- **Calibração**: Ajusta o limite ao volume normal da criança
- **Modo de teste**: Simula voz alta para validar configuração
- **Bandeja do sistema**: Roda minimizado sem atrapalhar
- **Configurações persistentes**: Salvas em JSON local

## Requisitos

- Windows 10/11
- Python 3.11+
- Microfone funcional

## Instalação

### 1. Instalar Python 3.11+

Baixe e instale de [python.org](https://www.python.org/downloads/). Marque a opção "Add Python to PATH" durante a instalação.

### 2. Clonar ou baixar o projeto

```bash
git clone https://github.com/rodrigocmendes/loud-voice-cooldown.git
cd loud-voice-cooldown
```

### 3. Criar ambiente virtual (recomendado)

```bash
python -m venv venv
venv\Scripts\activate
```

### 4. Instalar dependências

```bash
pip install -r requirements.txt
```

### 5. Executar

```bash
python main.py
```

## Uso

1. **Iniciar**: Clique em "▶ Iniciar" para começar o monitoramento
2. **Calibrar**: Com o monitoramento ativo, clique em "🎯 Calibrar" e peça à criança para falar normalmente por 5 segundos
3. **Ajustar sensibilidade**: Use o slider para ajustar manualmente o limite
4. **Testar**: Clique em "🧪 Testar" para simular um alerta
5. **Minimizar**: Feche a janela para minimizar na bandeja do sistema

## Configurações

| Parâmetro | Padrão | Descrição |
|-----------|--------|-----------|
| Sensibilidade | 15% | Limite de volume para detectar voz alta |
| Bloqueio | 8s | Duração do overlay na tela |
| Cooldown | 45s | Tempo mínimo entre bloqueios |
| Tempo sustentado | 2s | Tempo acumulado acima do limite para disparar |
| Janela detecção | 5s | Janela de tempo para acumular |
| Alertas progressivos | Sim | Escala gradual dos alertas |

As configurações são salvas automaticamente em `~/.loud_voice_cooldown/settings.json`.

## Estrutura do Projeto

```
loud-voice-cooldown/
├── main.py                  # Ponto de entrada
├── requirements.txt         # Dependências Python
├── README.md                # Este arquivo
├── README_BUILD.md          # Instruções para gerar .exe
└── src/
    ├── __init__.py
    ├── audio_monitor.py     # Captura de áudio do microfone
    ├── volume_detector.py   # Detecção de voz alta sustentada
    ├── alert_manager.py     # Níveis progressivos de alerta
    ├── cooldown_manager.py  # Controle de cooldown entre alertas
    ├── settings_manager.py  # Persistência de configurações JSON
    ├── overlay_window.py    # Overlay/bloqueio fullscreen
    └── main_window.py       # Interface principal e bandeja
```

## Módulos

- **AudioMonitor**: Captura áudio via `sounddevice`, calcula RMS e emite sinais Qt
- **VolumeDetector**: Analisa volume com janela deslizante e detecta voz alta sustentada
- **AlertManager**: Coordena níveis progressivos de alerta (aviso → overlay → bloqueio)
- **CooldownManager**: Impede alertas repetidos dentro do período de cooldown
- **SettingsManager**: Carrega/salva configurações em JSON local
- **OverlayWindow**: Janela fullscreen always-on-top com contador regressivo
- **MainWindow**: Interface principal com controles e bandeja do sistema

## Licença

MIT License - veja o arquivo [LICENSE](LICENSE) para detalhes.
