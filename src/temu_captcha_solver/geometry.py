import re

from temu_captcha_solver.models import ProportionalPoint

def rotate_angle_from_style(style: str) -> float:
    """Extract the rotate value from the css style attribute"""
    if not "rotate" in style:
        return 0
    rotate_string = re.sub(r".*rotate\(|deg.*", "", style)
    return float(rotate_string)


def xy_to_proportional_point(
        x: float,
        y: float,
        container_width: float,
        container_height: float
    ) -> ProportionalPoint:
    """Convert an x, y pair into a propotional point where the 
    resulting x and y proportions are the fraction of the width
    and height respectively.
    """
    return ProportionalPoint(
        proportion_x= x / container_width,
        proportion_y= y / container_height,
    )


def get_center(left_x: float, top_y: float, width: float, height: float) -> tuple[float, float]:
    """Get the center of a box from the left, top, width, and height measurements"""
    center_x = left_x + (width / 2)
    center_y = top_y + (height / 2)
    return center_x, center_y
