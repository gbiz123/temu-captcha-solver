from typing import Any
import pydantic
import requests
import logging

from .models import ArcedSlideCaptchaRequest, ArcedSlideCaptchaResponse, ProportionalPoint, PuzzleCaptchaResponse, SemanticShapesRequest, SemanticShapesResponse

LOGGER = logging.getLogger(__name__)

class ApiException(Exception):
    pass

class BadRequest(ApiException):
    pass

class ApiClient:

    def __init__(self, api_key: str) -> None:
        self._PUZZLE_URL = "https://www.sadcaptcha.com/api/v1/puzzle?licenseKey=" + api_key
        self._ARCED_SLIDE_URL = "https://www.sadcaptcha.com/api/v1/temu-arced-slide?licenseKey=" + api_key
        self._SEMANTIC_SHAPES_URL = "https://www.sadcaptcha.com/api/v1/semantic-shapes?licenseKey=" + api_key

    def puzzle(self, puzzle_b64: str, piece_b64: str) -> PuzzleCaptchaResponse:
        """Slide the puzzle piece"""
        data = {
            "puzzleImageB64": puzzle_b64,
            "pieceImageB64": piece_b64
        }        
        resp = self._make_post_request(self._PUZZLE_URL, data)
        result = resp.json()
        LOGGER.debug("Got API response: " + str(result))
        return PuzzleCaptchaResponse(slide_x_proportion=result.get("slideXProportion"))

    def arced_slide(self, request: ArcedSlideCaptchaRequest) -> ArcedSlideCaptchaResponse:
        """This is the Temu captcha where it's a puzzle slide, 
        but the piece travels in an unpredicatble trajectory and the 
        slide button is not correlated with the trajectory."""
        resp = self._make_post_request(self._ARCED_SLIDE_URL, request)
        result = resp.json()
        LOGGER.debug("Got API response: " + str(result))
        return ArcedSlideCaptchaResponse(pixels_from_slider_origin=result["pixelsFromSliderOrigin"])

    def semantic_shapes(self, request: SemanticShapesRequest) -> SemanticShapesResponse:
        """Get the correct place to click to answer the challenge"""
        resp = self._make_post_request(self._SEMANTIC_SHAPES_URL, request)
        result = resp.json()
        LOGGER.debug("Got API response: " + str(result))
        return SemanticShapesResponse(
            proportional_points=[
                ProportionalPoint(
                    proportion_x=point["proportionX"],
                    proportion_y=point["proportionY"]
                )
                for point in result["proportionalPoints"]
            ]
        )

    def _make_post_request(self, url: str, data: pydantic.BaseModel | dict[str, Any]) -> requests.Response:
        if isinstance(data, pydantic.BaseModel):
            resp = requests.post(url, json=data.model_dump())
        else:
            resp = requests.post(url, json=data)
        if resp.status_code == 400:
            raise BadRequest(f"status code {resp.status_code}. bad request or could not find answer")     
        if resp.status_code == 401:
            raise ApiException(f"status code {resp.status_code}. either bad API key or out of credits")     
        return resp
