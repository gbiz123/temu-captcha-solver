import requests
import logging

from .models import ArcedSlideCaptchaRequest, ArcedSlideCaptchaResponse, PuzzleCaptchaResponse

LOGGER = logging.getLogger(__name__)

class ApiClient:

    def __init__(self, api_key: str) -> None:
        self._PUZZLE_URL = "https://www.sadcaptcha.com/api/v1/puzzle?licenseKey=" + api_key
        self._ARCED_SLIDE_URL = "https://www.sadcaptcha.com/api/v1/temu-arced-slide?licenseKey=" + api_key

    def puzzle(self, puzzle_b64: str, piece_b64: str) -> PuzzleCaptchaResponse:
        """Slide the puzzle piece"""
        data = {
            "puzzleImageB64": puzzle_b64,
            "pieceImageB64": piece_b64
        }        
        resp = requests.post(self._PUZZLE_URL, json=data)
        result = resp.json()
        LOGGER.debug("Got API response: " + str(result))
        return PuzzleCaptchaResponse(slide_x_proportion=result.get("slideXProportion"))

    def arced_slide(self, request: ArcedSlideCaptchaRequest) -> ArcedSlideCaptchaResponse:
        """This is the Temu captcha where it's a puzzle slide, 
        but the piece travels in an unpredicatble trajectory and the 
        slide button is not correlated with the trajectory."""
        resp = requests.post(self._ARCED_SLIDE_URL, json=request.model_dump())
        result = resp.json()
        LOGGER.debug("Got API response: " + str(result))
        return ArcedSlideCaptchaResponse(pixels_from_slider_origin=result["pixelsFromSliderOrigin"])
