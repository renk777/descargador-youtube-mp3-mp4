from __future__ import annotations

import json
import os
import queue
import subprocess
import sys
import threading
from pathlib import Path

from PySide6.QtCore import QEvent, Qt, QTimer, QUrl, Property, QPropertyAnimation, QEasingCurve
from PySide6.QtGui import QColor, QDesktopServices, QIcon, QKeySequence, QPainter, QShortcut
from PySide6.QtWidgets import (
    QApplication, QCheckBox, QComboBox, QFileDialog, QGraphicsOpacityEffect,
    QFrame, QGridLayout, QHBoxLayout, QHeaderView, QLabel, QLineEdit,
    QMainWindow, QMessageBox, QPlainTextEdit, QProgressBar, QPushButton,
    QRadioButton, QScrollArea, QSizeGrip, QTableWidget, QTableWidgetItem,
    QVBoxLayout, QWidget,
)
import download_core as core
from download_core import DownloadSettings, DownloadWorker
from windows_backdrop import enable_acrylic, set_acrylic_active
from ui_animations import AnimatedButton, NoticeBar
from user_errors import UserError, describe_error
import browser_login
from app_version import __version__


STYLE = '''
QMainWindow { background: transparent; }
QWidget { color: #f0f0f4; font-family: "Segoe UI"; font-size: 13px; }
QWidget#surface, QWidget#body, QWidget#titlebar { background: transparent; }
QFrame#card { background: rgba(22, 23, 29, 118); border: 1px solid rgba(255,255,255,24); border-radius: 12px; }
QLabel { background: transparent; border: none; }
QLabel#muted { color: #b7b8c5; font-size: 12px; }
QLabel#heading { font-size: 27px; font-weight: 700; }
QLabel#section { font-size: 15px; font-weight: 600; }
QLabel#eyebrow { color: #d5b4ec; font-size: 11px; font-weight: 700; }
QPushButton { background: rgba(255,255,255,20); border: 1px solid rgba(255,255,255,24); border-radius: 7px; padding: 8px 13px; }
QPushButton:hover { background: rgba(255,255,255,40); }
QPushButton:disabled { color: #898994; background: rgba(0,0,0,15); }
QPushButton#primary { background: #cf3d5e; border: none; font-weight: 600; padding: 10px 22px; }
QPushButton#primary:hover { background: #e34c70; }
QPushButton#primary:disabled { background: #633044; }
QPushButton#caption, QPushButton#close { background: transparent; border: none; border-radius: 0; padding: 4px; font-size: 17px; }
QPushButton#caption:hover { background: rgba(255,255,255,25); }
QPushButton#close:hover { background: #bc344b; }
QPlainTextEdit, QLineEdit, QComboBox { background: rgba(15,16,23,155); border: 1px solid rgba(255,255,255,24); border-radius: 7px; padding: 7px; selection-background-color: #713f79; }
QPlainTextEdit:focus, QLineEdit:focus, QComboBox:focus { border-color: #a96cba; }
QComboBox::drop-down { border: none; width: 24px; }
QComboBox QAbstractItemView { background: #30313b; color: white; selection-background-color: #713f79; }
QCheckBox, QRadioButton { background: transparent; spacing: 7px; }
QCheckBox::indicator, QRadioButton::indicator { width: 15px; height: 15px; border: 1px solid #9996a6; background: #32323e; border-radius: 4px; }
QRadioButton::indicator { border-radius: 8px; }
QCheckBox::indicator:checked, QRadioButton::indicator:checked { background: #d34b70; border-color: #e584a0; }
QTableWidget { background: transparent; alternate-background-color: rgba(255,255,255,8); border: none; gridline-color: transparent; selection-background-color: rgba(180,100,160,60); }
QHeaderView::section { background: rgba(35,35,45,150); border: none; color: #b8b7c7; padding: 7px; text-align: left; }
QTableCornerButton::section { background: transparent; border: none; }
QProgressBar { background: rgba(10,10,20,110); border: none; border-radius: 3px; height: 6px; }
QProgressBar::chunk { background: #dd4b70; border-radius: 3px; }
QScrollArea { background: transparent; border: none; }
QScrollBar:vertical { background: transparent; width: 8px; margin: 0; }
QScrollBar::handle:vertical { background: rgba(210,205,225,90); border-radius: 4px; min-height: 20px; }
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }
QDialog { background: #34353d; }
'''


def label(text='', name=None):
    widget = QLabel(text)
    if name:
        widget.setObjectName(name)
    return widget


class TitleBar(QWidget):
    def __init__(self, window):
        super().__init__(window)
        self.window = window
        self.setObjectName('titlebar')
        self.setFixedHeight(44)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(16, 0, 0, 0)
        icon = QLabel()
        icon.setPixmap(window.windowIcon().pixmap(23, 23))
        icon.setFixedWidth(27)
        layout.addWidget(icon)
        layout.addWidget(label('Descargador · v' + __version__, 'section'))
        layout.addStretch()
        for text, callback, name in (('−', window.showMinimized, 'caption'),
                                     ('□', self.toggle_maximize, 'caption'), ('×', window.close, 'close')):
            button = QPushButton(text)
            button.setObjectName(name)
            button.setFixedSize(46, 44)
            button.clicked.connect(callback)
            layout.addWidget(button)

    def toggle_maximize(self):
        self.window.showNormal() if self.window.isMaximized() else self.window.showMaximized()

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton and self.window.windowHandle():
            self.window.windowHandle().startSystemMove()

    def mouseDoubleClickEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.toggle_maximize()


class DescargadorApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle('Descargador de YouTube · v' + __version__)
        self.setWindowIcon(QIcon(str(core._application_dir() / 'logo.png')))
        self.setWindowFlags(Qt.WindowType.Window | Qt.WindowType.FramelessWindowHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.resize(1080, 850)
        self.setMinimumSize(860, 700)
        self.events = queue.Queue()
        self.cancel_event = threading.Event()
        self.is_downloading = self.close_requested = False
        self.failed_urls, self.job_rows, self.controls = [], {}, []
        self.last_settings = None
        self.report_path = None
        self.cookie_file = self.cookie_browser = ''
        self.session_checking = False
        self.session_pending = False
        self.login_browser = None
        self._login_opening = False
        self._centered_on_start = False
        self.last_error = None
        self.seen_error_codes = set()
        self._cards = []
        self._intro_animations = []
        self._intro_started = False
        self._window_active = False
        self._background_color = QColor('#454648')
        self._focus_animation = QPropertyAnimation(self, b'backdropColor', self)
        self._focus_animation.setDuration(190)
        self._focus_animation.setEasingCurve(QEasingCurve.Type.OutCubic)
        self._focus_animation.finished.connect(self._focus_animation_finished)
        self.acrylic_enabled = False
        self.backdrop_message = 'Fondo sólido'
        self.backdrop_initialized = False
        self.saved = core._load_settings()
        self.setStyleSheet(STYLE)
        self._build_ui()
        self.timer = QTimer(self)
        self.timer.timeout.connect(self._process_events)
        self.timer.start(80)
        self.shortcut = QShortcut(QKeySequence('Ctrl+Return'), self)
        self.shortcut.activated.connect(self._start_download)

    def _card(self):
        frame = QFrame()
        frame.setObjectName('card')
        self._cards.append(frame)
        return frame

    def _button(self, text, callback, lock=False, primary=False):
        button = AnimatedButton(text)
        button.clicked.connect(callback)
        if primary:
            button.setObjectName('primary')
        if lock:
            self.controls.append(button)
        return button

    def _build_ui(self):
        self.surface = QWidget()
        self.surface.setObjectName('surface')
        self.surface.setAutoFillBackground(False)
        self.setCentralWidget(self.surface)
        shell = QVBoxLayout(self.surface)
        shell.setContentsMargins(0, 0, 0, 0)
        shell.setSpacing(0)
        self.titlebar = TitleBar(self)
        shell.addWidget(self.titlebar)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.viewport().setAutoFillBackground(False)
        scroll.viewport().setStyleSheet('background: transparent;')
        body = QWidget()
        body.setObjectName('body')
        body.setAutoFillBackground(False)
        scroll.setWidget(body)
        shell.addWidget(scroll, 1)
        main = QVBoxLayout(body)
        main.setContentsMargins(28, 12, 28, 14)
        main.setSpacing(14)
        main.addWidget(label('TU MÚSICA. TUS VIDEOS.', 'eyebrow'))
        main.addWidget(label('De YouTube a tu biblioteca', 'heading'))
        subtitle = QHBoxLayout()
        subtitle.addWidget(label('Audio y video, a tu manera.', 'muted'))
        subtitle.addStretch()
        self.session_button = self._button('Iniciar sesión en YouTube', self._session_dialog, lock=True)
        subtitle.addWidget(self.session_button)
        self.session_finish_button = self._button('Ya inicié sesión', self._verify_sign_in, lock=True)
        self.session_finish_button.hide()
        subtitle.addWidget(self.session_finish_button)
        main.addLayout(subtitle)

        composer = QHBoxLayout()
        composer.setSpacing(14)
        links = self._card()
        left = QVBoxLayout(links)
        left.setContentsMargins(16, 14, 16, 14)
        heading = QHBoxLayout()
        heading.addWidget(label('01  Añade tus enlaces', 'section'))
        heading.addStretch()
        self.counter = label('0 enlaces', 'muted')
        heading.addWidget(self.counter)
        left.addLayout(heading)
        left.addWidget(label('Videos, Shorts o playlists · un enlace por línea', 'muted'))
        self.url_text = QPlainTextEdit()
        self.url_text.setPlaceholderText('https://www.youtube.com/watch?v=…\nhttps://www.youtube.com/playlist?list=…')
        self.url_text.setFixedHeight(110)
        self.url_text.textChanged.connect(self._urls_changed)
        left.addWidget(self.url_text, 1)
        actions = QHBoxLayout()
        actions.addWidget(self._button('Pegar enlaces', self._paste_urls, lock=True))
        actions.addWidget(self._button('Limpiar', self._clear_urls, lock=True))
        actions.addStretch()
        left.addLayout(actions)
        composer.addWidget(links, 3)

        options = self._card()
        right = QVBoxLayout(options)
        right.setContentsMargins(16, 14, 16, 14)
        right.addWidget(label('02  Elige cómo guardarlo', 'section'))
        mode_row = QHBoxLayout()
        self.audio_radio, self.video_radio = QRadioButton('Solo audio'), QRadioButton('Video + audio')
        mode_row.addWidget(self.audio_radio)
        mode_row.addWidget(self.video_radio)
        right.addLayout(mode_row)
        grid = QGridLayout()
        grid.addWidget(label('Formato del archivo', 'muted'), 0, 0)
        grid.addWidget(label('Calidad máxima', 'muted'), 0, 1)
        self.format_combo, self.quality_combo = QComboBox(), QComboBox()
        grid.addWidget(self.format_combo, 1, 0)
        grid.addWidget(self.quality_combo, 1, 1)
        right.addLayout(grid)
        self.playlist_check = QCheckBox('Incluir listas de reproducción')
        self.playlist_check.setChecked(self.saved.get('playlist', True) is True)
        self.skip_check = QCheckBox('Omitir descargas completadas')
        self.skip_check.setChecked(self.saved.get('skip_completed', True) is True)
        right.addWidget(self.playlist_check)
        right.addWidget(self.skip_check)
        right.addWidget(label('Un fallo no detiene los demás videos.', 'muted'))
        composer.addWidget(options, 2)
        main.addLayout(composer)
        self.controls.extend([self.audio_radio, self.video_radio, self.format_combo,
                              self.quality_combo, self.playlist_check, self.skip_check])
        fmt = self.saved.get('format', 'mp3')
        if not isinstance(fmt, str) or fmt not in core.QUALITY:
            fmt = 'mp3'
        self.audio_radio.setChecked(fmt in core.AUDIO_FORMATS)
        self.video_radio.setChecked(fmt in core.VIDEO_FORMATS)
        self._mode_changed()
        self.format_combo.setCurrentIndex(self.format_combo.findData(fmt))
        self._format_changed()
        quality = self.saved.get('quality')
        if quality in core.QUALITY[fmt]:
            self.quality_combo.setCurrentText(quality)
        self.audio_radio.toggled.connect(self._mode_changed)
        self.format_combo.currentIndexChanged.connect(self._format_changed)

        folder = self._card()
        folder_layout = QHBoxLayout(folder)
        folder_layout.setContentsMargins(16, 10, 16, 10)
        folder_layout.addWidget(label('Guardar en'))
        self.output_dir = QLineEdit(str(core._load_output_dir()))
        self.controls.append(self.output_dir)
        folder_layout.addWidget(self.output_dir, 1)
        folder_layout.addWidget(self._button('Cambiar…', self._choose_folder, lock=True))
        folder_layout.addWidget(self._button('Abrir carpeta', self._open_folder, lock=True))
        main.addWidget(folder)

        activity = self._card()
        activity_layout = QVBoxLayout(activity)
        activity_layout.setContentsMargins(16, 12, 16, 12)
        row = QHBoxLayout()
        row.addWidget(label('Tu actividad', 'section'))
        row.addStretch()
        self.batch_label = label('SIN DESCARGAS ACTIVAS', 'muted')
        row.addWidget(self.batch_label)
        activity_layout.addLayout(row)
        self.jobs = QTableWidget(0, 2)
        self.jobs.setHorizontalHeaderLabels(['ENLACE DEL VIDEO', 'ESTADO'])
        self.jobs.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.jobs.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        self.jobs.verticalHeader().hide()
        self.jobs.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.jobs.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.jobs.setMinimumHeight(100)
        self.jobs.setMaximumHeight(150)
        self.jobs.setAlternatingRowColors(True)
        self.jobs.viewport().setAutoFillBackground(False)
        activity_layout.addWidget(self.jobs, 1)
        self.log_text = QPlainTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setMaximumBlockCount(500)
        self.log_text.setFixedHeight(58)
        self.log_text.setPlaceholderText('Aquí aparecerán los detalles de la descarga y el archivo TXT de fallos.')
        activity_layout.addWidget(self.log_text)
        main.addWidget(activity, 1)
        footer_widget = QWidget()
        footer_widget.setObjectName('body')
        footer = QVBoxLayout(footer_widget)
        footer.setContentsMargins(28, 10, 28, 6)
        footer.setSpacing(6)
        shell.addWidget(footer_widget)
        self.notice = NoticeBar()
        footer.addWidget(self.notice)
        self.progress = QProgressBar()
        self.progress.setRange(0, 1000)
        self.progress.setValue(0)
        self.progress.setTextVisible(False)
        self.progress.setFixedHeight(6)
        self.progress_animation = QPropertyAnimation(self.progress, b'value', self)
        self.progress_animation.setDuration(200)
        self.progress_animation.setEasingCurve(QEasingCurve.Type.OutCubic)
        footer.addWidget(self.progress)
        self.status_label = label('Todo listo. Añade tus enlaces para empezar.')
        self.status_label.setWordWrap(True)
        footer.addWidget(self.status_label)
        self.detail_label = label('El progreso corresponde al archivo actual.', 'muted')
        self.detail_label.setWordWrap(True)
        footer.addWidget(self.detail_label)
        buttons = QHBoxLayout()
        buttons.addWidget(label('by kenner manuel varilla fuentes', 'muted'))
        buttons.addStretch()
        self.report_button = self._button('Ver TXT de fallos', self._open_report)
        self.report_button.setEnabled(False)
        buttons.addWidget(self.report_button)
        self.retry_button = self._button('Reintentar fallidos', self._retry)
        self.retry_button.setEnabled(False)
        buttons.addWidget(self.retry_button)
        self.cancel_button = self._button('Cancelar', self._cancel)
        self.cancel_button.setEnabled(False)
        buttons.addWidget(self.cancel_button)
        self.download_button = self._button('Descargar', self._start_download, primary=True)
        buttons.addWidget(self.download_button)
        footer.addLayout(buttons)
        self.grip = QSizeGrip(self.surface)
        self.grip.setFixedSize(14, 14)
        shell.addWidget(self.grip, 0, Qt.AlignmentFlag.AlignRight)

    @Property(QColor)
    def backdropColor(self):
        return self._background_color

    @backdropColor.setter
    def backdropColor(self, value):
        self._background_color = QColor(value)
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_Source)
        painter.fillRect(self.rect(), self._background_color)
        painter.end()

    def event(self, event):
        result = super().event(event)
        if hasattr(self, '_focus_animation'):
            if event.type() == QEvent.Type.WindowActivate:
                self._set_window_active(True)
                if getattr(self, 'session_pending', False) and not self.session_checking and not self.is_downloading:
                    QTimer.singleShot(450, lambda: self._verify_sign_in() if self.session_pending else None)
            elif event.type() == QEvent.Type.WindowDeactivate:
                self._set_window_active(False)
            elif event.type() == QEvent.Type.WindowStateChange and getattr(self, 'backdrop_initialized', False) and not self.isMinimized():
                QTimer.singleShot(0, self._initialize_backdrop)
        return result

    def _center_on_start(self):
        if self._centered_on_start:
            return
        self._centered_on_start = True
        screen = self.screen() or QApplication.primaryScreen()
        if screen is None:
            return
        area = screen.availableGeometry()
        # Fit the work area first; the layout already scrolls on small screens.
        width = min(self.width(), area.width())
        height = min(self.height(), area.height())
        if width < self.minimumWidth() or height < self.minimumHeight():
            self.setMinimumSize(min(self.minimumWidth(), width), min(self.minimumHeight(), height))
        self.resize(width, height)
        frame = self.frameGeometry()
        frame.moveCenter(area.center())
        self.move(frame.topLeft())

    def showEvent(self, event):
        self._center_on_start()
        super().showEvent(event)
        if not self.backdrop_initialized:
            self.backdrop_initialized = True
            QTimer.singleShot(0, self._initialize_backdrop)
        if not self._intro_started:
            self._intro_started = True
            for index, card in enumerate(self._cards):
                effect = QGraphicsOpacityEffect(card)
                card.setGraphicsEffect(effect)
                effect.setOpacity(0)
                animation = QPropertyAnimation(effect, b'opacity', self)
                animation.setDuration(300)
                animation.setStartValue(0.0)
                animation.setEndValue(1.0)
                animation.setEasingCurve(QEasingCurve.Type.OutCubic)
                self._intro_animations.append(animation)
                QTimer.singleShot(50 + index * 55, animation.start)

    def _initialize_backdrop(self):
        self.acrylic_enabled, self.backdrop_message = enable_acrylic(int(self.winId()))
        self._set_window_active(self.isActiveWindow(), force=True)

    def _set_window_active(self, active, force=False):
        if active == self._window_active and not force:
            return
        self._window_active = active
        self._focus_animation.stop()
        if active and self.acrylic_enabled:
            applied, message = set_acrylic_active(int(self.winId()), True)
            if not applied:
                self.acrylic_enabled = False
                self.backdrop_message = message
        target = QColor(19, 19, 25, 18) if active and self.acrylic_enabled else QColor('#454648')
        self._focus_animation.setStartValue(self._background_color)
        self._focus_animation.setEndValue(target)
        self._focus_animation.start()

    def _focus_animation_finished(self):
        if not self._window_active and self.acrylic_enabled:
            set_acrylic_active(int(self.winId()), False)

    def _notify(self, title, message, kind='error', action_text='', callback=None):
        self.notice.show_message(title, message, kind, action_text, callback)

    def _notify_issue(self, issue, callback=None):
        action = 'Reintentar' if callback else ''
        self._notify(issue.title, issue.message, 'error', action, callback)

    def _animate_progress(self, percent):
        self.progress_animation.stop()
        if self.progress.maximum() == 0:
            self.progress.setRange(0, 1000)
            self.progress.setValue(0)
        self.progress_animation.setStartValue(self.progress.value())
        self.progress_animation.setEndValue(max(0, min(1000, round(percent * 10))))
        self.progress_animation.start()

    def _mode_changed(self, *_):
        formats = core.AUDIO_FORMATS if self.audio_radio.isChecked() else core.VIDEO_FORMATS
        self.format_combo.blockSignals(True)
        self.format_combo.clear()
        for fmt in formats:
            self.format_combo.addItem(core.FORMAT_NAMES[fmt], fmt)
        self.format_combo.blockSignals(False)
        self._format_changed()

    def _format_changed(self, *_):
        fmt = self.format_combo.currentData()
        if fmt:
            self.quality_combo.clear()
            self.quality_combo.addItems(core.QUALITY[fmt])

    def _urls_changed(self):
        count = len(core._parse_urls(self.url_text.toPlainText()))
        self.counter.setText(f"{count} enlace{'s' if count != 1 else ''}")

    def _paste_urls(self):
        if self.is_downloading:
            return
        text = QApplication.clipboard().text().strip()
        if text:
            self.url_text.appendPlainText(text)

    def _clear_urls(self):
        if not self.is_downloading:
            self.url_text.clear()

    def _session_dialog(self):
        if self.is_downloading or self.session_checking or self._login_opening:
            return
        if self.session_pending:
            # Repeated clicks/returning focus may check the existing attempt, never open a second browser.
            self._notify('Ya abrimos YouTube para iniciar sesión',
                'Termina de iniciar sesión allí y vuelve aquí. No abriremos otro navegador.',
                'info', 'Ya inicié sesión', self._verify_sign_in)
            return
        self._login_opening = True
        try:
            browser = browser_login.available_browser()
            if browser is None:
                self._notify('Necesitas Firefox u otro navegador compatible',
                    'Instala Firefox, que es gratuito, y vuelve a pulsar Iniciar sesión en YouTube. No hace falta exportar archivos.', 'warning')
                return
            self.login_browser = browser
            self.session_pending = True
            browser_login.open_sign_in(browser)
        except OSError as error:
            self.login_browser = None
            self.session_pending = False
            self._log(str(error))
            self._notify('No pudimos abrir el navegador de inicio de sesión',
                         'Comprueba que Firefox o el navegador seleccionado funcione y vuelve a intentarlo.')
            return
        finally:
            self._login_opening = False
        self.session_finish_button.show()
        self.session_button.setText('Comprobar sesión de YouTube')
        name = {'firefox': 'Firefox', 'edge': 'Edge', 'chrome': 'Chrome'}.get(browser[0], 'el navegador')
        self._notify('Termina de iniciar sesión en ' + name,
            'Vuelve aquí cuando hayas entrado en YouTube. Preferimos Firefox para conectar tu sesión y no abriremos otro navegador.',
            'info', 'Ya inicié sesión', self._verify_sign_in)

    def _verify_sign_in(self):
        if self.is_downloading or self.session_checking or not self.login_browser:
            return
        self.session_checking = True
        self._refresh_session_controls()
        self._notify('Conectando tu sesión de YouTube', 'Estamos comprobando si terminaste de iniciar sesión en el navegador.', 'loading')
        browser_name = self.login_browser[0]
        events = self.events
        def verify():
            try:
                browser_login.check_connection()
                connected = browser_login.verify_browser_session(browser_name)
                events.put(('session_result', (connected, browser_name, None)))
            except Exception as error:
                events.put(('session_result', (False, browser_name, str(error))))
        threading.Thread(target=verify, daemon=True).start()

    def _refresh_session_controls(self):
        enabled = not self.is_downloading and not self.session_checking
        self.session_button.setEnabled(enabled)
        self.session_finish_button.setEnabled(enabled)
        self.download_button.setEnabled(enabled)
        self.retry_button.setEnabled(enabled and bool(self.failed_urls))
        self.shortcut.setEnabled(enabled)

    def _choose_folder(self):
        if self.is_downloading:
            return
        folder = QFileDialog.getExistingDirectory(self, 'Carpeta de destino', self.output_dir.text())
        if folder:
            self.output_dir.setText(folder)

    def _open_folder(self):
        if self.is_downloading:
            return
        value = self.output_dir.text().strip()
        folder = Path(value).expanduser() if value else None
        if not folder or not folder.is_dir():
            self._notify('La carpeta todavía no existe', 'Se creará automáticamente cuando inicies una descarga.', 'info')
            return
        QDesktopServices.openUrl(QUrl.fromLocalFile(str(folder.resolve())))

    def _open_report(self):
        if not self.is_downloading and self.report_path and Path(self.report_path).is_file():
            QDesktopServices.openUrl(QUrl.fromLocalFile(self.report_path))

    def _persist(self):
        core._save_settings({'output_dir': self.output_dir.text().strip(),
            'format': self.format_combo.currentData(), 'quality': self.quality_combo.currentText(),
            'playlist': self.playlist_check.isChecked(), 'skip_completed': self.skip_check.isChecked()})

    def _start_download(self):
        if self.is_downloading or self.session_checking:
            return
        urls = core._parse_urls(self.url_text.toPlainText())
        invalid = [url for url in urls if not core._is_youtube_url(url)]
        if not urls:
            self._notify('Añade un enlace para empezar', 'Pega un enlace de un video, Short o playlist de YouTube.', 'warning')
            self.url_text.setFocus()
            return
        if invalid:
            self._notify('Hay enlaces que no son de YouTube', 'Revisa estos enlaces: ' + ' · '.join(invalid[:3]), 'warning')
            return
        if not self.output_dir.text().strip():
            self._notify('Elige dónde guardar tus archivos', 'Pulsa Cambiar y selecciona una carpeta de destino.', 'warning')
            return
        try:
            settings = DownloadSettings(Path(self.output_dir.text().strip()).expanduser().resolve(),
                self.format_combo.currentData(), self.quality_combo.currentText(), self.playlist_check.isChecked(),
                self.skip_check.isChecked(), self.cookie_file, self.cookie_browser)
        except (OSError, ValueError) as error:
            self._log(str(error))
            self._notify('No podemos usar esa carpeta', 'Elige una carpeta existente o una ubicación donde puedas guardar archivos.')
            return
        self._begin_download(urls, settings)

    def _begin_download(self, urls, settings):
        if self.is_downloading or self.session_checking:
            return
        if core.yt_dlp is None or not core._ffmpeg_location() or not core._js_runtime():
            self._notify('La instalación está incompleta', 'Abre la versión compilada del descargador o reinstala sus componentes. Faltan herramientas de descarga o conversión.')
            return
        try:
            settings.output.mkdir(parents=True, exist_ok=True)
        except (OSError, ValueError) as error:
            self._log(str(error))
            self._notify('No podemos guardar en esa carpeta', 'Elige una carpeta donde tengas permiso para guardar archivos.')
            return
        try:
            self._persist()
        except OSError as error:
            self._log('No se guardaron las preferencias: ' + str(error))
        self.last_settings = settings
        self.failed_urls, self.job_rows = [], {}
        self.report_path = None
        self.last_error = None
        self.seen_error_codes = set()
        self.cancel_event.clear()
        self.jobs.setRowCount(0)
        self.progress_animation.stop()
        self.progress.setRange(0, 0)
        self.batch_label.setText('COMPROBANDO CONEXIÓN')
        self.status_label.setText('Preparando la descarga…')
        self.detail_label.setText('Los controles se desbloquearán cuando termine o canceles la descarga.')
        self._log(f'Nueva descarga · {core.FORMAT_NAMES[settings.media_format]} · {settings.quality}')
        self._set_busy(True)
        self._notify('Preparando tus archivos', 'Comprobando la conexión con YouTube…', 'loading')
        events, cancel = self.events, self.cancel_event
        def run():
            try:
                browser_login.check_connection()
            except Exception as error:
                events.put(('preflight_failed', str(error)))
                return
            if cancel.is_set():
                events.put(('preflight_cancelled', None))
                return
            events.put(('connection_ready', None))
            DownloadWorker(events, cancel).run(list(urls), settings)
        threading.Thread(target=run, daemon=True).start()

    def _set_busy(self, busy):
        self.is_downloading = busy
        for widget in self.controls:
            widget.setEnabled(not busy)
        self.url_text.setReadOnly(busy)
        self.report_button.setEnabled(not busy and bool(self.report_path))
        self.cancel_button.setEnabled(busy)
        self.download_button.setText('Descargando…' if busy else 'Descargar')
        self.notice.set_busy(busy)
        self._refresh_session_controls()

    def _cancel(self):
        if self.is_downloading:
            self.cancel_event.set()
            self.cancel_button.setEnabled(False)
            self.status_label.setText('Cancelando… esperando a que termine la operación actual.')

    def _retry(self):
        if not self.is_downloading and not self.session_checking and self.failed_urls and self.last_settings:
            settings = self.last_settings
            self.output_dir.setText(str(settings.output))
            self.audio_radio.setChecked(settings.media_format in core.AUDIO_FORMATS)
            self.video_radio.setChecked(settings.media_format in core.VIDEO_FORMATS)
            self.format_combo.setCurrentIndex(self.format_combo.findData(settings.media_format))
            self.quality_combo.setCurrentText(settings.quality)
            self.playlist_check.setChecked(settings.playlist)
            self.skip_check.setChecked(settings.skip_completed)
            self._begin_download(list(self.failed_urls), settings)

    def _log(self, message):
        from datetime import datetime
        self.log_text.appendPlainText(f'{datetime.now():%H:%M:%S}  {message}')

    def _process_events(self):
        for _ in range(150):
            try:
                event, value = self.events.get_nowait()
            except queue.Empty:
                break
            if event == 'session_result':
                connected, browser_name, error = value
                self.session_checking = False
                self._refresh_session_controls()
                if error:
                    self._log(error)
                    issue = describe_error(error)
                    if issue.code == 'session_locked':
                        self._notify(issue.title, issue.message, 'error')
                    else:
                        self._notify_issue(issue, self._verify_sign_in)
                elif connected:
                    self.cookie_file = ''
                    self.cookie_browser = browser_name
                    self.session_pending = False
                    self.session_finish_button.hide()
                    self.session_button.setText('YouTube conectado ✓')
                    self._notify('Tu sesión de YouTube está conectada', 'Ya puedes intentar descargar contenido al que tu cuenta tenga acceso.', 'success')
                else:
                    self._notify('Todavía no detectamos tu sesión',
                        'Termina de entrar en YouTube en el navegador que abrimos y pulsa Ya inicié sesión. No uses una ventana privada.',
                        'warning', 'Volver a comprobar', self._verify_sign_in)
            elif event in ('preflight_failed', 'preflight_cancelled'):
                self.progress_animation.stop()
                self.progress.setRange(0, 1000)
                self.progress.setValue(0)
                self._set_busy(False)
                self.batch_label.setText('SIN DESCARGAS ACTIVAS')
                if event == 'preflight_cancelled' or self.cancel_event.is_set():
                    self.status_label.setText('Descarga cancelada antes de empezar.')
                    self._notify('Descarga cancelada', 'No se han iniciado nuevas descargas.', 'info')
                else:
                    issue = describe_error(value)
                    if issue.code == 'download':
                        issue = UserError('offline', 'No pudimos conectar con YouTube', 'Comprueba tu conexión a Internet y vuelve a intentarlo.')
                    self.status_label.setText(issue.title)
                    self.detail_label.setText('No se inició la descarga. Puedes volver a intentarlo sin perder tus enlaces.')
                    self._log(str(value))
                    self._notify_issue(issue, self._start_download)
                if self.close_requested:
                    self.close()
            elif event == 'connection_ready':
                self.batch_label.setText('PREPARANDO VIDEOS')
                self._notify('Descarga en curso', 'Estamos procesando tus enlaces. Puedes cancelar si necesitas detener el lote.', 'loading')
            elif event == 'download_error':
                url, issue = value
                self.last_error = issue
                if issue.code not in self.seen_error_codes:
                    self.seen_error_codes.add(issue.code)
                    self._notify_issue(issue)
            elif event == 'log':
                self._log(str(value))
            elif event == 'status' and not self.cancel_event.is_set():
                self.status_label.setText(str(value))
                if 'FFmpeg' in str(value) or 'preparando el formato final' in str(value):
                    self.progress_animation.stop()
                    self.progress.setRange(0, 0)
            elif event == 'progress' and not self.cancel_event.is_set():
                percent, title, detail = value
                self._animate_progress(percent)
                self.status_label.setText(f'{percent:.0f}% · {title[:110]}')
                self.detail_label.setText(detail)
            elif event == 'job_add':
                index, url = value
                row = self.jobs.rowCount()
                self.jobs.insertRow(row)
                self.jobs.setItem(row, 0, QTableWidgetItem(url))
                self.jobs.setItem(row, 1, QTableWidgetItem('Pendiente'))
                self.job_rows[index] = row
            elif event == 'job':
                index, state = value
                row = self.job_rows[index]
                item = self.jobs.item(row, 1)
                item.setText(state)
                item.setForeground(QColor('#ff99ae' if state.startswith('Error') else '#97dfbd' if state.startswith('Completado') else '#f0f0f4'))
                self.jobs.scrollToItem(item)
                if state == 'Procesando':
                    self.progress_animation.stop()
                    self.progress.setRange(0, 1000)
                    self.progress.setValue(0)
            elif event == 'batch':
                self.batch_label.setText(f'{value[0]} COMPLETADOS  ·  {value[1]} FALLOS  ·  {value[2]} VIDEOS')
            elif event == 'finished':
                self.failed_urls = value['failed']
                self.report_path = value.get('report')
                self.progress_animation.stop()
                self.progress.setRange(0, 1000)
                self._set_busy(False)
                if value['cancelled']:
                    message = 'Descarga cancelada. Se conservan los archivos parciales.'
                    for row in self.job_rows.values():
                        if self.jobs.item(row, 1).text() in ('Pendiente', 'Procesando'):
                            self.jobs.item(row, 1).setText('Cancelado')
                else:
                    message = f"{value['completed']} videos completados / existentes · {len(self.failed_urls)} fallidos."
                    if not self.failed_urls:
                        self.progress.setValue(1000)
                self.status_label.setText(message)
                self.batch_label.setText('CANCELADO' if value['cancelled'] else 'FINALIZADO')
                self.detail_label.setText('TXT de fallos: ' + self.report_path if self.report_path else 'No se pudo guardar el TXT. Revisa el registro.')
                self._log(message)
                if value['cancelled']:
                    self._notify('Descarga cancelada', 'Tus archivos completados y los parciales se conservan.', 'info')
                elif self.failed_urls:
                    if self.last_error and self.last_error.code == 'authentication':
                        self.session_button.setText('Volver a iniciar sesión en YouTube')
                    issue = self.last_error or describe_error('download')
                    title = issue.title if not value['completed'] else 'Algunos videos no pudieron descargarse'
                    self._notify(title, issue.message + ' Los enlaces fallidos están en el TXT.',
                                 'warning' if value['completed'] else 'error',
                                 'Ver TXT de fallos' if self.report_path else '', self._open_report if self.report_path else None)
                else:
                    self._notify('Descarga terminada', 'Tus archivos ya están en la carpeta de destino.',
                                 'success', 'Abrir carpeta', self._open_folder)
                if self.close_requested:
                    self.close()

    def closeEvent(self, event):
        if self.is_downloading:
            answer = QMessageBox.question(self, 'Descarga en curso', '¿Cancelar y cerrar cuando termine la operación actual?')
            if answer == QMessageBox.StandardButton.Yes:
                self.close_requested = True
                self._cancel()
            event.ignore()
            return
        try:
            self._persist()
        except OSError:
            pass
        event.accept()


def main():
    application = QApplication(sys.argv)
    application.setApplicationName('Descargador')
    application.setApplicationVersion(__version__)
    application.setStyle('Fusion')
    window = DescargadorApp()
    if '--check' in sys.argv:
        if core.yt_dlp is None or core._ffmpeg_location() is None or window.windowIcon().isNull() or not core._js_runtime():
            raise RuntimeError('Faltan dependencias, logo o motor JavaScript')
        location = Path(core._ffmpeg_location())
        for name in ('ffmpeg', 'ffprobe'):
            binary = location / (name + '.exe' if sys.platform == 'win32' else name)
            subprocess.run([str(binary), '-version'], check=True, capture_output=True, timeout=15,
                           creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
        name, runtime = next(iter(core._js_runtime().items()))
        subprocess.run([runtime['path'], '--version'], check=True, capture_output=True, timeout=15,
                       creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
        return
    window.show()
    sys.exit(application.exec())


if __name__ == '__main__':
    main()
