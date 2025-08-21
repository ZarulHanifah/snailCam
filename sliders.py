
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QPainter, QPalette
from PyQt5.QtWidgets import (QApplication, QCheckBox, QComboBox,
                             QDoubleSpinBox, QFormLayout, QHBoxLayout, QLabel,
                             QLineEdit, QPushButton, QSlider, QSpinBox,
                             QTabWidget, QVBoxLayout, QWidget)

import numpy as np

class logControlSlider(QWidget):
    def __init__(self):
        super().__init__()
        self.layout = QHBoxLayout()
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.setLayout(self.layout)

        self.slider = QSlider(Qt.Horizontal)
        self.box = QDoubleSpinBox()

        self.valueChanged = self.box.valueChanged
        self.valueChanged.connect(lambda: self.setValue(self.value()))
        self.slider.valueChanged.connect(self.updateValue)

        self.layout.addWidget(self.box)
        self.layout.addWidget(self.slider)

        self.precision = self.box.singleStep()
        self.slider.setSingleStep(1)
        self.minimum = 0.0
        self.maximum = 2.0

    @property
    def points(self):
        return int(1.0 / self.precision) * 2

    def boxToSlider(self, val=None):
        if val is None:
            val = self.box.value()
        if val == 0:
            return 0
        else:
            center = self.points // 2
            scaling = center / np.log2(self.maximum)
            return round(np.log2(val) * scaling) + center

    def sliderToBox(self, val=None):
        if val is None:
            val = self.slider.value()
        if val == 0:
            return 0
        else:
            center = self.points // 2
            scaling = center / np.log2(self.maximum)
            return round(2**((val - center) / scaling), int(-np.log10(self.precision)))

    def updateValue(self):
        self.blockAllSignals(True)
        if self.box.value() != self.sliderToBox():
            self.box.setValue(self.sliderToBox())
        self.blockAllSignals(False)
        self.valueChanged.emit(self.value())

    def redrawSlider(self):
        self.slider.setMinimum(0)
        self.slider.setMaximum(self.points)
        self.slider.setValue(self.boxToSlider())

    def setSingleStep(self, val):
        self.box.setSingleStep(val)
        self.precision = val

    def setValue(self, val, emit=False):
        self.blockAllSignals(True)
        self.box.setValue(val)
        self.redrawSlider()
        self.blockAllSignals(False)
        if emit:
            self.valueChanged.emit(self.value())

    def setMinimum(self, val):
        self.box.setMinimum(val)
        self.minimum = val
        self.redrawSlider()

    def setMaximum(self, val):
        self.box.setMaximum(val)
        self.maximum = val
        self.redrawSlider()

    def blockAllSignals(self, y):
        self.box.blockSignals(y)
        self.slider.blockSignals(y)

    def value(self):
        return self.box.value()


class controlSlider(QWidget):
    def __init__(self, box_type=float):
        super().__init__()
        self.layout = QHBoxLayout()
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.setLayout(self.layout)

        self.slider = QSlider(Qt.Horizontal)
        if box_type == float:
            self.box = QDoubleSpinBox()
        else:
            self.box = QSpinBox()

        self.valueChanged = self.box.valueChanged
        self.valueChanged.connect(lambda: self.setValue(self.value()))
        self.slider.valueChanged.connect(self.updateValue)

        self.layout.addWidget(self.box)
        self.layout.addWidget(self.slider)

        self.precision = self.box.singleStep()
        self.slider.setSingleStep(1)

    def updateValue(self):
        self.blockAllSignals(True)
        if self.box.value() != self.slider.value() * self.precision:
            self.box.setValue(self.slider.value() * self.precision)
        self.blockAllSignals(False)
        self.valueChanged.emit(self.value())

    def setSingleStep(self, val):
        self.box.setSingleStep(val)
        self.precision = val

    def setValue(self, val, emit=False):
        self.blockAllSignals(True)
        if val is None:
            val = 0
        self.box.setValue(val)
        self.slider.setValue(int(val / self.precision))
        self.blockAllSignals(False)
        if emit:
            self.valueChanged.emit(self.value())

    def setMinimum(self, val):
        self.box.setMinimum(val)
        self.slider.setMinimum(int(val / self.precision))

    def setMaximum(self, val):
        self.box.setMaximum(val)
        self.slider.setMaximum(int(val / self.precision))

    def blockAllSignals(self, y):
        self.box.blockSignals(y)
        self.slider.blockSignals(y)

    def value(self):
        return self.box.value()

