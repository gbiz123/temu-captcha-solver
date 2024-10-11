from pydantic import BaseModel

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
