from enum import Enum

class CaptchaType(Enum):
    ARCED_SLIDE = 0
    PUZZLE = 1
    SEMANTIC_SHAPES = 2
    THREE_BY_THREE = 3
    SWAP_TWO = 4
    TWO_IMAGE = 5
    NONE = 6
