YES: str = "yes"
NO: str = "no"

YES_NO_SELECTION: list[tuple[str, str]] = [
    (YES, "Yes"),
    (NO, "No"),
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
