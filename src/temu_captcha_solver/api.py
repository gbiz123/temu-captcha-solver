from typing import Any
import pydantic
import requests
import logging

from .models import ArcedSlideCaptchaRequest, ArcedSlideCaptchaResponse, ProportionalPoint, PuzzleCaptchaResponse, SemanticShapesRequest, MultiPointResponse, SwapTwoRequest, ThreeByThreeCaptchaRequest, ThreeByThreeCaptchaResponse, TwoImageCaptchaRequest

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
        self._SEMANTIC_ITEMS_URL = "https://www.sadcaptcha.com/api/v1/semantic-items?licenseKey=" + api_key
        self._THREE_BY_THREE_URL = "https://www.sadcaptcha.com/api/v1/temu-three-by-three?licenseKey=" + api_key
        self._SWAP_TWO_URL = "https://www.sadcaptcha.com/api/v1/temu-swap-two?licenseKey=" + api_key
        self._TWO_IMAGE_URL = "https://www.sadcaptcha.com/api/v1/temu-two-image?licenseKey=" + api_key

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

    def arced_slide(self, request: ArcedSlideCaptchaRequest | dict[str, Any]) -> ArcedSlideCaptchaResponse:
        """This is the Temu captcha where it's a puzzle slide, 
        but the piece travels in an unpredicatble trajectory and the 
        slide button is not correlated with the trajectory."""
        resp = self._make_post_request(self._ARCED_SLIDE_URL, request)
        result = resp.json()
        LOGGER.debug("Got API response: " + str(result))
        return ArcedSlideCaptchaResponse(pixels_from_slider_origin=result["pixelsFromSliderOrigin"])

    def semantic_shapes(self, request: SemanticShapesRequest | dict[str, Any]) -> MultiPointResponse:
        """Get the correct place to click to answer the challenge"""
        resp = self._make_post_request(self._SEMANTIC_SHAPES_URL, request)
        result = resp.json()
        LOGGER.debug("Got API response: " + str(result))
        return MultiPointResponse(
            proportional_points=[
                ProportionalPoint(
                    proportion_x=point["proportionX"],
                    proportion_y=point["proportionY"]
                )
                for point in result["proportionalPoints"]
            ]
        )

    def semantic_items(self, request: SemanticShapesRequest | dict[str, Any]) -> MultiPointResponse:
        """Get the correct place to click to answer the challenge"""
        resp = self._make_post_request(self._SEMANTIC_ITEMS_URL, request)
        result = resp.json()
        LOGGER.debug("Got API response: " + str(result))
        return MultiPointResponse(
            proportional_points=[
                ProportionalPoint(
                    proportion_x=point["proportionX"],
                    proportion_y=point["proportionY"]
                )
                for point in result["proportionalPoints"]
            ]
        )

    def three_by_three(self, request: ThreeByThreeCaptchaRequest | dict[str, Any]) -> ThreeByThreeCaptchaResponse:
        """Get the indices of correct inages to click, in the order they must be clicked.
        Where the indeces correspond to the following panels:
            0 1 2
            3 4 5
            6 7 8"""
        resp = self._make_post_request(self._THREE_BY_THREE_URL, request)
        result = resp.json()
        LOGGER.debug("Got API response: " + str(result))
        return ThreeByThreeCaptchaResponse(solution_indices=result["solutionIndices"])

    def swap_two(self, request: SwapTwoRequest | dict[str, Any]) -> MultiPointResponse:
        """Get the two sets of coordinates on the image to click and drag to.
        First point is the place to start the click, second point is the place to 
        drag to and release"""
        resp = self._make_post_request(self._SWAP_TWO_URL, request)
        result = resp.json()
        LOGGER.debug("Got API response: " + str(result))
        return MultiPointResponse(
            proportional_points=[
                ProportionalPoint(
                    proportion_x=point["proportionX"],
                    proportion_y=point["proportionY"]
                )
                for point in result["proportionalPoints"]
            ]
        )

    def two_image(self, request: TwoImageCaptchaRequest | dict[str, Any]) -> MultiPointResponse:
        """Get the correct place to click to answer the challenge"""
        resp = self._make_post_request(self._TWO_IMAGE_URL, request)
        result = resp.json()
        LOGGER.debug("Got API response: " + str(result))
        return MultiPointResponse(
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
        if resp.status_code == 502:
            raise ApiException("The SadCaptcha server is currently under maintenance, and will be back within 5 minutes.")
        if resp.status_code not in (200, 201):
            raise ApiException(f"status code {resp.status_code}. Probably a server issue. Please set log level to DEBUG and send the output to the SadCaptcha team to investigate")     
        LOGGER.debug(f"made successful request on {url}")
        return resp
