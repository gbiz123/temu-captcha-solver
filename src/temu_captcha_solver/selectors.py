ARCED_SLIDE_PUZZLE_IMAGE_SELECTOR = "#slider > img"
ARCED_SLIDE_PIECE_CONTAINER_SELECTOR = "#img-button"
ARCED_SLIDE_PIECE_IMAGE_SELECTOR = "#img-button > img"
ARCED_SLIDE_BUTTON_SELECTOR = "#slide-button"
ARCED_SLIDE_UNIQUE_IDENTIFIERS = [".handleBar-vT4I5", ".vT4I57cQ", "div[style=\"width: 414px;\"] #slider", "div[style=\"width: 410px;\"] #slider"]

PUZZLE_BUTTON_SELECTOR = "#slide-button"
PUZZLE_PUZZLE_IMAGE_SELECTOR = "#slider > img"
PUZZLE_PIECE_IMAGE_SELECTOR = "#img-button > img"
PUZZLE_UNIQUE_IDENTIFIERS = ["#Slider"]

SEMANTIC_SHAPES_IFRAME = ".iframe-3eaNR" # TODO: Make this a more universal selector
SEMANTIC_SHAPES_CHALLENGE_ROOT_ELE = "#Picture"
SEMANTIC_SHAPES_CHALLENGE_TEXT = ".picture-text-2Alt0"
SEMANTIC_SHAPES_IMAGE = "#captchaImg"
SEMANTIC_SHAPES_REFRESH_BUTTON = ".refresh-27d6x"
SEMANTIC_SHAPES_UNIQUE_IDENTIFIERS = [SEMANTIC_SHAPES_IFRAME, SEMANTIC_SHAPES_IMAGE]

THREE_BY_THREE_IMAGE = "img.loaded"
THREE_BY_THREE_TEXT = ".verifyDialog div[role=dialog]"
THREE_BY_THREE_CONFIRM_BUTTON = ".verifyDialog div[role=button]:has(span)"
THREE_BY_THREE_UNIQUE_IDENTIFIERS = ["#imageSemantics img.loaded"]

# Occassionally Temu shows a familiar challenge but it's in an iframe
# Need a way to account for occasions when other challenges are nested in iframe

CAPTCHA_PRESENCE_INDICATORS = [
    "#imageSemantics img.loaded",
    "#slide-button",
    "#Slider",
    "#slider",
    SEMANTIC_SHAPES_IFRAME
]
