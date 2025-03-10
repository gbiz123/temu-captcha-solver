import logging
from enum import Enum

from temu_captcha_solver.selectors import TWO_IMAGE_FIRST_IMAGE, TWO_IMAGE_SECOND_IMAGE
from temu_captcha_solver.solver_commons.exceptions import UnsupportedLanguageException

LOGGER = logging.getLogger(__name__)

def two_image_challenge_is_supported(challenge_text: str) -> bool:
    if "left to right" in challenge_text.lower():
        LOGGER.debug(f"challenge \"{challenge_text}\" is supported")
        return True
    elif "right to left" in challenge_text.lower():
        LOGGER.debug(f"challenge \"{challenge_text}\" is supported")
        return True
    else:
        LOGGER.debug(f"challenge \"{challenge_text}\" is not supported")
        return False

def identify_selector_of_image_to_click(challenge_text: str) -> str:
    """Get the CSS selector of the left or right image that must be clicked
    according to the challenge text."""
    lower_text = challenge_text.lower()
    figure_1_index = lower_text.find("figure 1")
    figure_2_index = lower_text.find("figure 2")
    if figure_1_index == -1 or figure_2_index == -1:
        raise UnsupportedLanguageException("Possible issue due to unsupported language. Currently only English is supported. Could not see 'figure 1' or 'figure 2' in challenge text: " + challenge_text)
    if figure_1_index < figure_2_index:
        return TWO_IMAGE_FIRST_IMAGE
    else:
        return TWO_IMAGE_SECOND_IMAGE
    

