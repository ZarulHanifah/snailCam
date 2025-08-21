
still_kwargs = {
  # "lores": {"size": lores_size},
  "display": "lores",
  "encode": "lores",
  "buffer_count": 1,
}

implemented_controls = [
    "ColourCorrectionMatrix",
    "Saturation",
    "Contrast",
    "Sharpness",
    "Brightness",
    "NoiseReductionMode",
    "AeEnable",
    "AeMeteringMode",
    "AeConstraintMode",
    "AeExposureMode",
    "AwbEnable",
    "AwbMode",
    "ExposureValue",
    "ExposureTime",
    "AnalogueGain",
    "ColourGains",
    "ScalerCrop",
    "FrameDurationLimits"
]

ignore_controls = {
    # It is not helpful to try to drive AF with simple slider controls, so ignore them.
    # "AfMode",
    # "AfTrigger",
    "AfSpeed",
    "AfRange",
    "AfWindows",
    "AfPause",
    "AfMetering",
    "ScalerCrops"
}
