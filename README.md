# Loud Voice Cooldown

Aplicação para Windows 11 que monitora o volume do microfone em tempo real e ajuda uma criança a falar mais baixo enquanto joga online com fone de ouvido.

## Características

- **Privacidade total**: Não grava áudio, não transcreve fala, não envia nada para a internet
- **Monitoramento em tempo real**: Volume do microfone em escala 0-100 com análise a cada 100ms
- **Detecção de picos curtos**: Detecta voz alta mesmo em picos menores que 1 segundo
- **Acúmulo com janela móvel**: Acumula tempo acima do limite em janela configurável (padrão 10s)
- **Lembrete visual**: Toast não-bloqueante "Fale mais baixo" com cooldown de 3s entre lembretes
- **Bloqueio fullscreen**: Tela escura always-on-top com contador regressivo ao atingir 5s acumulados
- **Cooldown pós-bloqueio**: 45 segundos após bloqueio para evitar punição repetida
- **Painel de debug**: Mostra volume atual, máximo, limite, acumulado, gatilhos, estado da app
- **Botões de teste**: Testar lembrete, testar bloqueio, simular pico (+1s), resetar acumulador
- **Bandeja do sistema**: Roda minimizado sem atrapalhar
- **Configurações persistentes**: Salvas em JSON local
- **Logs técnicos**: Registro de eventos para troubleshooting

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

1. **Iniciar**: Clique em "Iniciar" para começar o monitoramento
2. **Ajustar limite**: Use o slider "Limite de volume para alerta" (escala 0-100)
3. **Testar lembrete**: Clique em "Testar lembrete" para ver o toast sem áudio
4. **Testar bloqueio**: Clique em "Testar bloqueio" para ver a tela de bloqueio sem áudio
5. **Simular pico**: Clique em "Simular pico (+1s)" para adicionar 1s ao acumulador
6. **Resetar**: Clique em "Resetar acumulador" para zerar contadores
7. **Minimizar**: Feche a janela para minimizar na bandeja do sistema

## Lógica de Detecção

A cada 100ms a aplicação lê o volume do microfone e compara com o limite:

```
Se volume_atual > limite_de_volume_para_alerta → registra como voz alta
```

O tempo acima do limite é acumulado numa janela móvel (padrão 10s, customizável). Quando o acumulado atinge 5s, o bloqueio visual é acionado. Picos curtos (< 1s) também geram lembrete visual imediato.

## Configurações

| Parâmetro | Padrão | Descrição |
|-----------|--------|-----------|
| Limite de volume para alerta | 40 | Escala 0-100 (0=qualquer som, 100=só muito alto) |
| Intervalo de análise | 100ms | Frequência de leitura do volume |
| Janela de acúmulo | 10s | Eventos mais antigos são descartados (customizável) |
| Tempo acumulado para bloqueio | 5s | Total acumulado que dispara bloqueio |
| Duração do lembrete | 1.5s | Tempo que o toast fica visível |
| Cooldown entre lembretes | 3s | Mínimo entre lembretes consecutivos |
| Duração do bloqueio | 8s | Tempo da tela escura fullscreen |
| Cooldown após bloqueio | 45s | Mínimo entre bloqueios consecutivos |

As configurações são salvas automaticamente em `~/.loud_voice_cooldown/settings.json`.

## Painel de Debug

Mostra em tempo real:
- Microfone selecionado e status
- Volume atual (0-100) e volume máximo recente
- Limite de volume para alerta
- Indicação se volume está acima ou abaixo do limite
- Tempo acumulado acima do limite dentro da janela móvel
- Janela de acúmulo e tempo necessário para bloqueio
- Quantidade de gatilhos detectados e último horário
- Estado da aplicação (Parado, Monitorando, Lembrete ativo, Bloqueio ativo, Cooldown, Pausado)

## Estrutura do Projeto

```
loud-voice-cooldown/
├── main.py                  # Ponto de entrada + logging init
├── requirements.txt         # Dependências Python
├── README.md                # Este arquivo
├── README_BUILD.md          # Instruções para gerar .exe
└── src/
    ├── __init__.py
    ├── logger.py            # Logging técnico com rotação
    ├── audio_monitor.py     # Captura de áudio (escala 0-100)
    ├── volume_detector.py   # Acumulador com janela móvel
    ├── alert_manager.py     # Lembretes e bloqueios
    ├── cooldown_manager.py  # Cooldown pós-bloqueio
    ├── settings_manager.py  # Configurações JSON
    ├── overlay_window.py    # Bloqueio fullscreen
    ├── reminder_window.py   # Toast não-bloqueante
    └── main_window.py       # Interface principal + debug
```

## Módulos

- **AudioMonitor**: Captura áudio via `sounddevice`, calcula RMS e converte para escala 0-100
- **VolumeDetector**: Timer a cada 100ms, acumula tempo acima do limite com janela móvel, dispara bloqueio
- **AlertManager**: Coordena lembretes (com cooldown 3s) e bloqueios (com cooldown 45s)
- **CooldownManager**: Impede bloqueios repetidos dentro do período de cooldown
- **SettingsManager**: Carrega/salva configurações em JSON local
- **OverlayWindow**: Janela fullscreen always-on-top com mensagem e contador regressivo
- **ReminderWindow**: Toast não-bloqueante "Fale mais baixo" posicionado no topo da tela
- **MainWindow**: Interface completa com controles, painel de debug, testes e bandeja

## Logs

Logs técnicos são gravados em `~/.loud_voice_cooldown/app.log` com rotação automática (2MB, 3 backups). Não contêm áudio nem conteúdo falado.

## Licença

MIT License - veja o arquivo [LICENSE](LICENSE) para detalhes.
