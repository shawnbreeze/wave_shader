import sys
import numpy as np
from PIL import Image
from PySide6.QtWidgets import QApplication, QMainWindow, QGraphicsView, QGraphicsScene
from PySide6.QtGui import QImage, QPainter, QPen, QColor
from PySide6.QtCore import Qt, QLineF, QPointF, QPoint


class WaveformWindow(QMainWindow):
    def __init__(self, texture_path):
        super().__init__()
        self.setWindowTitle("Waveform Debug View")
        self.resize(800, 400)
        self.texture_path = texture_path
        self.waveform_data = []
        self.scene = None
        self.view = None
        self.initUI()
        self.loadWaveformData()

    def initUI(self):
        self.scene = QGraphicsScene()
        self.view = QGraphicsView(self.scene)
        self.view.setRenderHint(QPainter.Antialiasing)
        self.view.setAlignment(Qt.AlignLeft | Qt.AlignTop)
        self.setCentralWidget(self.view)
        self.updateWaveform()

    def srgb_to_linear(self, v: int) -> float:
        return v
        """ Convert from sRGB (0-255) to linear [0.0; 1.0] using IEC 61966-2-1. """
        v = v / 255.0
        if v <= 0.04045:
            return v / 12.92
        return ((v + 0.055) / 1.055) ** 2.4

    def loadWaveformData(self):
        image = QImage(self.texture_path)
        if image.isNull():
            raise RuntimeError("Failed to load texture")

        w, h = image.width(), image.height()
        if h < 1:
            raise RuntimeError("Texture must be at least 1 pixel tall")

        # Access data via memoryview
        ptr = image.constBits()  # Pointer to data as memoryview
        bytes_per_line = image.bytesPerLine()

        self.waveform_data.clear()
        for y in range(h):
            for x in range(w):
                # Offset for pixel (y, x)
                offset = y * bytes_per_line + x * 4

                # Extract components (order BGRA)
                blue = ptr[offset]
                green = ptr[offset + 1]
                red = ptr[offset + 2]
                alpha = ptr[offset + 3]

                # Convert to linear range [-1.0, 1.0]
                r = (red / 255) * 2.0 - 1.0
                g = (green / 255) * 2.0 - 1.0
                b = (blue / 255) * 2.0 - 1.0
                a = (alpha / 255) * 2.0 - 1.0

                self.waveform_data.append((r, g, b, a))

    def updateWaveform(self):
        if not self.waveform_data:
            return

        self.scene.clear()
        w = len(self.waveform_data)
        current_height = self.height()
        self.scene.setSceneRect(0, 0, w, current_height)

        # Draw grid
        grid_pen = QPen(QColor(230, 230, 230), 1, Qt.DotLine)
        for y in range(0, current_height + 1, 20):
            self.scene.addLine(0, y, w, y, grid_pen)

        amp = 100
        baseL = current_height * 0.25   # Left channel (blue)
        baseR = current_height * 0.75   # Right channel (red)

        pen_left = QPen(QColor("blue"), 1.5)
        pen_right = QPen(QColor("red"),  1.5)

        for x in range(w):
            rMin, rMax, lMin, lMax = self.waveform_data[x]

            # Left channel (B/A)
            y_l1 = baseL + (1.0 - lMin) * amp
            y_l2 = baseL + (1.0 - lMax) * amp
            self.scene.addLine(x, y_l1, x, y_l2, pen_left)

            # Right channel (R/G)
            y_r1 = baseR + (1.0 - rMin) * amp
            y_r2 = baseR + (1.0 - rMax) * amp
            self.scene.addLine(x, y_r1, x, y_r2, pen_right)

        self.view.fitInView(self.scene.sceneRect(),
                            Qt.AspectRatioMode.IgnoreAspectRatio)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.updateWaveform()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = WaveformWindow("w.png")
    window.show()
    sys.exit(app.exec())
