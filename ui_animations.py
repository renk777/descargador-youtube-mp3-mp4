"""Small, local animations: buttons, inline notices and activity symbols."""
from PySide6.QtCore import QEasingCurve, QParallelAnimationGroup, Property, QPropertyAnimation, QTimer, Qt
from PySide6.QtGui import QColor, QPainter, QPen
from PySide6.QtWidgets import QFrame, QGraphicsOpacityEffect, QHBoxLayout, QLabel, QPushButton, QVBoxLayout, QWidget


class AnimatedButton(QPushButton):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._hover = 0.0
        self.hover_animation = QPropertyAnimation(self, b'hoverAmount', self)
        self.hover_animation.setDuration(140)
        self.hover_animation.setEasingCurve(QEasingCurve.Type.OutCubic)

    @Property(float)
    def hoverAmount(self):
        return self._hover

    @hoverAmount.setter
    def hoverAmount(self, value):
        self._hover = value
        self.update()

    def _animate(self, target):
        self.hover_animation.stop()
        self.hover_animation.setStartValue(self._hover)
        self.hover_animation.setEndValue(target)
        self.hover_animation.start()

    def enterEvent(self, event):
        if self.isEnabled():
            self._animate(1.0)
        super().enterEvent(event)

    def leaveEvent(self, event):
        self._animate(0.0)
        super().leaveEvent(event)

    def paintEvent(self, event):
        super().paintEvent(event)
        if self.isEnabled() and self._hover > 0:
            painter = QPainter(self)
            painter.setRenderHint(QPainter.RenderHint.Antialiasing)
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QColor(255, 255, 255, round(17 * self._hover)))
            painter.drawRoundedRect(self.rect().adjusted(1, 1, -1, -1), 7, 7)


class AnimatedMark(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(32, 32)
        self.kind, self.angle = 'info', 0
        self.phase = 0.0
        self.timer = QTimer(self)
        self.timer.setInterval(30)
        self.timer.timeout.connect(self._tick)

    def set_kind(self, kind):
        self.kind, self.phase, self.angle = kind, 0.0, 0
        self.timer.start()
        self.update()

    def _tick(self):
        self.phase = min(1, self.phase + 0.08)
        self.angle = (self.angle + 12) % 360
        self.update()
        if not self.isVisible() or (self.kind != 'loading' and self.phase >= 1):
            self.timer.stop()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        color = QColor({'error': '#ff9eb4', 'warning': '#f0c58a', 'success': '#8ee1b6',
                        'loading': '#d8b3f4'}.get(self.kind, '#bfcaef'))
        painter.translate(16, 16)
        scale = 0.8 + 0.2 * self.phase
        painter.scale(scale, scale)
        painter.translate(-16, -16)
        painter.setPen(QPen(color, 2.1, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin))
        if self.kind == 'loading':
            painter.drawArc(5, 5, 22, 22, self.angle * 16, 250 * 16)
            return
        fill = QColor(color)
        fill.setAlpha(22)
        painter.setBrush(fill)
        painter.drawEllipse(3, 3, 26, 26)
        if self.kind == 'success':
            painter.drawLine(9, 16, 14, 21)
            painter.drawLine(14, 21, 23, 11)
        else:
            painter.drawLine(16, 9, 16, 17)
            painter.drawPoint(16, 23)


class NoticeBar(QFrame):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName('notice')
        self.setStyleSheet('QFrame#notice { background: rgba(35,32,45,235); border: 1px solid #685067; border-radius: 9px; }')
        self.busy = False
        row = QHBoxLayout(self)
        row.setContentsMargins(12, 9, 10, 9)
        self.mark = AnimatedMark()
        row.addWidget(self.mark)
        text = QVBoxLayout()
        text.setSpacing(3)
        self.title = QLabel()
        self.title.setStyleSheet('font-weight: 600; background: transparent; border: none;')
        self.body = QLabel()
        self.body.setWordWrap(True)
        self.body.setStyleSheet('color: #d0c9d6; font-size: 12px; background: transparent; border: none;')
        text.addWidget(self.title)
        text.addWidget(self.body)
        row.addLayout(text, 1)
        self.action = AnimatedButton()
        self.action.hide()
        self.callback = None
        self.action.clicked.connect(self._trigger)
        row.addWidget(self.action)
        self.dismiss = AnimatedButton('×')
        self.dismiss.setFixedWidth(32)
        self.dismiss.clicked.connect(self.hide_animated)
        row.addWidget(self.dismiss)
        self.effect = QGraphicsOpacityEffect(self)
        self.setGraphicsEffect(self.effect)
        self.animation = QParallelAnimationGroup(self)
        self.height_animation = QPropertyAnimation(self, b'maximumHeight', self.animation)
        self.opacity_animation = QPropertyAnimation(self.effect, b'opacity', self.animation)
        for animation in (self.height_animation, self.opacity_animation):
            animation.setDuration(230)
            animation.setEasingCurve(QEasingCurve.Type.OutCubic)
            self.animation.addAnimation(animation)
        self.animation.finished.connect(self._finished)
        self.hiding = False
        self.hide()

    def show_message(self, title, body, kind='info', action_text='', callback=None):
        was_visible = self.isVisible()
        self.animation.stop()
        self.hiding = False
        self.title.setText(title)
        self.body.setText(body)
        self.callback = callback
        self.action.setText(action_text)
        self.action.setVisible(bool(action_text and callback))
        self.action.setEnabled(not self.busy)
        self.dismiss.setEnabled(not self.busy)
        self.show()
        self.mark.set_kind(kind)
        self.setMaximumHeight(16777215)
        measured = self.layout().heightForWidth(max(300, self.width()))
        target = max(65, measured if measured > 0 else self.sizeHint().height())
        self.height_animation.setStartValue(min(self.height(), target) if was_visible else 0)
        self.height_animation.setEndValue(target)
        self.opacity_animation.setStartValue(self.effect.opacity() if was_visible else 0.0)
        self.opacity_animation.setEndValue(1.0)
        self.animation.start()

    def set_busy(self, busy):
        self.busy = busy
        self.action.setEnabled(not busy)
        self.dismiss.setEnabled(not busy)

    def hide_animated(self):
        self.animation.stop()
        self.hiding = True
        self.height_animation.setStartValue(self.height())
        self.height_animation.setEndValue(0)
        self.opacity_animation.setStartValue(self.effect.opacity())
        self.opacity_animation.setEndValue(0.0)
        self.animation.start()

    def _finished(self):
        if self.hiding:
            self.hide()
        else:
            self.setMaximumHeight(16777215)

    def _trigger(self):
        if self.callback and not self.busy:
            self.callback()
