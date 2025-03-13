import base64
import json
import os

from ..downloader import download_image_b64
from ..api import ApiClient
from temu_captcha_solver.models import ArcedSlideCaptchaRequest, ArcedSlideCaptchaResponse, ProportionalPoint, PuzzleCaptchaResponse, SemanticShapesRequest, MultiPointResponse, ThreeByThreeCaptchaRequest, ThreeByThreeCaptchaResponse

api_client = ApiClient(os.environ["API_KEY"])

def test_puzzle():
    piece = download_image_b64("https://raw.githubusercontent.com/gbiz123/sadcaptcha-code-examples/master/images/piece.png")
    puzzle = download_image_b64("https://raw.githubusercontent.com/gbiz123/sadcaptcha-code-examples/master/images/puzzle.jpg")
    res = api_client.puzzle(puzzle, piece)
    assert isinstance(res, PuzzleCaptchaResponse)

def test_arced_slide():
    with open("src/temu_captcha_solver/tests/temu_slide_captcha_request.json") as file:
        data = json.load(file)
        res = api_client.arced_slide(ArcedSlideCaptchaRequest(**data))
        assert isinstance(res, ArcedSlideCaptchaResponse)

def test_semantic_shapes():
    with open("src/temu_captcha_solver/tests/shapes.png", "rb") as file:
        shapes = base64.b64encode(file.read()).decode()

    challenge = "Please click on the lowercase letter corresponding to the green letter."
    res = api_client.semantic_shapes(SemanticShapesRequest(image_b64=shapes, challenge=challenge))
    assert isinstance(res, MultiPointResponse)

def test_three_by_three():
    with open("src/temu_captcha_solver/tests/three_by_three_request.json", "rb") as file:
        data = json.load(file)
        res = api_client.three_by_three(data)
        assert isinstance(res, ThreeByThreeCaptchaResponse)

def test_two_image():
    with open("src/temu_captcha_solver/tests/two-image-request.json", "rb") as file:
        data = json.load(file)
        res = api_client.two_image(data)
        assert isinstance(res, MultiPointResponse)

def test_cats_and_cars():
    with open("src/temu_captcha_solver/tests/temu-cats-and-cars.json", "rb") as file:
        data = json.load(file)
        res = api_client.semantic_shapes(data)
        assert isinstance(res, MultiPointResponse)
