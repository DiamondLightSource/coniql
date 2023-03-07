# This will eventually go in a different module so pvi and coniql (and gda) can use it
from enum import Enum

import strawberry


@strawberry.enum
class DisplayForm(str, Enum):
    """
    Instructions for how a number should be formatted for display
    """

    # Use the default representation from value
    DEFAULT = "DEFAULT"
    # Force string representation, most useful for array of bytes
    STRING = "STRING"
    # Binary, precision determines number of binary digits
    BINARY = "BINARY"
    # Decimal, precision determines number of digits after decimal point
    DECIMAL = "DECIMAL"
    # Hexadecimal, precision determines number of hex digits
    HEX = "HEX"
    # Exponential, precision determines number of digits after decimal point
    EXPONENTIAL = "EXPONENTIAL"
    # Exponential where exponent is multiple of 3, precision determines number
    # of digits after decimal point
    ENGINEERING = "ENGINEERING"


@strawberry.enum
class Widget(str, Enum):
    """
    Widget that should be used to display a Channel
    """

    # Editable text input
    TEXTINPUT = "TEXTINPUT"
    # Read-only text display
    TEXTUPDATE = "TEXTUPDATE"
    # Multiline read-only text display
    MULTILINETEXTUPDATE = "MULTILINETEXTUPDATE"
    # Read-only LED indicator
    LED = "LED"
    # Editable combo-box style menu for selecting between fixed choices
    COMBO = "COMBO"
    # Editable check box
    CHECKBOX = "CHECKBOX"
    # Editable progress type bar
    BAR = "BAR"
    # Clickable button to send default value to Channel
    BUTTON = "BUTTON"
    # X-axis for lines on a graph. Only valid within a Group with widget Plot
    PLOTX = "PLOTX"
    # Y-axis for a line on a graph. Only valid within a Group with widget Plot
    PLOTY = "PLOTY"


class Layout(str, Enum):
    SCREEN = "SCREEN"
    BOX = "BOX"
    PLOT = "PLOT"
    ROW = "ROW"
    TABLE = "TABLE"
