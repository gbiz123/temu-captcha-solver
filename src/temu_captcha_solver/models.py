import json
from typing import Type
from pydantic import BaseModel

def dump_to_json(obj: BaseModel, filename: str) -> None:
    """Dump a pydantic obj to json file"""
    with open(filename, "w") as f:
        json.dump(obj.model_dump(), f)

class SwapTwoRequest(BaseModel):
    """Single image"""
    image_b64: str

class SemanticShapesRequest(BaseModel):
    """Single image with a text challenge"""
    image_b64: str
    challenge: str

class PuzzleCaptchaResponse(BaseModel):
    """This object contains data about the location
    of the slider button within its slide. The proportion x
    is the location of the slide button divided by the 
    length of the slide bar"""
    slide_x_proportion: float

class ArcedSlideCaptchaResponse(BaseModel):
    """This object contains data about the location
    of the slider button within its slide. The answer is 
    the number of pixels from slider origin"""
    pixels_from_slider_origin: int

class ProportionalPoint(BaseModel):
    """This object represents a point (x, y) where x is
    the x coordinate divided by the width of the container,
    and y is the y coordinate divided by the
    height of the container"""
    proportion_x: float
    proportion_y: float

class MultiPointResponse(BaseModel):
    """List of proportional points"""
    proportional_points: list[ProportionalPoint]

class ArcedSlideTrajectoryElement(BaseModel):
    """This object represents a point on the slider's trajectory.
    It contains data about the slider piece location and its rotation,
    as well as the location of the slider button.

    pixels_from_slider_origin (float): The number of pixels the slider button has been dragged from its origin
    piece_rotation_angle (float): The angle of rotation of the slider piece element
    piece_center (ProporitonalPoint): The center of the puzzle piece
    """
    pixels_from_slider_origin: int
    piece_rotation_angle: float
    piece_center: ProportionalPoint

class ArcedSlideCaptchaRequest(BaseModel):
    """This object contains data about the arced slide captcha including
    images, the trajectory of the slider, and the position of the 
    slider button."""
    puzzle_image_b64: str
    piece_image_b64: str
    slide_piece_trajectory: list[ArcedSlideTrajectoryElement]


class ThreeByThreeCaptchaRequest(BaseModel):
    """Contains data bout the 3x3 captcha.
    This includes the names of the objects as a list
    in the order they are meant to be selected. It
    also includes the images as a list of base64 strings
    where  indexes 0-2 are the top row, 3-5 are the
    middle, and 6-8 are the bottom row.
    """
    objects_of_interest: list[str]
    images: list[str]

class ThreeByThreeCaptchaResponse(BaseModel):
    """The indices of correct inages to click, in the order they must be clicked.
    Where the indeces correspond to the following panels:
        0 1 2
        3 4 5
        6 7 8"""
    solution_indices: list[int]

class TwoImageCaptchaRequest(BaseModel):
    """Contains text challenge and first and second images"""
    challenge: str
    images_b64: list[str]
