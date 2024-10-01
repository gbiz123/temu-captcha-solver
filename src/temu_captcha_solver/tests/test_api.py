import json
import os

from ..downloader import download_image_b64
from ..api import ApiClient
from temu_captcha_solver.models import ArcedSlideCaptchaRequest, ArcedSlideCaptchaResponse

api_client = ApiClient(os.environ["API_KEY"])

def test_puzzle():
    piece = download_image_b64("https://raw.githubusercontent.com/gbiz123/sadcaptcha-code-examples/master/images/piece.png")
    puzzle = download_image_b64("https://raw.githubusercontent.com/gbiz123/sadcaptcha-code-examples/master/images/puzzle.jpg")
    res = api_client.puzzle(puzzle, piece)
    assert isinstance(res, ArcedSlideCaptchaResponse)

def test_arced_slide():
    with open("src/temu_captcha_solver/tests/temu_slide_captcha_request.json") as file:
        data = json.load(file)
        res = api_client.arced_slide(ArcedSlideCaptchaRequest(**data))
        assert isinstance(res, ArcedSlideCaptchaResponse)
