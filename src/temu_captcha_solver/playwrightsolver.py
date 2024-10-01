"""This class handles the captcha solving for playwright users"""

import random
import time
from typing import Literal
from playwright.sync_api import FloatRect, Locator, Page, expect
from undetected_chromedriver import logging

from .urls import ARCED_SLIDE_URL_PATTERN

from .selectors import (
    ARCED_SLIDE_BAR_SELECTOR,
    ARCED_SLIDE_BUTTON_SELECTOR,
    ARCED_SLIDE_PIECE_IMAGE_SELECTOR,
    ARCED_SLIDE_PUZZLE_IMAGE_SELECTOR,
    CAPTCHA_WRAPPERS,
    PUZZLE_SELECTORS
) 

from .geometry import (
    get_center,
    rotate_angle_from_style,
    xy_to_proportional_point
) 

from .models import (
    ArcedSlideCaptchaRequest,
    ArcedSlideTrajectoryElement
) 

from .syncsolver import SyncSolver
from .api import ApiClient
from .downloader import download_image_b64


class PlaywrightSolver(SyncSolver):

    client: ApiClient
    page: Page

    def __init__(
            self,
            page: Page,
            sadcaptcha_api_key: str,
            headers: dict | None = None, 
            proxy: str | None = None
        ) -> None:
        self.page = page
        self.client = ApiClient(sadcaptcha_api_key)
        self.headers = headers
        self.proxy = proxy

    def captcha_is_present(self, timeout: int = 15) -> bool:
        try:
            captcha_locator = self.page.locator(CAPTCHA_WRAPPERS[0])
            expect(captcha_locator.first).to_be_visible(timeout=timeout * 1000)
            return True
        except (TimeoutError, AssertionError):
            return False

    def captcha_is_not_present(self, timeout: int = 15) -> bool:
        try:
            captcha_locator = self.page.locator(CAPTCHA_WRAPPERS[0])
            expect(captcha_locator.first).to_have_count(0, timeout=timeout * 1000)
            return True
        except (TimeoutError, AssertionError):
            return False

    def identify_captcha(self) -> Literal["puzzle", "arced_slide"]:
        for _ in range(15):
            if self._any_selector_in_list_present(PUZZLE_SELECTORS):
                logging.debug("detected puzzle")
                return "puzzle"
            elif ARCED_SLIDE_URL_PATTERN in self.page.url:
                logging.debug("detected arced slide")
                return "arced_slide"
            else:
                time.sleep(2)
        raise ValueError("Neither puzzle, or arced slide was present")

    def solve_puzzle(self, retries: int = 3) -> None:
        """Temu puzzle is special because the pieces shift when pressing the slider button.
        Therefore we must send the pictures after pressing the button. """
        raise NotImplementedError()

    def solve_arced_slide(self) -> None:
        """Solves the arced slide puzzle. This challenge is similar to the puzzle
        challenge, but the puzzle piece travels in an arc, hence then name arced slide.
        The API expects the b64 encoded puzzle and piece images, along with data about the piece's
        trajectory in a list of ArcedSlideTrajectoryElements.

        This function will get the b64 encoded images, and will 'sweep' the slide
        bar to determine the piece's trajectory. Then it sends the data to the API
        and consumes the response.
        """
        if not self._any_selector_in_list_present(["#captcha-verify-image"]):
            logging.debug("Went to solve icon captcha but #captcha-verify-image was not present")
            return
        puzzle = self.get_b64_img_from_src(ARCED_SLIDE_PUZZLE_IMAGE_SELECTOR)
        piece = self.get_b64_img_from_src(ARCED_SLIDE_PIECE_SELECTOR)
        trajectory = self._get_arced_slide_trajectory()
        request = ArcedSlideCaptchaRequest(
            puzzle_image_b64=puzzle,
            piece_image_b64=piece,
            slide_piece_trajectory=trajectory
        )
        solution = self.client.arced_slide(request)
        distance = self._compute_puzzle_slide_distance(solution.pixels_from_slider_origin)
        self._drag_element_horizontal_with_overshoot(ARCED_SLIDE_BUTTON_SELECTOR, distance)
        if self.captcha_is_not_present(timeout=5):
            return
        else:
            time.sleep(5)

    def _click_proportional(
            self,
            bounding_box: FloatRect,
            proportion_x: float,
            proportion_y: float
        ) -> None:
        """Click an element inside its bounding box at a point defined by the proportions of x and y
        to the width and height of the entire element

        Args:
            element: FloatRect to click inside
            proportion_x: float from 0 to 1 defining the proportion x location to click 
            proportion_y: float from 0 to 1 defining the proportion y location to click 
        """
        x_origin = bounding_box["x"]
        y_origin = bounding_box["y"]
        x_offset = (proportion_x * bounding_box["width"])
        y_offset = (proportion_y * bounding_box["height"]) 
        self.page.mouse.move(x_origin + x_offset, y_origin + y_offset)
        time.sleep(random.randint(1, 10) / 11)
        self.page.mouse.down()
        time.sleep(0.001337)
        self.page.mouse.up()
        time.sleep(random.randint(1, 10) / 11)

    def _drag_element_horizontal_with_overshoot(self, css_selector: str, x: int, frame_selector: str | None = None) -> None:
        if frame_selector:
            e = self.page.frame_locator(frame_selector).locator(css_selector)
        else:
            e = self.page.locator(css_selector)
        box = e.bounding_box()
        if not box:
            raise AttributeError("Element had no bounding box")
        start_x = (box["x"] + (box["width"] / 1.337))
        start_y = (box["y"] +  (box["height"] / 1.337))
        self.page.mouse.move(start_x, start_y)
        time.sleep(random.randint(1, 10) / 11)
        self.page.mouse.down()
        time.sleep(random.randint(1, 10) / 11)
        self.page.mouse.move(start_x + x, start_y, steps=100)
        overshoot = random.choice([1, 2, 3, 4])
        self.page.mouse.move(start_x + x + overshoot, start_y + overshoot, steps=100) # overshoot forward
        self.page.mouse.move(start_x + x, start_y, steps=75) # overshoot back
        time.sleep(0.001)
        self.page.mouse.up()

    def _any_selector_in_list_present(self, selectors: list[str]) -> bool:
        for selector in selectors:
            for ele in self.page.locator(selector).all():
                if ele.is_visible():
                    logging.debug("Detected selector: " + selector + " from list " + ", ".join(selectors))
                    return True
        logging.debug("No selector in list found: " + ", ".join(selectors))
        return False

    def _get_arced_slide_trajectory(self) -> list[ArcedSlideTrajectoryElement]:
        """Determines slider trajectory by dragging the slider element across the entire box,
        and computing the ArcedSlideTrajectoryElement at each location."""
        slide_button_locator = self.page.locator(ARCED_SLIDE_BUTTON_SELECTOR)
        slider_piece_locator = self.page.locator(ARCED_SLIDE_PIECE_SELECTOR)
        slide_bar_width = self._get_element_width(ARCED_SLIDE_BAR_SELECTOR)
        puzzle_img_bounding_box = self._get_element_bounding_box(ARCED_SLIDE_PUZZLE_IMAGE_SELECTOR)
        self._move_mouse_to_element_center(slide_button_locator)
        self.page.mouse.down()
        trajectory: list[ArcedSlideTrajectoryElement] = []
        for pixel in range(0, int(slide_bar_width), 4):
            self._move_mouse_to_element_center(slide_button_locator, x_offset=pixel)
            trajectory.append(
                self._get_arced_slide_trajectory_element(
                    pixel,
                    slide_bar_width,
                    puzzle_img_bounding_box,
                    slider_piece_locator
                )
            )
        self.page.mouse.up()
        return trajectory

    def _get_arced_slide_trajectory_element(
            self,
            current_slider_pixel: int,
            slide_bar_width: float,
            large_img_bounding_box: FloatRect,
            slider_piece_locator: Locator, 
        ) -> ArcedSlideTrajectoryElement:
        """Compute current slider trajectory element by extracting information on the 
        slide button location, the piece rotation, and the piece location"""
        slider_piece_bounding_box = slider_piece_locator.bounding_box()
        if not slider_piece_bounding_box:
            raise ValueError("Bouding box for slider image was None")
        slider_piece_style = slider_piece_locator.get_attribute("style")
        if not slider_piece_style:
            raise ValueError("Slider piece style was None")
        rotate_angle = rotate_angle_from_style(slider_piece_style)
        top = slider_piece_bounding_box["x"]
        left = slider_piece_bounding_box["y"]
        width = slider_piece_bounding_box["width"]
        height = slider_piece_bounding_box["height"]
        container_width = large_img_bounding_box["width"]
        container_height = large_img_bounding_box["height"]
        piece_center_x, piece_center_y = get_center(left, top, width, height)
        piece_center = xy_to_proportional_point(piece_center_x, piece_center_y, container_width, container_height)
        return ArcedSlideTrajectoryElement(
            pixels_from_slider_origin=current_slider_pixel / slide_bar_width,
            piece_rotation_angle=rotate_angle,
            piece_center=piece_center
        )

    def _get_element_bounding_box(self, selector: str) -> FloatRect:
        box = self.page.locator(selector).bounding_box()
        if box is None:
            raise ValueError("Bounding box for slide bar was none")
        return box

    def _move_mouse_to_element_center(self, ele: Locator, x_offset: float = 0, y_offset: int = 0) -> None:
        box = ele.bounding_box()
        if box is None:
            raise ValueError("Bounding box for element was none")
        self.page.mouse.move(
            *get_center(
                box["x"] + x_offset,
                box["y"] + y_offset,
                box["width"],
                box["height"]
            )
        )

    def get_b64_img_from_src(self, selector: str) -> str:
        """Get the source of b64 image element and return the portion after the data:image/png;base64,"""
        e = self.page.locator(selector)
        url = e.get_attribute("src")
        if not url:
            raise ValueError("element " + selector + " had no url")
        return url.split(",")[1]

    def _compute_puzzle_slide_distance(self, proportion_x: float) -> int:
        e = self.page.locator("#captcha-verify-image")
        box = e.bounding_box()
        if box:
            return int(proportion_x * box["width"])
        raise AttributeError("#captcha-verify-image was found but had no bouding box")

    def _get_element_width(self, selector: str) -> float:
        e = self.page.locator(selector)
        box = e.bounding_box()
        if box:
            return int(box["width"])
        raise AttributeError(".captcha_verify_slide--slidebar was found but had no bouding box")

