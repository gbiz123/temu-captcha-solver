import requests
import logging

from .models import ArcedSlideCaptchaRequest, ArcedSlideCaptchaResponse

class ApiClient:

    _PUZZLE_URL: str
    _ARCED_SLIDE_URL: str

    def __init__(self, api_key: str) -> None:
        self._PUZZLE_URL = "https://www.sadcaptcha.com/api/v1/puzzle?licenseKey=" + api_key
        self._ARCED_SLIDE_URL = "https://www.sadcaptcha.com/api/v1/temu-arced-slide?licenseKey=" + api_key

    def puzzle(self, puzzle_b64: str, piece_b64: str) -> ArcedSlideCaptchaResponse:
        """Slide the puzzle piece"""
        data = {
            "puzzleImageB64": puzzle_b64,
            "pieceImageB64": piece_b64
        }        
        resp = requests.post(self._PUZZLE_URL, json=data)
        result = resp.json()
        logging.debug("Got API response: " + str(result))
        return ArcedSlideCaptchaResponse(pixels_from_slider_origin=result.get("slideXProportion"))

    def arced_slide(self, request: ArcedSlideCaptchaRequest) -> ArcedSlideCaptchaResponse:
        """This is the Temu captcha where it's a puzzle slide, 
        but the piece travels in an unpredicatble trajectory and the 
        slide button is not correlated with the trajectory."""
        resp = requests.post(self._ARCED_SLIDE_URL, json=request.model_dump())
        result = resp.json()
        logging.debug("Got API response: " + str(result))
        return ArcedSlideCaptchaResponse(pixels_from_slider_origin=result["pixelsFromSliderOrigin"])
