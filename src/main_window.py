"""
MainWindow - Interface principal do aplicativo.

Controles: iniciar/parar monitoramento, calibrar, ajustar sensibilidade,
tempo de bloqueio, cooldown, seleção de microfone, modo de teste.
Minimiza para bandeja do sistema.
"""

from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QSlider, QComboBox, QGroupBox,
    QProgressBar, QSpinBox, QDoubleSpinBox, QCheckBox,
    QSystemTrayIcon, QMenu, QMessageBox, QApplication,
)
from PySide6.QtCore import Qt, QTimer, Slot
from PySide6.QtGui import QAction, QCloseEvent

from .audio_monitor import AudioMonitor
from .volume_detector import VolumeDetector
from .alert_manager import AlertManager, AlertLevel
from .cooldown_manager import CooldownManager
from .settings_manager import SettingsManager
from .overlay_window import OverlayWindow


class MainWindow(QMainWindow):
    """Janela principal do Loud Voice Cooldown."""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Loud Voice Cooldown")
        self.setMinimumSize(500, 600)

        # Gerenciadores
        self._settings_mgr = SettingsManager()
        self._settings = self._settings_mgr.settings

        self._audio_monitor = AudioMonitor(
            device=self._settings.microphone_device,
            sample_rate=self._settings.sample_rate,
            block_size=self._settings.block_size,
        )
        self._volume_detector = VolumeDetector(
            threshold=self._settings.volume_threshold,
            sustained_duration=self._settings.sustained_duration,
            detection_window=self._settings.detection_window,
        )
        self._alert_manager = AlertManager(
            progressive=self._settings.progressive_alerts,
            block_duration=self._settings.block_duration,
        )
        self._cooldown_manager = CooldownManager(
            cooldown_duration=self._settings.cooldown_duration,
        )
        self._overlay = OverlayWindow()

        # Estado
        self._monitoring = False
        self._calibrating = False
        self._calibration_samples: list[float] = []
        self._current_volume = 0.0

        # Timer para atualizar UI e cooldown
        self._ui_timer = QTimer(self)
        self._ui_timer.setInterval(100)
        self._ui_timer.timeout.connect(self._update_ui_status)

        # Conecta sinais
        self._connect_signals()

        # Cria interface
        self._setup_ui()
        self._setup_tray()

        # Carrega valores iniciais na UI
        self._load_settings_to_ui()

        self._ui_timer.start()

    def _connect_signals(self) -> None:
        """Conecta sinais entre os componentes."""
        self._audio_monitor.volume_updated.connect(self._on_volume_updated)
        self._audio_monitor.volume_updated.connect(self._volume_detector.process_volume)
        self._audio_monitor.error_occurred.connect(self._on_audio_error)
        self._volume_detector.loud_voice_detected.connect(self._on_loud_voice)
        self._volume_detector.accumulation_updated.connect(self._on_accumulation_updated)
        self._overlay.overlay_closed.connect(self._on_overlay_closed)
        self._alert_manager.alert_triggered.connect(self._on_alert_triggered)
        self._alert_manager.alert_finished.connect(self._cooldown_manager.start_cooldown)

    def _setup_ui(self) -> None:
        """Configura a interface principal."""
        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)

        # === Medidor de Volume ===
        volume_group = QGroupBox("Monitor de Volume")
        volume_layout = QVBoxLayout(volume_group)

        self._volume_bar = QProgressBar()
        self._volume_bar.setRange(0, 100)
        self._volume_bar.setTextVisible(True)
        self._volume_bar.setFormat("%v%")
        self._volume_bar.setMinimumHeight(30)
        volume_layout.addWidget(self._volume_bar)

        # Barra de acumulação
        self._accumulation_bar = QProgressBar()
        self._accumulation_bar.setRange(0, 100)
        self._accumulation_bar.setFormat("Acumulado: %v%")
        self._accumulation_bar.setStyleSheet(
            "QProgressBar::chunk { background-color: #ff6600; }"
        )
        volume_layout.addWidget(QLabel("Tempo acima do limite:"))
        volume_layout.addWidget(self._accumulation_bar)

        self._volume_label = QLabel("Volume: 0%")
        volume_layout.addWidget(self._volume_label)

        layout.addWidget(volume_group)

        # === Controles Principais ===
        controls_group = QGroupBox("Controles")
        controls_layout = QVBoxLayout(controls_group)

        # Botões iniciar/parar
        btn_layout = QHBoxLayout()
        self._start_btn = QPushButton("▶ Iniciar")
        self._start_btn.clicked.connect(self._toggle_monitoring)
        self._start_btn.setMinimumHeight(40)
        btn_layout.addWidget(self._start_btn)

        self._calibrate_btn = QPushButton("🎯 Calibrar")
        self._calibrate_btn.clicked.connect(self._start_calibration)
        self._calibrate_btn.setMinimumHeight(40)
        btn_layout.addWidget(self._calibrate_btn)

        self._test_btn = QPushButton("🧪 Testar")
        self._test_btn.clicked.connect(self._simulate_loud_voice)
        self._test_btn.setMinimumHeight(40)
        btn_layout.addWidget(self._test_btn)

        controls_layout.addLayout(btn_layout)
        layout.addWidget(controls_group)

        # === Configurações ===
        settings_group = QGroupBox("Configurações")
        settings_layout = QVBoxLayout(settings_group)

        # Microfone
        mic_layout = QHBoxLayout()
        mic_layout.addWidget(QLabel("Microfone:"))
        self._mic_combo = QComboBox()
        self._mic_combo.currentIndexChanged.connect(self._on_mic_changed)
        mic_layout.addWidget(self._mic_combo)
        self._refresh_mic_btn = QPushButton("↻")
        self._refresh_mic_btn.setMaximumWidth(30)
        self._refresh_mic_btn.clicked.connect(self._refresh_devices)
        mic_layout.addWidget(self._refresh_mic_btn)
        settings_layout.addLayout(mic_layout)

        # Sensibilidade (threshold)
        thresh_layout = QHBoxLayout()
        thresh_layout.addWidget(QLabel("Sensibilidade:"))
        self._threshold_slider = QSlider(Qt.Orientation.Horizontal)
        self._threshold_slider.setRange(1, 50)
        self._threshold_slider.valueChanged.connect(self._on_threshold_changed)
        thresh_layout.addWidget(self._threshold_slider)
        self._threshold_label = QLabel("15%")
        thresh_layout.addWidget(self._threshold_label)
        settings_layout.addLayout(thresh_layout)

        # Tempo de bloqueio
        block_layout = QHBoxLayout()
        block_layout.addWidget(QLabel("Bloqueio (seg):"))
        self._block_spin = QSpinBox()
        self._block_spin.setRange(1, 60)
        self._block_spin.valueChanged.connect(self._on_block_duration_changed)
        block_layout.addWidget(self._block_spin)
        settings_layout.addLayout(block_layout)

        # Cooldown
        cooldown_layout = QHBoxLayout()
        cooldown_layout.addWidget(QLabel("Cooldown (seg):"))
        self._cooldown_spin = QSpinBox()
        self._cooldown_spin.setRange(5, 300)
        self._cooldown_spin.valueChanged.connect(self._on_cooldown_changed)
        cooldown_layout.addWidget(self._cooldown_spin)
        settings_layout.addLayout(cooldown_layout)

        # Tempo sustentado
        sustained_layout = QHBoxLayout()
        sustained_layout.addWidget(QLabel("Tempo sustentado (seg):"))
        self._sustained_spin = QDoubleSpinBox()
        self._sustained_spin.setRange(0.5, 10.0)
        self._sustained_spin.setSingleStep(0.5)
        self._sustained_spin.valueChanged.connect(self._on_sustained_changed)
        sustained_layout.addWidget(self._sustained_spin)
        settings_layout.addLayout(sustained_layout)

        # Janela de detecção
        window_layout = QHBoxLayout()
        window_layout.addWidget(QLabel("Janela detecção (seg):"))
        self._window_spin = QDoubleSpinBox()
        self._window_spin.setRange(2.0, 30.0)
        self._window_spin.setSingleStep(1.0)
        self._window_spin.valueChanged.connect(self._on_window_changed)
        window_layout.addWidget(self._window_spin)
        settings_layout.addLayout(window_layout)

        # Alertas progressivos
        self._progressive_check = QCheckBox("Alertas progressivos")
        self._progressive_check.stateChanged.connect(self._on_progressive_changed)
        settings_layout.addWidget(self._progressive_check)

        layout.addWidget(settings_group)

        # === Status ===
        status_group = QGroupBox("Status")
        status_layout = QVBoxLayout(status_group)
        self._status_label = QLabel("Parado")
        self._status_label.setStyleSheet("font-weight: bold; font-size: 14px;")
        status_layout.addWidget(self._status_label)
        self._cooldown_label = QLabel("")
        status_layout.addWidget(self._cooldown_label)
        layout.addWidget(status_group)

        # Popula dispositivos
        self._refresh_devices()

    def _setup_tray(self) -> None:
        """Configura o ícone na bandeja do sistema."""
        self._tray_icon = QSystemTrayIcon(self)
        # Usa ícone padrão do sistema
        icon = self.style().standardIcon(self.style().StandardPixmap.SP_MediaVolumeMuted)
        self._tray_icon.setIcon(icon)
        self.setWindowIcon(icon)

        tray_menu = QMenu()
        show_action = QAction("Mostrar", self)
        show_action.triggered.connect(self.show)
        tray_menu.addAction(show_action)

        quit_action = QAction("Sair", self)
        quit_action.triggered.connect(QApplication.quit)
        tray_menu.addAction(quit_action)

        self._tray_icon.setContextMenu(tray_menu)
        self._tray_icon.activated.connect(self._on_tray_activated)
        self._tray_icon.show()

    def _load_settings_to_ui(self) -> None:
        """Carrega valores das configurações para os controles da UI."""
        s = self._settings
        self._threshold_slider.setValue(int(s.volume_threshold * 100))
        self._block_spin.setValue(int(s.block_duration))
        self._cooldown_spin.setValue(int(s.cooldown_duration))
        self._sustained_spin.setValue(s.sustained_duration)
        self._window_spin.setValue(s.detection_window)
        self._progressive_check.setChecked(s.progressive_alerts)

    def _refresh_devices(self) -> None:
        """Atualiza lista de dispositivos de microfone."""
        self._mic_combo.blockSignals(True)
        self._mic_combo.clear()
        self._mic_combo.addItem("Padrão do sistema", None)
        try:
            devices = AudioMonitor.list_devices()
            for dev in devices:
                self._mic_combo.addItem(dev["name"], dev["index"])
        except Exception:
            pass
        self._mic_combo.blockSignals(False)

    # === Slots de eventos ===

    @Slot(float)
    def _on_volume_updated(self, volume: float) -> None:
        """Atualiza o medidor de volume na UI."""
        self._current_volume = volume
        self._volume_bar.setValue(int(volume * 100))
        self._volume_label.setText(f"Volume: {int(volume * 100)}%")

        # Muda cor baseado no limite
        if volume > self._settings.volume_threshold:
            self._volume_bar.setStyleSheet(
                "QProgressBar::chunk { background-color: #ff3333; }"
            )
        else:
            self._volume_bar.setStyleSheet(
                "QProgressBar::chunk { background-color: #33cc33; }"
            )

        # Coleta amostras durante calibração
        if self._calibrating:
            self._calibration_samples.append(volume)

    @Slot(float)
    def _on_accumulation_updated(self, fraction: float) -> None:
        """Atualiza barra de acumulação."""
        self._accumulation_bar.setValue(int(fraction * 100))

    @Slot()
    def _on_loud_voice(self) -> None:
        """Chamado quando voz alta sustentada é detectada."""
        if self._cooldown_manager.in_cooldown:
            return
        if self._alert_manager.is_active:
            return
        self._alert_manager.trigger_alert()

    @Slot(int)
    def _on_alert_triggered(self, level: int) -> None:
        """Exibe o overlay baseado no nível de alerta."""
        # Determina duração baseada no nível
        if level == AlertLevel.SMALL_WARNING:
            duration = max(3.0, self._settings.block_duration / 3)
        elif level == AlertLevel.OVERLAY:
            duration = max(5.0, self._settings.block_duration / 1.5)
        else:
            duration = self._settings.block_duration

        # Desativa detecção durante o alerta
        self._volume_detector.set_enabled(False)
        self._overlay.show_alert(level, duration)

    @Slot()
    def _on_overlay_closed(self) -> None:
        """Chamado quando o overlay fecha."""
        self._alert_manager.finish_alert()
        self._volume_detector.set_enabled(True)
        self._volume_detector.reset()

    @Slot(str)
    def _on_audio_error(self, error: str) -> None:
        """Mostra erro de áudio."""
        self._status_label.setText(f"Erro: {error}")
        self._tray_icon.showMessage("Erro", error, QSystemTrayIcon.MessageIcon.Warning)

    @Slot()
    def _toggle_monitoring(self) -> None:
        """Inicia ou para o monitoramento."""
        if self._monitoring:
            self._audio_monitor.stop()
            self._monitoring = False
            self._start_btn.setText("▶ Iniciar")
            self._status_label.setText("Parado")
            self._volume_bar.setValue(0)
            self._accumulation_bar.setValue(0)
        else:
            self._audio_monitor.start()
            self._monitoring = True
            self._start_btn.setText("⏹ Parar")
            self._status_label.setText("Monitorando...")

    @Slot()
    def _start_calibration(self) -> None:
        """Inicia calibração (5 segundos de captura)."""
        if not self._monitoring:
            QMessageBox.information(
                self, "Calibração",
                "Inicie o monitoramento antes de calibrar."
            )
            return

        self._calibrating = True
        self._calibration_samples.clear()
        self._calibrate_btn.setEnabled(False)
        self._status_label.setText("Calibrando... Fale normalmente por 5 segundos.")

        QTimer.singleShot(5000, self._finish_calibration)

    @Slot()
    def _finish_calibration(self) -> None:
        """Finaliza a calibração e define o limiar."""
        self._calibrating = False
        self._calibrate_btn.setEnabled(True)

        if not self._calibration_samples:
            self._status_label.setText("Calibração falhou - sem amostras.")
            return

        # Calcula média + margem de 50% para definir o limite
        avg = sum(self._calibration_samples) / len(self._calibration_samples)
        threshold = min(avg * 1.5, 0.95)
        threshold = max(threshold, 0.05)

        self._settings.calibrated_volume = avg
        self._settings.volume_threshold = threshold
        self._volume_detector.threshold = threshold
        self._threshold_slider.setValue(int(threshold * 100))
        self._settings_mgr.save()

        self._status_label.setText(
            f"Calibrado! Volume normal: {int(avg * 100)}%, Limite: {int(threshold * 100)}%"
        )

    @Slot()
    def _simulate_loud_voice(self) -> None:
        """Modo de teste: simula detecção de voz alta."""
        if self._cooldown_manager.in_cooldown:
            self._status_label.setText("Em cooldown - aguarde para testar.")
            return
        self._status_label.setText("Teste: simulando voz alta...")
        self._alert_manager.trigger_alert()

    @Slot(int)
    def _on_mic_changed(self, index: int) -> None:
        """Troca o microfone selecionado."""
        device = self._mic_combo.currentData()
        self._settings.microphone_device = device
        self._audio_monitor.set_device(device)
        self._settings_mgr.save()

    @Slot(int)
    def _on_threshold_changed(self, value: int) -> None:
        """Ajusta o limiar de volume."""
        threshold = value / 100.0
        self._settings.volume_threshold = threshold
        self._volume_detector.threshold = threshold
        self._threshold_label.setText(f"{value}%")
        self._settings_mgr.save()

    @Slot(int)
    def _on_block_duration_changed(self, value: int) -> None:
        """Ajusta duração do bloqueio."""
        self._settings.block_duration = float(value)
        self._alert_manager.block_duration = float(value)
        self._settings_mgr.save()

    @Slot(int)
    def _on_cooldown_changed(self, value: int) -> None:
        """Ajusta duração do cooldown."""
        self._settings.cooldown_duration = float(value)
        self._cooldown_manager.cooldown_duration = float(value)
        self._settings_mgr.save()

    @Slot(float)
    def _on_sustained_changed(self, value: float) -> None:
        """Ajusta tempo sustentado."""
        self._settings.sustained_duration = value
        self._volume_detector.sustained_duration = value
        self._settings_mgr.save()

    @Slot(float)
    def _on_window_changed(self, value: float) -> None:
        """Ajusta janela de detecção."""
        self._settings.detection_window = value
        self._volume_detector.detection_window = value
        self._settings_mgr.save()

    @Slot(int)
    def _on_progressive_changed(self, state: int) -> None:
        """Ativa/desativa alertas progressivos."""
        enabled = state == Qt.CheckState.Checked.value
        self._settings.progressive_alerts = enabled
        self._alert_manager.progressive = enabled
        self._settings_mgr.save()

    @Slot()
    def _update_ui_status(self) -> None:
        """Atualiza informações de status na UI."""
        if self._cooldown_manager.in_cooldown:
            remaining = self._cooldown_manager.remaining_time
            self._cooldown_label.setText(
                f"Cooldown: {int(remaining)}s restantes"
            )
        else:
            self._cooldown_label.setText("")

    def _on_tray_activated(self, reason: QSystemTrayIcon.ActivationReason) -> None:
        """Mostra a janela ao clicar no ícone da bandeja."""
        if reason == QSystemTrayIcon.ActivationReason.DoubleClick:
            self.show()
            self.activateWindow()

    def closeEvent(self, event: QCloseEvent) -> None:
        """Minimiza para bandeja em vez de fechar."""
        if self._tray_icon.isVisible():
            self.hide()
            self._tray_icon.showMessage(
                "Loud Voice Cooldown",
                "Aplicativo minimizado na bandeja do sistema.",
                QSystemTrayIcon.MessageIcon.Information,
                2000,
            )
            event.ignore()
        else:
            self._audio_monitor.stop()
            event.accept()
