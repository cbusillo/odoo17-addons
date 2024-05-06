YES: str = "yes"
NO: str = "no"

YES_NO_SELECTION: list[tuple[str, str]] = [
    (YES, "Yes"),
    (NO, "No"),
]

MOTOR_CONFIGURATION_SELECTION: list[tuple[str, str]] = [
    ("s1", "Single 1"),
    ("i2", "Inline 2"),
    ("i3", "Inline 3"),
    ("i4", "Inline 4"),
    ("i5", "Inline 5"),
    ("i6", "Inline 6"),
    ("i8", "Inline 8"),
    ("v2", "V2"),
    ("v4", "V4"),
    ("v6", "V6"),
    ("v8", "V8"),
    ("v10", "V10"),
    ("v12", "V12"),
]

MOTOR_STROKE_SELECTION: list[tuple[str, str]] = [
    ("2", "2 Stroke"),
    ("4", "4 Stroke"),
]

MOTOR_STAGE_SELECTION: list[tuple[str, str]] = [
    ("basic_info", "Basic Info"),
    ("images", "Images"),
    ("parts", "Parts"),
    ("basic_testing", "Basic Testing"),
    ("extended_testing", "Extended Testing"),
    ("finalization", "Finalization"),
]

MOTOR_IMAGE_NAME_AND_ORDER: list[str] = [
    "Port Side",
    "Starboard Side",
    "Port Mid Section",
    "Starboard Midsection",
    "Data Label",
    "Powerhead - Port Side",
    "Powerhead - Starboard Side",
    "Powerhead - Front",
    "Powerhead - Back",
]
