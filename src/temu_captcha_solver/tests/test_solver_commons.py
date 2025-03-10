import time
import logging
import os

import pytest

from temu_captcha_solver.selectors import TWO_IMAGE_FIRST_IMAGE, TWO_IMAGE_SECOND_IMAGE
from temu_captcha_solver.solver_commons.exceptions import UnsupportedLanguageException

from ..solver_commons.two_image import two_image_challenge_is_supported, identify_selector_of_image_to_click

def test_check_challenge_is_supported(caplog):
    caplog.set_level(logging.DEBUG)
    challenge = "Please click on the corresponding characters in [FIGURE_NUM] in the order they appear from left to right in [FIGURE_NUM]."
    assert two_image_challenge_is_supported(challenge) == True

def test_check_challenge_is_not_supported(caplog):
    caplog.set_level(logging.DEBUG)
    challenge = "floopy doober"
    assert two_image_challenge_is_supported(challenge) == False

def test_identift_selector_of_image_to_click_is_figure_1(caplog):
    caplog.set_level(logging.DEBUG)
    challenge = "Please click on the corresponding characters in figure 1 in the order they appear from left to right in figure 2."
    assert identify_selector_of_image_to_click(challenge) == TWO_IMAGE_FIRST_IMAGE

def test_identift_selector_of_image_to_click_is_figure_2(caplog):
    caplog.set_level(logging.DEBUG)
    challenge = "Please click on the corresponding characters in figure 2 in the order they appear from left to right in figure 1."
    assert identify_selector_of_image_to_click(challenge) == TWO_IMAGE_SECOND_IMAGE

def test_identift_selector_of_image_to_click_throws_if_not_english(caplog):
    caplog.set_level(logging.DEBUG)
    challenge = "oye como va"
    with pytest.raises(UnsupportedLanguageException):
        identify_selector_of_image_to_click(challenge)
