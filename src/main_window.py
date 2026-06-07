"""
MainWindow - Interface principal do aplicativo.

Inclui: medidor de volume, painel de debug, controles de configuração,
botões de teste, seleção de microfone e bandeja do sistema.
"""

from enum import Enum

from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QSlider, QComboBox, QGroupBox,
    QProgressBar, QSpinBox, QDoubleSpinBox, QCheckBox,
    QSystemTrayIcon, QMenu, QApplication, QScrollArea,
)
from PySide6.QtCore import Qt, QTimer, Slot
from PySide6.QtGui import QAction, QCloseEvent

from .audio_monitor import AudioMonitor
from .volume_detector import VolumeDetector
from .alert_manager import AlertManager
from .cooldown_manager import CooldownManager
from .settings_manager import SettingsManager
from .overlay_window import OverlayWindow
from .reminder_window import ReminderWindow
from .logger import get_logger


class AppState(Enum):
    STOPPED = "Parado"
    MONITORING = "Monitorando"
    REMINDER_ACTIVE = "Lembrete ativo"
    BLOCK_ACTIVE = "Bloqueio ativo"
    COOLDOWN = "Cooldown"
    PAUSED = "Pausado"


class MainWindow(QMainWindow):
    """Janela principal do Loud Voice Cooldown v2."""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Loud Voice Cooldown")
        self.setMinimumSize(560, 780)
        self._log = get_logger()
        self._log.info("Aplicação iniciada")

        # Gerenciadores
        self._settings_mgr = SettingsManager()
        self._s = self._settings_mgr.settings

        self._audio = AudioMonitor(
            device=self._s.microphone_device,
            sample_rate=self._s.sample_rate,
            block_size=self._s.block_size,
        )
        self._detector = VolumeDetector(
            threshold=self._s.volume_threshold,
            analysis_interval_ms=self._s.analysis_interval_ms,
            accumulation_window=self._s.accumulation_window,
            block_accumulation=self._s.block_accumulation,
        )
        self._detector.set_volume_source(self._audio)

        self._alert = AlertManager(
            reminder_cooldown=self._s.reminder_cooldown,
            block_duration=self._s.block_duration,
            allow_reminders_during_cooldown=self._s.allow_reminders_during_cooldown,
        )
        self._cooldown = CooldownManager(
            cooldown_duration=self._s.post_block_cooldown,
        )
        self._overlay = OverlayWindow()
        self._reminder = ReminderWindow()

        # Estado
        self._state = AppState.STOPPED
        self._current_volume: float = 0.0
        self._paused = False

        # Timer UI (100ms) para atualizar painel de debug
        self._ui_timer = QTimer(self)
        self._ui_timer.setInterval(100)
        self._ui_timer.timeout.connect(self._update_debug_panel)

        self._connect_signals()
        self._setup_ui()
        self._setup_tray()
        self._load_settings_to_ui()
        self._ui_timer.start()

    # ------------------------------------------------------------------ #
    #  Sinais
    # ------------------------------------------------------------------ #

    def _connect_signals(self) -> None:
        self._audio.volume_updated.connect(self._on_volume_updated)
        self._audio.error_occurred.connect(self._on_audio_error)

        # Pico detectado -> pede lembrete
        self._detector.peak_detected.connect(self._on_peak_detected)
        # Bloqueio por acúmulo
        self._detector.block_triggered.connect(self._on_block_triggered)

        # Alert manager
        self._alert.show_reminder.connect(self._show_reminder)
        self._alert.show_block.connect(self._show_block)
        self._alert.block_finished.connect(self._on_block_finished)

        # Overlay fecha
        self._overlay.overlay_closed.connect(self._on_overlay_closed)

        # Reminder fecha
        self._reminder.reminder_closed.connect(self._on_reminder_closed)

    # ------------------------------------------------------------------ #
    #  UI
    # ------------------------------------------------------------------ #

    def _setup_ui(self) -> None:
        central = QWidget()
        self.setCentralWidget(central)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll_content = QWidget()
        layout = QVBoxLayout(scroll_content)
        scroll.setWidget(scroll_content)

        outer = QVBoxLayout(central)
        outer.addWidget(scroll)

        # === Volume Meter ===
        vol_group = QGroupBox("Volume do Microfone")
        vol_layout = QVBoxLayout(vol_group)

        self._volume_bar = QProgressBar()
        self._volume_bar.setRange(0, 100)
        self._volume_bar.setTextVisible(True)
        self._volume_bar.setFormat("%v")
        self._volume_bar.setMinimumHeight(28)
        vol_layout.addWidget(self._volume_bar)

        # Acumulação
        self._acc_bar = QProgressBar()
        self._acc_bar.setRange(0, 100)
        self._acc_bar.setFormat("Acumulado: %v%")
        self._acc_bar.setStyleSheet("QProgressBar::chunk { background-color: #ff6600; }")
        vol_layout.addWidget(QLabel("Tempo acima do limite (janela móvel):"))
        vol_layout.addWidget(self._acc_bar)

        layout.addWidget(vol_group)

        # === Controles ===
        ctrl_group = QGroupBox("Controles")
        ctrl_layout = QVBoxLayout(ctrl_group)

        row1 = QHBoxLayout()
        self._start_btn = QPushButton("Iniciar")
        self._start_btn.setMinimumHeight(36)
        self._start_btn.clicked.connect(self._toggle_monitoring)
        row1.addWidget(self._start_btn)

        self._pause_btn = QPushButton("Pausar")
        self._pause_btn.setMinimumHeight(36)
        self._pause_btn.setEnabled(False)
        self._pause_btn.clicked.connect(self._toggle_pause)
        row1.addWidget(self._pause_btn)
        ctrl_layout.addLayout(row1)

        # Botões de teste
        row2 = QHBoxLayout()
        btn_reminder = QPushButton("Testar lembrete")
        btn_reminder.clicked.connect(self._test_reminder)
        row2.addWidget(btn_reminder)

        btn_block = QPushButton("Testar bloqueio")
        btn_block.clicked.connect(self._test_block)
        row2.addWidget(btn_block)
        ctrl_layout.addLayout(row2)

        row3 = QHBoxLayout()
        btn_sim = QPushButton("Simular pico (+1s)")
        btn_sim.clicked.connect(self._simulate_peak)
        row3.addWidget(btn_sim)

        btn_reset = QPushButton("Resetar acumulador")
        btn_reset.clicked.connect(self._reset_accumulator)
        row3.addWidget(btn_reset)
        ctrl_layout.addLayout(row3)

        layout.addWidget(ctrl_group)

        # === Configurações ===
        cfg_group = QGroupBox("Configurações")
        cfg_layout = QVBoxLayout(cfg_group)

        # Microfone
        mic_row = QHBoxLayout()
        mic_row.addWidget(QLabel("Microfone:"))
        self._mic_combo = QComboBox()
        self._mic_combo.currentIndexChanged.connect(self._on_mic_changed)
        mic_row.addWidget(self._mic_combo)
        btn_refresh = QPushButton("↻")
        btn_refresh.setMaximumWidth(30)
        btn_refresh.clicked.connect(self._refresh_devices)
        mic_row.addWidget(btn_refresh)
        cfg_layout.addLayout(mic_row)

        # Limite de volume para alerta
        thresh_row = QHBoxLayout()
        thresh_row.addWidget(QLabel("Limite de volume para alerta:"))
        self._threshold_slider = QSlider(Qt.Orientation.Horizontal)
        self._threshold_slider.setRange(0, 100)
        self._threshold_slider.valueChanged.connect(self._on_threshold_changed)
        thresh_row.addWidget(self._threshold_slider)
        self._threshold_label = QLabel("40")
        self._threshold_label.setMinimumWidth(30)
        thresh_row.addWidget(self._threshold_label)
        cfg_layout.addLayout(thresh_row)

        # Intervalo de análise
        self._add_spin_row(cfg_layout, "Intervalo de análise (ms):",
                           50, 1000, self._s.analysis_interval_ms,
                           self._on_analysis_interval_changed, is_int=True,
                           attr="_analysis_spin")

        # Janela de acúmulo
        self._add_dspin_row(cfg_layout, "Janela de acúmulo (s):",
                            5.0, 300.0, self._s.accumulation_window, 5.0,
                            self._on_acc_window_changed, attr="_acc_window_spin")

        # Tempo acumulado para bloqueio
        self._add_dspin_row(cfg_layout, "Tempo acumulado para bloqueio (s):",
                            1.0, 60.0, self._s.block_accumulation, 0.5,
                            self._on_block_acc_changed, attr="_block_acc_spin")

        # Duração do lembrete visual
        self._add_dspin_row(cfg_layout, "Duração do lembrete (s):",
                            0.5, 10.0, self._s.reminder_duration, 0.5,
                            self._on_reminder_duration_changed, attr="_reminder_dur_spin")

        # Cooldown entre lembretes
        self._add_dspin_row(cfg_layout, "Cooldown entre lembretes (s):",
                            0.5, 30.0, self._s.reminder_cooldown, 0.5,
                            self._on_reminder_cd_changed, attr="_reminder_cd_spin")

        # Duração do bloqueio
        self._add_spin_row(cfg_layout, "Duração do bloqueio (s):",
                           1, 60, int(self._s.block_duration),
                           self._on_block_duration_changed, is_int=True,
                           attr="_block_dur_spin")

        # Cooldown após bloqueio
        self._add_spin_row(cfg_layout, "Cooldown após bloqueio (s):",
                           5, 300, int(self._s.post_block_cooldown),
                           self._on_post_block_cd_changed, is_int=True,
                           attr="_post_block_cd_spin")

        # Checkbox: lembretes durante cooldown
        self._remind_in_cd_check = QCheckBox("Permitir lembretes durante cooldown")
        self._remind_in_cd_check.stateChanged.connect(self._on_remind_in_cd_changed)
        cfg_layout.addWidget(self._remind_in_cd_check)

        layout.addWidget(cfg_group)

        # === Painel de Debug ===
        debug_group = QGroupBox("Painel de Debug")
        debug_layout = QVBoxLayout(debug_group)
        self._debug_labels: dict[str, QLabel] = {}

        debug_fields = [
            "mic_name", "mic_status", "volume_current", "volume_max",
            "threshold", "above_below", "accumulated_time",
            "acc_window", "block_target", "trigger_count",
            "last_trigger", "app_state", "cooldown_remaining",
        ]
        field_names = [
            "Microfone", "Status microfone", "Volume atual",
            "Volume máximo recente", "Limite de volume", "Acima/Abaixo do limite",
            "Tempo acumulado", "Janela de acúmulo", "Tempo para bloqueio",
            "Gatilhos detectados", "Último gatilho", "Estado da aplicação",
            "Cooldown restante",
        ]
        for key, name in zip(debug_fields, field_names):
            row = QHBoxLayout()
            row.addWidget(QLabel(f"{name}:"))
            lbl = QLabel("—")
            lbl.setStyleSheet("font-weight: bold;")
            row.addWidget(lbl)
            row.addStretch()
            debug_layout.addLayout(row)
            self._debug_labels[key] = lbl

        layout.addWidget(debug_group)

        # Popula devices
        self._refresh_devices()

    # --- helpers para criar rows ---

    def _add_spin_row(self, parent_layout, label, min_v, max_v, default, slot,
                      is_int=True, attr=None):
        row = QHBoxLayout()
        row.addWidget(QLabel(label))
        spin = QSpinBox()
        spin.setRange(min_v, max_v)
        spin.setValue(default)
        spin.valueChanged.connect(slot)
        row.addWidget(spin)
        parent_layout.addLayout(row)
        if attr:
            setattr(self, attr, spin)

    def _add_dspin_row(self, parent_layout, label, min_v, max_v, default, step,
                       slot, attr=None):
        row = QHBoxLayout()
        row.addWidget(QLabel(label))
        spin = QDoubleSpinBox()
        spin.setRange(min_v, max_v)
        spin.setSingleStep(step)
        spin.setValue(default)
        spin.valueChanged.connect(slot)
        row.addWidget(spin)
        parent_layout.addLayout(row)
        if attr:
            setattr(self, attr, spin)

    def _setup_tray(self) -> None:
        self._tray = QSystemTrayIcon(self)
        icon = self.style().standardIcon(self.style().StandardPixmap.SP_MediaVolumeMuted)
        self._tray.setIcon(icon)
        self.setWindowIcon(icon)

        menu = QMenu()
        show_act = QAction("Mostrar", self)
        show_act.triggered.connect(self.show)
        menu.addAction(show_act)
        quit_act = QAction("Sair", self)
        quit_act.triggered.connect(QApplication.quit)
        menu.addAction(quit_act)

        self._tray.setContextMenu(menu)
        self._tray.activated.connect(self._on_tray_activated)
        self._tray.show()

    def _load_settings_to_ui(self) -> None:
        s = self._s
        self._threshold_slider.setValue(s.volume_threshold)
        self._remind_in_cd_check.setChecked(s.allow_reminders_during_cooldown)

    def _refresh_devices(self) -> None:
        self._mic_combo.blockSignals(True)
        self._mic_combo.clear()
        self._mic_combo.addItem("Padrão do sistema", None)
        try:
            for dev in AudioMonitor.list_devices():
                self._mic_combo.addItem(dev["name"], dev["index"])
        except Exception:
            pass
        self._mic_combo.blockSignals(False)

    # ------------------------------------------------------------------ #
    #  Estado
    # ------------------------------------------------------------------ #

    def _set_state(self, state: AppState) -> None:
        self._state = state

    # ------------------------------------------------------------------ #
    #  Slots de volume
    # ------------------------------------------------------------------ #

    @Slot(float)
    def _on_volume_updated(self, volume: float) -> None:
        self._current_volume = volume
        self._volume_bar.setValue(int(volume))
        if volume > self._s.volume_threshold:
            self._volume_bar.setStyleSheet(
                "QProgressBar::chunk { background-color: #ff3333; }"
            )
        else:
            self._volume_bar.setStyleSheet(
                "QProgressBar::chunk { background-color: #33cc33; }"
            )

    @Slot()
    def _on_peak_detected(self) -> None:
        """Pico de voz alta detectado -> solicita lembrete."""
        if self._state == AppState.BLOCK_ACTIVE:
            return
        if self._cooldown.in_cooldown and not self._alert.allow_reminders_during_cooldown:
            return
        self._alert.request_reminder()

    @Slot()
    def _on_block_triggered(self) -> None:
        """Tempo acumulado atingiu limiar -> aciona bloqueio."""
        if self._cooldown.in_cooldown:
            return
        if self._alert.is_block_active:
            return
        self._alert.trigger_block()

    @Slot()
    def _show_reminder(self) -> None:
        self._set_state(AppState.REMINDER_ACTIVE)
        self._reminder.show_reminder(self._s.reminder_duration)

    @Slot()
    def _on_reminder_closed(self) -> None:
        if self._state == AppState.REMINDER_ACTIVE:
            if self._cooldown.in_cooldown:
                self._set_state(AppState.COOLDOWN)
            else:
                self._set_state(AppState.MONITORING)

    @Slot()
    def _show_block(self) -> None:
        self._set_state(AppState.BLOCK_ACTIVE)
        self._detector.set_enabled(False)
        self._overlay.show_block(self._alert.block_duration)

    @Slot()
    def _on_overlay_closed(self) -> None:
        self._alert.finish_block()

    @Slot()
    def _on_block_finished(self) -> None:
        # Zera acumulador e inicia cooldown
        self._detector.reset()
        self._cooldown.start_cooldown()
        self._detector.set_enabled(True)
        self._set_state(AppState.COOLDOWN)

    @Slot(str)
    def _on_audio_error(self, error: str) -> None:
        self._debug_labels["mic_status"].setText(f"ERRO: {error}")
        self._tray.showMessage("Erro", error, QSystemTrayIcon.MessageIcon.Warning)

    # ------------------------------------------------------------------ #
    #  Controles
    # ------------------------------------------------------------------ #

    @Slot()
    def _toggle_monitoring(self) -> None:
        if self._state != AppState.STOPPED and self._state != AppState.PAUSED:
            # Parar
            self._audio.stop()
            self._detector.stop()
            self._set_state(AppState.STOPPED)
            self._start_btn.setText("Iniciar")
            self._pause_btn.setEnabled(False)
            self._pause_btn.setText("Pausar")
            self._paused = False
            self._volume_bar.setValue(0)
            self._acc_bar.setValue(0)
            self._log.info("Monitoramento parado")
        else:
            # Iniciar
            self._audio.start()
            self._detector.start()
            self._set_state(AppState.MONITORING)
            self._start_btn.setText("Parar")
            self._pause_btn.setEnabled(True)
            self._paused = False
            self._log.info("Monitoramento iniciado")

    @Slot()
    def _toggle_pause(self) -> None:
        if self._paused:
            self._detector.set_enabled(True)
            self._set_state(AppState.MONITORING)
            self._pause_btn.setText("Pausar")
            self._paused = False
            self._log.info("Monitoramento retomado")
        else:
            self._detector.set_enabled(False)
            self._set_state(AppState.PAUSED)
            self._pause_btn.setText("Retomar")
            self._paused = True
            self._log.info("Monitoramento pausado")

    @Slot()
    def _test_reminder(self) -> None:
        self._alert.force_reminder()

    @Slot()
    def _test_block(self) -> None:
        self._alert.force_block()
        self._show_block()

    @Slot()
    def _simulate_peak(self) -> None:
        self._detector.inject_time(1.0)

    @Slot()
    def _reset_accumulator(self) -> None:
        self._detector.reset()

    # ------------------------------------------------------------------ #
    #  Configurações
    # ------------------------------------------------------------------ #

    @Slot(int)
    def _on_mic_changed(self, index: int) -> None:
        device = self._mic_combo.currentData()
        self._s.microphone_device = device
        self._audio.set_device(device)
        self._settings_mgr.save()

    @Slot(int)
    def _on_threshold_changed(self, value: int) -> None:
        self._s.volume_threshold = value
        self._detector.threshold = value
        self._threshold_label.setText(str(value))
        self._settings_mgr.save()

    @Slot(int)
    def _on_analysis_interval_changed(self, value: int) -> None:
        self._s.analysis_interval_ms = value
        self._detector.analysis_interval_ms = value
        self._settings_mgr.save()

    @Slot(float)
    def _on_acc_window_changed(self, value: float) -> None:
        self._s.accumulation_window = value
        self._detector.accumulation_window = value
        self._settings_mgr.save()

    @Slot(float)
    def _on_block_acc_changed(self, value: float) -> None:
        self._s.block_accumulation = value
        self._detector.block_accumulation = value
        self._settings_mgr.save()

    @Slot(float)
    def _on_reminder_duration_changed(self, value: float) -> None:
        self._s.reminder_duration = value
        self._settings_mgr.save()

    @Slot(float)
    def _on_reminder_cd_changed(self, value: float) -> None:
        self._s.reminder_cooldown = value
        self._alert.reminder_cooldown = value
        self._settings_mgr.save()

    @Slot(int)
    def _on_block_duration_changed(self, value: int) -> None:
        self._s.block_duration = float(value)
        self._alert.block_duration = float(value)
        self._settings_mgr.save()

    @Slot(int)
    def _on_post_block_cd_changed(self, value: int) -> None:
        self._s.post_block_cooldown = float(value)
        self._cooldown.cooldown_duration = float(value)
        self._settings_mgr.save()

    @Slot(int)
    def _on_remind_in_cd_changed(self, state: int) -> None:
        enabled = state == Qt.CheckState.Checked.value
        self._s.allow_reminders_during_cooldown = enabled
        self._alert.allow_reminders_during_cooldown = enabled
        self._settings_mgr.save()

    # ------------------------------------------------------------------ #
    #  Painel de Debug (atualizado a cada 100ms)
    # ------------------------------------------------------------------ #

    @Slot()
    def _update_debug_panel(self) -> None:
        d = self._debug_labels
        d["mic_name"].setText(
            self._mic_combo.currentText() if self._mic_combo.currentIndex() >= 0
            else "—"
        )
        d["mic_status"].setText(
            "Ativo" if self._audio.is_running else "Inativo"
        )
        vol = self._current_volume
        d["volume_current"].setText(f"{vol:.0f}")
        d["volume_max"].setText(f"{self._detector.max_recent_volume:.0f}")
        d["threshold"].setText(str(self._s.volume_threshold))

        above = vol > self._s.volume_threshold
        d["above_below"].setText(
            "ACIMA do limite" if above else "Abaixo do limite"
        )
        d["above_below"].setStyleSheet(
            "font-weight: bold; color: red;" if above
            else "font-weight: bold; color: green;"
        )

        acc = self._detector.accumulated_time
        self._acc_bar.setValue(
            int(min(acc / self._s.block_accumulation * 100, 100))
            if self._s.block_accumulation > 0 else 0
        )
        d["accumulated_time"].setText(f"{acc:.1f}s")
        d["acc_window"].setText(f"{self._s.accumulation_window:.0f}s")
        d["block_target"].setText(f"{self._s.block_accumulation:.1f}s")
        d["trigger_count"].setText(str(self._detector.trigger_count))
        d["last_trigger"].setText(self._detector.last_trigger_time or "—")

        # Estado
        if self._cooldown.in_cooldown and self._state not in (
            AppState.BLOCK_ACTIVE, AppState.REMINDER_ACTIVE
        ):
            self._set_state(AppState.COOLDOWN)
        elif (
            not self._cooldown.in_cooldown
            and self._state == AppState.COOLDOWN
        ):
            self._set_state(AppState.MONITORING)

        d["app_state"].setText(self._state.value)
        remaining = self._cooldown.remaining_time
        d["cooldown_remaining"].setText(
            f"{remaining:.0f}s" if remaining > 0 else "—"
        )

    # ------------------------------------------------------------------ #
    #  Bandeja
    # ------------------------------------------------------------------ #

    def _on_tray_activated(self, reason: QSystemTrayIcon.ActivationReason) -> None:
        if reason == QSystemTrayIcon.ActivationReason.DoubleClick:
            self.show()
            self.activateWindow()

    def closeEvent(self, event: QCloseEvent) -> None:
        if self._tray.isVisible():
            self.hide()
            self._tray.showMessage(
                "Loud Voice Cooldown",
                "Minimizado na bandeja do sistema.",
                QSystemTrayIcon.MessageIcon.Information,
                2000,
            )
            event.ignore()
        else:
            self._audio.stop()
            self._detector.stop()
            event.accept()
