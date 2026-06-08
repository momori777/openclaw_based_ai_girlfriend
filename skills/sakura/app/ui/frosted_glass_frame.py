from __future__ import annotations

from PySide6.QtCore import QPoint, QRectF, Qt
from PySide6.QtGui import QColor, QPainter, QPainterPath, QPixmap
from PySide6.QtWidgets import (
    QFrame,
    QGraphicsBlurEffect,
    QGraphicsPixmapItem,
    QGraphicsScene,
    QWidget,
)


class FrostedGlassFrame(QFrame):
    """绘制带高斯模糊取样的半透明文本框遮罩。"""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._source_widgets: tuple[QWidget, ...] = ()
        self._blur_radius = 18.0
        self._corner_radius = 19.0
        self._tint = QColor(255, 255, 255, 92)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

    def set_source_widgets(self, widgets: tuple[QWidget, ...]) -> None:
        self._source_widgets = widgets

    def paintEvent(self, event) -> None:  # type: ignore[no-untyped-def]
        del event
        source = QPixmap(self.size())
        source.fill(Qt.GlobalColor.transparent)

        source_painter = QPainter(source)
        for widget in self._source_widgets:
            if widget.isVisible():
                widget_origin = self.mapFromGlobal(widget.mapToGlobal(QPoint(0, 0)))
                widget.render(source_painter, widget_origin)
        source_painter.end()

        blurred = _blur_pixmap(source, self._blur_radius)

        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        rect = QRectF(self.rect()).adjusted(0.5, 0.5, -0.5, -0.5)
        path = QPainterPath()
        path.addRoundedRect(rect, self._corner_radius, self._corner_radius)

        painter.setClipPath(path)
        painter.drawPixmap(0, 0, blurred)
        painter.fillPath(path, self._tint)
        painter.end()


def _blur_pixmap(pixmap: QPixmap, radius: float) -> QPixmap:
    if pixmap.isNull() or radius <= 0:
        return pixmap

    scene = QGraphicsScene()
    item = QGraphicsPixmapItem(pixmap)
    effect = QGraphicsBlurEffect()
    effect.setBlurRadius(radius)
    effect.setBlurHints(QGraphicsBlurEffect.BlurHint.QualityHint)
    item.setGraphicsEffect(effect)
    scene.addItem(item)
    scene.setSceneRect(QRectF(pixmap.rect()))

    result = QPixmap(pixmap.size())
    result.fill(Qt.GlobalColor.transparent)
    painter = QPainter(result)
    scene.render(painter, QRectF(result.rect()), QRectF(pixmap.rect()))
    painter.end()
    return result
