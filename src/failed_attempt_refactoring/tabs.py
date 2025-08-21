
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QPainter, QPalette
from PyQt5.QtWidgets import (QApplication, QCheckBox, QComboBox,
                             QDoubleSpinBox, QFormLayout, QHBoxLayout, QLabel,
                             QLineEdit, QPushButton, QSlider, QSpinBox,
                             QTabWidget, QVBoxLayout, QWidget)

from sliders import logControlSlider, controlSlider
from config import implemented_controls, ignore_controls, still_kwargs

try:
    import cv2
    cv_present = True
except ImportError:
    cv_present = False
    print("OpenCV not found - HDR not available")

hide_button = QPushButton(">")
hide_button.clicked.connect(toggle_hidden_controls)
hide_button.setMaximumSize(50, 400)

class panTab(QWidget):
    def __init__(self, picam2):
        super().__init__()
        self.picam2 = picam2
        # Pan/Zoom
        self.layout = QFormLayout()
        self.setLayout(self.layout)

        self.label = QLabel((
            "Pan and Zoom Controls\n"
            "To zoom in/out, scroll up/down in the display below\n"
            "To pan, click and drag in the display below"),
            alignment=Qt.AlignCenter)
        self.zoom_text = QLabel("Current Zoom Level: 1.0", alignment=Qt.AlignCenter)
        self.pan_display = panZoomDisplay(self.picam2)
        self.pan_display.updated.connect(lambda: self.zoom_text.setText(
            f"Current Zoom Level: {self.pan_display.zoom_level:.1f}x"))

        self.layout.addRow(self.label)
        self.layout.addRow(self.zoom_text)
        self.layout.addRow(self.pan_display)
        self.layout.setAlignment(self.pan_display, Qt.AlignCenter)


class panZoomDisplay(QWidget):
    updated = pyqtSignal()

    def __init__(self, picam2):
        super().__init__()
        self.picam2 = picam2
        self.setMinimumSize(201, 151)
        _, full_img, _ = self.picam2.camera_controls['ScalerCrop']
        self.scale = 200 / full_img[2]
        self.zoom_level_ = 1.0
        self.max_zoom = 7.0
        self.zoom_step = 0.1

    @property
    def zoom_level(self):
        return self.zoom_level_

    @zoom_level.setter
    def zoom_level(self, val):
        if val != self.zoom_level:
            self.zoom_level_ = val
            self.setZoom()

    def setZoomLevel(self, val):
        self.zoom_level = val

    def paintEvent(self, event):
        painter = QPainter()
        painter.begin(self)
        _, full_img, _ = self.picam2.camera_controls['ScalerCrop']
        self.scale = 200 / full_img[2]
        # Whole frame
        scaled_full_img = [int(i * self.scale) for i in full_img]
        origin = scaled_full_img[:2]
        scaled_full_img[:2] = [0, 0]
        painter.drawRect(*scaled_full_img)
        # Cropped section
        scaled_scaler_crop = [int(i * self.scale) for i in scaler_crop]
        scaled_scaler_crop[0] -= origin[0]
        scaled_scaler_crop[1] -= origin[1]
        painter.drawRect(*scaled_scaler_crop)
        painter.end()
        self.updated.emit()

    def draw_centered(self, pos):
        global scaler_crop
        center = [int(i / self.scale) for i in pos]
        _, full_img, _ = self.picam2.camera_controls['ScalerCrop']
        w = scaler_crop[2]
        h = scaler_crop[3]
        x = center[0] - w // 2 + full_img[0]
        y = center[1] - h // 2 + full_img[1]
        new_scaler_crop = [x, y, w, h]

        # Check still within bounds
        new_scaler_crop[1] = max(new_scaler_crop[1], full_img[1])
        new_scaler_crop[1] = min(new_scaler_crop[1], full_img[1] + full_img[3] - new_scaler_crop[3])
        new_scaler_crop[0] = max(new_scaler_crop[0], full_img[0])
        new_scaler_crop[0] = min(new_scaler_crop[0], full_img[0] + full_img[2] - new_scaler_crop[2])
        scaler_crop = tuple(new_scaler_crop)
        self.picam2.controls.ScalerCrop = scaler_crop
        self.update()

    def mouseMoveEvent(self, event):
        pos = event.pos()
        pos = (pos.x(), pos.y())
        self.draw_centered(pos)

    def setZoom(self):
        global scaler_crop
        if self.zoom_level < 1:
            self.zoom_level = 1.0
        if self.zoom_level > self.max_zoom:
            self.zoom_level = self.max_zoom
        factor = 1.0 / self.zoom_level
        _, full_img, _ = self.picam2.camera_controls['ScalerCrop']
        current_center = (scaler_crop[0] + scaler_crop[2] // 2, scaler_crop[1] + scaler_crop[3] // 2)
        w = int(factor * full_img[2])
        h = int(factor * full_img[3])
        x = current_center[0] - w // 2
        y = current_center[1] - h // 2
        new_scaler_crop = [x, y, w, h]
        # Check still within bounds
        new_scaler_crop[1] = max(new_scaler_crop[1], full_img[1])
        new_scaler_crop[1] = min(new_scaler_crop[1], full_img[1] + full_img[3] - new_scaler_crop[3])
        new_scaler_crop[0] = max(new_scaler_crop[0], full_img[0])
        new_scaler_crop[0] = min(new_scaler_crop[0], full_img[0] + full_img[2] - new_scaler_crop[2])
        scaler_crop = tuple(new_scaler_crop)
        self.picam2.controls.ScalerCrop = scaler_crop
        self.update()

    def wheelEvent(self, event):
        zoom_dir = np.sign(event.angleDelta().y())
        self.zoom_level += zoom_dir * self.zoom_step
        self.setZoom()
        # If desired then also center the zoom on the pointer
        # self.draw_centered((event.position().x(), event.position().y()))


class AECTab(QWidget):
    def __init__(self, picam2):
        super().__init__()
        self.picam2 = picam2
        self.layout = QFormLayout()
        self.setLayout(self.layout)

        self.aec_check = QCheckBox("AEC")
        self.aec_check.setChecked(True)
        self.aec_check.stateChanged.connect(self.aec_update)
        self.aec_meter = QComboBox()
        self.aec_meter.addItems(["Centre Weighted", "Spot", "Matrix"])
        self.aec_meter.currentIndexChanged.connect(self.aec_update)
        self.aec_constraint = QComboBox()
        self.aec_constraint.addItems(["Default", "Highlight"])
        self.aec_constraint.currentIndexChanged.connect(self.aec_update)
        self.aec_exposure = QComboBox()
        self.aec_exposure.addItems(["Normal", "Short", "Long"])
        self.aec_exposure.currentIndexChanged.connect(self.aec_update)
        self.exposure_val = controlSlider()
        self.exposure_val.valueChanged.connect(self.aec_update)
        self.exposure_val.setSingleStep(0.1)
        self.exposure_time = QSpinBox()
        self.exposure_time.setSingleStep(1000)
        self.analogue_gain = QDoubleSpinBox()
        self.analogue_label = QLabel()
        self.aec_apply = QPushButton("Apply Manual Values")
        self.aec_apply.setEnabled(False)
        self.aec_apply.clicked.connect(self.aec_manual_update)
        self.exposure_time.valueChanged.connect(lambda: self.aec_apply.setEnabled(self.exposure_time.isEnabled()))
        self.analogue_gain.valueChanged.connect(lambda: self.aec_apply.setEnabled(self.exposure_time.isEnabled()))

        self.awb_check = QCheckBox("AWB")
        self.awb_check.setChecked(True)
        self.awb_check.stateChanged.connect(self.awb_update)
        self.awb_mode = QComboBox()
        self.awb_mode.addItems([
            "Auto", "Incandescent", "Tungsten", "Fluorescent",
            "Indoor", "Daylight", "Cloudy"
        ])
        self.awb_mode.currentIndexChanged.connect(self.awb_update)
        self.colour_gain_r = QDoubleSpinBox()
        self.colour_gain_r.setSingleStep(0.1)
        self.colour_gain_r.valueChanged.connect(self.awb_update)
        self.colour_gain_b = QDoubleSpinBox()
        self.colour_gain_b.setSingleStep(0.1)
        self.colour_gain_b.valueChanged.connect(self.awb_update)

        self.reset()
        self.aec_update()
        self.awb_update()
        self.aec_apply.setEnabled(False)

        self.layout.addRow(self.aec_check)
        self.layout.addRow("AEC Metering Mode", self.aec_meter)
        self.layout.addRow("AEC Constraint Mode", self.aec_constraint)
        self.layout.addRow("AEC Exposure Mode", self.aec_exposure)
        self.layout.addRow("Exposure Value", self.exposure_val)
        self.layout.addRow("Exposure Time/\u03bcs", self.exposure_time)
        self.layout.addRow("Gain", self.analogue_gain)
        self.layout.addRow(self.analogue_label)
        self.layout.addRow(self.aec_apply)

        self.layout.addRow(self.awb_check)
        self.layout.addRow("AWB Mode", self.awb_mode)
        self.layout.addRow("Red Gain", self.colour_gain_r)
        self.layout.addRow("Blue Gain", self.colour_gain_b)

    def reset(self):
        self.aec_check.setChecked(True)
        self.awb_check.setChecked(True)
        self.exposure_time.setValue(10000)
        self.analogue_gain.setValue(1.0)
        self.colour_gain_r.setValue(1.0)
        self.colour_gain_b.setValue(1.0)

    @property
    def aec_dict(self):
        ret = {
            "AeEnable": self.aec_check.isChecked(),
            "AeMeteringMode": self.aec_meter.currentIndex(),
            "AeConstraintMode": self.aec_constraint.currentIndex(),
            "AeExposureMode": self.aec_exposure.currentIndex(),
            "ExposureValue": self.exposure_val.value(),
            "ExposureTime": self.exposure_time.value(),
            "AnalogueGain": self.analogue_gain.value()
        }
        if self.aec_check.isChecked():
            del ret["ExposureTime"]
            del ret["AnalogueGain"]
        return ret

    def aec_update(self):
        self.exposure_val.setMinimum(self.picam2.camera_controls["ExposureValue"][0])
        self.exposure_val.setMaximum(self.picam2.camera_controls["ExposureValue"][1])
        self.exposure_time.setMinimum(self.picam2.camera_controls["ExposureTime"][0])
        self.exposure_time.setMaximum(self.picam2.camera_controls["ExposureTime"][1])
        self.analogue_gain.setMinimum(self.picam2.camera_controls["AnalogueGain"][0])
        self.analogue_label.setText(f"Analogue up to {self.picam2.camera_controls['AnalogueGain'][1]:.2f}, then digital beyond")

        self.aec_meter.setEnabled(self.aec_check.isChecked())
        self.aec_constraint.setEnabled(self.aec_check.isChecked())
        self.aec_exposure.setEnabled(self.aec_check.isChecked())
        self.exposure_val.setEnabled(self.aec_check.isChecked())
        self.exposure_time.setEnabled(not self.aec_check.isChecked())
        self.analogue_gain.setEnabled(not self.aec_check.isChecked())
        if self.aec_check.isChecked():
            self.aec_apply.setEnabled(False)
        # print(self.aec_dict)
        self.picam2.set_controls(self.aec_dict)

    def aec_manual_update(self):
        if not self.aec_check.isChecked():
            self.aec_update()
        self.aec_apply.setEnabled(False)

    @property
    def awb_dict(self):
        ret = {
            "AwbEnable": self.awb_check.isChecked(),
            "AwbMode": self.awb_mode.currentIndex(),
            "ColourGains": [self.colour_gain_r.value(), self.colour_gain_b.value()]
        }
        if self.awb_check.isChecked():
            del ret["ColourGains"]
        return ret

    def awb_update(self):
        self.colour_gain_r.setMinimum(self.picam2.camera_controls["ColourGains"][0] + 0.01)
        self.colour_gain_r.setMaximum(self.picam2.camera_controls["ColourGains"][1])
        self.colour_gain_b.setMinimum(self.picam2.camera_controls["ColourGains"][0] + 0.01)
        self.colour_gain_b.setMaximum(self.picam2.camera_controls["ColourGains"][1])

        self.colour_gain_r.setEnabled(not self.awb_check.isChecked())
        self.colour_gain_b.setEnabled(not self.awb_check.isChecked())
        # print(self.awb_dict)
        self.picam2.set_controls(self.awb_dict)


class IMGTab(QWidget):
    def __init__(self, picam2):
        super().__init__()
        self.picam2 = picam2
        self.layout = QFormLayout()
        self.setLayout(self.layout)

        self.ccm = QDoubleSpinBox()
        self.ccm.valueChanged.connect(self.img_update)
        self.saturation = logControlSlider()
        self.saturation.valueChanged.connect(self.img_update)
        self.saturation.setSingleStep(0.1)
        self.contrast = logControlSlider()
        self.contrast.valueChanged.connect(self.img_update)
        self.contrast.setSingleStep(0.1)
        self.sharpness = logControlSlider()
        self.sharpness.valueChanged.connect(self.img_update)
        self.sharpness.setSingleStep(0.1)
        self.brightness = controlSlider()
        self.brightness.setSingleStep(0.1)
        self.brightness.valueChanged.connect(self.img_update)
        self.noise_reduction = QComboBox()
        self.noise_reduction.addItems(["Off", "Fast", "High Quality", "Minimal", "ZSL"])
        self.noise_reduction.currentIndexChanged.connect(self.img_update)
        self.reset_button = QPushButton("Reset")
        self.reset_button.clicked.connect(self.reset)

        self.reset()
        self.img_update()

        # self.layout.addRow("Colour Correction Matrix", self.ccm)
        self.layout.addRow("Saturation", self.saturation)
        self.layout.addRow("Contrast", self.contrast)
        self.layout.addRow("Sharpness", self.sharpness)
        self.layout.addRow("Brightness", self.brightness)
        # self.layout.addRow("Noise Reduction Mode", self.noise_reduction)
        self.layout.addRow(self.reset_button)

    @property
    def img_dict(self):
        return {
            # "ColourCorrectionMatrix": self.ccm.value(),
            "Saturation": self.saturation.value(),
            "Contrast": self.contrast.value(),
            "Sharpness": self.sharpness.value(),
            "Brightness": self.brightness.value(),
            # "NoiseReductionMode": self.noise_reduction.currentIndex()
        }

    def reset(self):
        # self.ccm.setValue(picam2.camera_controls["ColourCorrectionMatrix"][2])
        self.saturation.setValue(self.picam2.camera_controls["Saturation"][2], emit=True)
        self.contrast.setValue(self.picam2.camera_controls["Contrast"][2], emit=True)
        self.sharpness.setValue(self.picam2.camera_controls["Sharpness"][2], emit=True)
        self.brightness.setValue(self.picam2.camera_controls["Brightness"][2], emit=True)

    def img_update(self):
        # self.ccm.setMinimum(self.picam2.camera_controls["ColourCorrectionMatrix"][0])
        # self.ccm.setMaximum(self.picam2.camera_controls["ColourCorrectionMatrix"][1])
        self.saturation.setMinimum(self.picam2.camera_controls["Saturation"][0])
        # self.saturation.setMaximum(self.picam2.camera_controls["Saturation"][1])
        self.saturation.setMaximum(6.0)
        self.contrast.setMinimum(self.picam2.camera_controls["Contrast"][0])
        # self.contrast.setMaximum(self.picam2.camera_controls["Contrast"][1])
        self.contrast.setMaximum(6.0)
        self.sharpness.setMinimum(self.picam2.camera_controls["Sharpness"][0])
        self.sharpness.setMaximum(self.picam2.camera_controls["Sharpness"][1])
        self.brightness.setMinimum(self.picam2.camera_controls["Brightness"][0])
        self.brightness.setMaximum(self.picam2.camera_controls["Brightness"][1])

        # print(self.img_dict)
        self.picam2.set_controls(self.img_dict)


class otherTab(QWidget):
    # Should capture any other camera controls
    def __init__(self, picam2):
        super().__init__()
        self.picam2 = picam2
        self.layout = QFormLayout()
        self.setLayout(self.layout)

        global implemented_controls, ignore_controls  # noqa
        all_controls = self.picam2.camera_controls.keys()
        other_controls = []
        for control in all_controls:
            if control not in implemented_controls and control not in ignore_controls:
                other_controls.append(control)
        self.fields = {}
        for control in other_controls:
            widget = controlSlider(box_type=type(self.picam2.camera_controls[control][0]))
            widget.setMinimum(self.picam2.camera_controls[control][0])
            widget.setMaximum(self.picam2.camera_controls[control][1])
            widget.setValue(self.picam2.camera_controls[control][2])
            widget.valueChanged.connect(self.other_update)
            self.fields[control] = widget

        for k, v in self.fields.items():
            self.layout.addRow(k, v)

        print("Other controls", other_controls)

    @property
    def other_dict(self):
        ret = {}
        for k, v in self.fields.items():
            ret[k] = v.value()
        return ret

    def other_update(self):
        self.picam2.set_controls(self.other_dict)


class vidTab(QWidget):
    def __init__(self, picam2):
        super().__init__()
        self.picam2 = picam2
        self.layout = QFormLayout()
        self.setLayout(self.layout)
        self.filename = QLineEdit()
        self.filetype = QComboBox()
        self.filetype.addItems(["mp4", "mkv", "ts", "mov", "avi", "h264"])
        self.quality_box = QComboBox()
        self.quality_box.addItems(["Very Low", "Low", "Medium", "High", "Very High"])
        self.framerate = QSpinBox()
        self.framerate.valueChanged.connect(self.vid_update)
        self.framerate.setMinimum(1)
        self.framerate.setMaximum(500)
        self.actual_framerate = QLabel()
        self.resolution_w = QSpinBox()
        self.resolution_w.setMaximum(self.picam2.sensor_resolution[0])
        self.resolution_h = QSpinBox()
        # Max height is 1080 for the encoder to still work
        self.resolution_h.setMaximum(min(self.picam2.sensor_resolution[1], 1080))
        self.raw_format = QComboBox()
        self.raw_format.addItem("Default")
        self.raw_format.addItems([f'{x["format"].format} {x["size"]}, {x["fps"]:.0f}fps' for x in self.picam2.sensor_modes])
        self.apply_button = QPushButton("Apply")
        self.apply_button.clicked.connect(self.apply_settings)

        # Cosmetic additions
        resolution = QWidget()
        res_layout = QHBoxLayout()
        res_layout.addWidget(self.resolution_w)
        res_layout.addWidget(QLabel("x"), alignment=Qt.AlignHCenter)
        res_layout.addWidget(self.resolution_h)
        resolution.setLayout(res_layout)

        # Add the rows
        self.layout.addRow("Name", self.filename)
        self.layout.addRow("File Type", self.filetype)
        self.layout.addRow("Quality", self.quality_box)
        self.layout.addRow("Frame Rate", self.framerate)
        self.layout.addRow(self.actual_framerate)
        self.layout.addRow("Resolution", resolution)
        self.layout.addRow("Sensor Mode", self.raw_format)

        self.layout.addRow(self.apply_button)

        self.reset()

    @property
    def quality(self):
        qualities = {
            "Very Low": Quality.VERY_LOW,
            "Low": Quality.LOW,
            "Medium": Quality.MEDIUM,
            "High": Quality.HIGH,
            "Very High": Quality.VERY_HIGH
        }
        return qualities[self.quality_box.currentText()]

    @property
    def sensor_mode(self):
        configs = [None]
        for mode in self.picam2.sensor_modes:
            configs.append({"size": mode["size"], "format": mode["format"].format})
        return configs[self.raw_format.currentIndex()]

    @property
    def frametime(self):
        return self.frametime_

    @frametime.setter
    def frametime(self, value):
        self.frametime_ = value
        self.actual_framerate.setText(f"Actual Framerate: {1e6 / self.frametime:.1f}fps")

    @property
    def vid_dict(self):
        return {
            "FrameRate": self.framerate.value()
        }

    def vid_update(self):
        if self.isVisible():
            self.picam2.set_controls(self.vid_dict)
        else:
            print("Not setting vid controls when not visible")

    def reset(self):
        self.quality_box.setCurrentIndex(2)
        self.framerate.setValue(30)
        self.resolution_h.setValue(720)
        self.resolution_w.setValue(1280)
        self.picam2.video_configuration = self.picam2.create_video_configuration(
            main={"size": (self.resolution_w.value(), self.resolution_h.value())},
            raw=self.sensor_mode
        )

    def apply_settings(self):
        self.picam2.video_configuration = self.picam2.create_video_configuration(
            main={"size": (self.resolution_w.value(), self.resolution_h.value())},
            raw=self.sensor_mode
        )
        switch_config("video")


class picTab(QWidget):
    def __init__(self, picam2):
        super().__init__()
        self.picam2 = picam2
        self.layout = QFormLayout()
        self.setLayout(self.layout)

        self.filename = QLineEdit()
        self.filetype = QComboBox()
        self.filetype.addItems(["jpg", "png", "bmp", "gif", "raw"])
        self.resolution_w = QSpinBox()
        self.resolution_w.setMaximum(self.picam2.sensor_resolution[0])
        self.resolution_w.valueChanged.connect(lambda: self.apply_button.setEnabled(True))
        self.resolution_h = QSpinBox()
        self.resolution_h.setMaximum(self.picam2.sensor_resolution[1])
        self.resolution_h.valueChanged.connect(lambda: self.apply_button.setEnabled(True))
        self.raw_format = QComboBox()
        self.raw_format.addItem("Default")
        self.raw_format.addItems([f'{x["format"].format} {x["size"]}' for x in self.picam2.sensor_modes])
        self.raw_format.currentIndexChanged.connect(self.update_options)
        self.preview_format = QComboBox()
        self.preview_format.currentIndexChanged.connect(lambda: self.apply_button.setEnabled(True))
        self.preview_check = QCheckBox()
        self.preview_check.setChecked(True)
        self.preview_check.stateChanged.connect(self.apply_settings)
        self.preview_warning = QLabel("WARNING: Preview and Capture modes have different fields of view")
        self.preview_warning.setWordWrap(True)
        self.preview_warning.hide()
        self.hdr_label = QLabel("HDR")
        self.hdr = QCheckBox()
        self.hdr.setChecked(False)
        self.hdr.setEnabled(cv_present)

        # --- Autofocus controls start here ---
        self.af_mode = QComboBox()
        self.af_mode.addItems(["Manual", "Auto", "Continuous"])
        self.af_mode.currentIndexChanged.connect(self.set_af_mode)
        # self.af_trigger = QPushButton("Trigger Autofocus")
        # self.af_trigger.clicked.connect(self.trigger_af)
        self.af_status = QLabel("")
        # --- Autofocus controls end here ---

        if cv_present:
            self.hdr.stateChanged.connect(self.pic_update)
            self.num_hdr = QSpinBox()
            self.num_hdr.setRange(3, 8)
            self.stops_hdr_above = QSpinBox()
            self.stops_hdr_above.setRange(1, 10)
            self.stops_hdr_below = QSpinBox()
            self.stops_hdr_below.setRange(1, 10)
            self.hdr_gamma = QDoubleSpinBox()
            self.hdr_gamma.setSingleStep(0.1)
        self.apply_button = QPushButton("Apply")
        self.apply_button.clicked.connect(self.apply_settings)
        self.apply_button.setEnabled(False)

        # Cosmetic additions
        resolution = QWidget()
        res_layout = QHBoxLayout()
        res_layout.addWidget(self.resolution_w)
        res_layout.addWidget(QLabel("x"), alignment=Qt.AlignHCenter)
        res_layout.addWidget(self.resolution_h)
        resolution.setLayout(res_layout)

        self.pic_update()
        self.update_options()
        self.reset()

        # Add the rows
        self.layout.addRow("Name", self.filename)
        self.layout.addRow("File Type", self.filetype)
        self.layout.addRow("Resolution", resolution)
        self.layout.addRow("Sensor Mode", self.raw_format)
        self.layout.addRow("Enable Preview Mode", self.preview_check)
        self.layout.addRow(self.preview_warning)
        self.layout.addRow("Preview Mode", self.preview_format)
        # --- Autofocus widgets in the layout ---
        self.layout.addRow("Autofocus Mode", self.af_mode)
        # self.layout.addRow(self.af_trigger)
        self.layout.addRow(self.af_status)
        # --- End autofocus widgets ---
        if cv_present:
            self.layout.addRow(self.hdr_label, self.hdr)
            self.layout.addRow("Number of HDR frames", self.num_hdr)
            self.layout.addRow("Number of HDR stops above", self.stops_hdr_above)
            self.layout.addRow("Number of HDR stops below", self.stops_hdr_below)
            self.layout.addRow("HDR Gamma Setting", self.hdr_gamma)
        else:
            self.layout.addRow(QLabel("HDR unavailable - install opencv to try it out"))

        self.layout.addRow(self.apply_button)

    @property
    def sensor_mode(self):
        configs = [{}]
        for mode in self.picam2.sensor_modes:
            configs.append({"size": mode["size"], "format": mode["format"].format})
        return configs[self.raw_format.currentIndex()]

    @property
    def preview_mode(self):
        configs = [self.sensor_mode]
        for mode in self.preview_modes:
            configs.append({"size": mode["size"], "format": mode["format"].format})
        return configs[self.preview_format.currentIndex()]

    @property
    def pic_dict(self):
        return {
            "FrameDurationLimits": self.picam2.camera_controls["FrameDurationLimits"][0:2]
        }

    def pic_update(self):
        if cv_present:
            self.stops_hdr_above.setEnabled(self.hdr.isChecked())
            self.stops_hdr_below.setEnabled(self.hdr.isChecked())
            self.num_hdr.setEnabled(self.hdr.isChecked())
            self.hdr_gamma.setEnabled(self.hdr.isChecked())
        if self.isVisible():
            self.picam2.set_controls(self.pic_dict)
        else:
            print("Not setting pic controls when not visible")

    def reset(self):
        self.resolution_h.setValue(self.picam2.still_configuration.main.size[1])
        self.resolution_w.setValue(self.picam2.still_configuration.main.size[0])
        if cv_present:
            self.hdr_gamma.setValue(2.2)
        self.picam2.still_configuration = self.picam2.create_still_configuration(
            main={"size": (self.resolution_w.value(), self.resolution_h.value())},
            **still_kwargs,
            raw=self.sensor_mode,
        )

    def update_options(self):
        self.apply_button.setEnabled(True)
        # Set the resolution
        try:
            self.resolution_w.setValue(self.sensor_mode["size"][0])
            self.resolution_h.setValue(self.sensor_mode["size"][1])
        except KeyError:
            self.resolution_h.setValue(self.picam2.still_configuration.main.size[1])
            self.resolution_w.setValue(self.picam2.still_configuration.main.size[0])

        # Update preview options
        preview_index = self.preview_format.currentIndex()
        if preview_index < 0:
            preview_index = 0
        if self.sensor_mode:
            crop_limits = self.picam2.sensor_modes[self.raw_format.currentIndex() - 1]["crop_limits"]
        else:
            crop_limits = (0, 0, *self.picam2.sensor_resolution)
        self.preview_format.clear()
        self.preview_format.addItem("Same as capture")
        self.preview_modes = []
        for mode in self.picam2.sensor_modes:
            if mode["crop_limits"] == crop_limits:
                self.preview_format.addItem(f'{mode["format"].format} {mode["size"]}')
                self.preview_modes.append(mode)
        try:
            self.preview_format.setCurrentIndex(preview_index)
        except IndexError:
            self.preview_format.setCurrentIndex(0)

    def apply_settings(self):
        hide_button.setEnabled(self.preview_check.isChecked())

        # Set configurations
        self.picam2.still_configuration = self.picam2.create_still_configuration(
            main={"size": (self.resolution_w.value(), self.resolution_h.value())},
            **still_kwargs,
            raw=self.sensor_mode,
        )
        self.picam2.preview_configuration = self.picam2.create_preview_configuration(
            main={"size": (
                qpicamera2.width(), int(qpicamera2.width() * (self.resolution_h.value() / self.resolution_w.value()))
            )},
            raw=self.preview_mode
        )
        self.preview_format.setEnabled(self.preview_check.isChecked())

        # Finally set the modes and check sensor crop
        if self.preview_check.isChecked():
            switch_config("still")
            _, current_crop, _ = self.picam2.camera_controls['ScalerCrop']
            switch_config("preview")
            _, preview_crop, _ = self.picam2.camera_controls['ScalerCrop']
            if current_crop != preview_crop:
                print("Preview and Still configs have different aspect ratios")
                self.preview_warning.show()
            else:
                self.preview_warning.hide()
        else:
            switch_config("still")
            self.preview_warning.hide()
        self.apply_button.setEnabled(False)

    # Autofocus Methods
    def set_af_mode(self):
        mode = self.af_mode.currentIndex()    # 0=Manual, 1=Auto, 2=Continuous
        self.picam2.set_controls({"AfMode": mode})
        self.af_status.setText(f"AF Mode set to {self.af_mode.currentText()}")

    # def trigger_af(self):
    #     if self.af_mode.currentIndex() != 0:
    #         self.picam2.set_controls({"AfTrigger": 0})
    #         self.af_status.setText("AF Triggered")
    #     else:
    #         self.af_status.setText("Switch to Auto or Continuous to trigger AF")

