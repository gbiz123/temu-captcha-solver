"""This class handles the captcha solving for selenium users"""

import time
from typing import Literal
from playwright.sync_api import FloatRect

from selenium.webdriver import ActionChains, Chrome
from selenium.webdriver.common.actions.action_builder import ActionBuilder
from selenium.webdriver.common.by import By
from selenium.webdriver.remote.webelement import WebElement
from undetected_chromedriver import logging
from undetected_chromedriver.patcher import random

from .geometry import(
    get_center,
    rotate_angle_from_style,
    xy_to_proportional_point
) 

from .selectors import (
    ARCED_SLIDE_BAR_SELECTOR,
    ARCED_SLIDE_BUTTON_SELECTOR,
    ARCED_SLIDE_PIECE_IMAGE_SELECTOR,
    ARCED_SLIDE_PUZZLE_IMAGE_SELECTOR,
    CAPTCHA_WRAPPERS,
    PUZZLE_SELECTORS
) 
 
from .models import ArcedSlideCaptchaRequest, ArcedSlideTrajectoryElement
from .urls import ARCED_SLIDE_URL_PATTERN
from .api import ApiClient
from .downloader import download_image_b64
from .syncsolver import SyncSolver

class SeleniumSolver(SyncSolver):

    client: ApiClient
    chromedriver: Chrome

    def __init__(
            self, 
            chromedriver: Chrome,
            sadcaptcha_api_key: str,
            headers: dict | None = None,
            proxy: str | None = None
        ) -> None:
        self.chromedriver = chromedriver
        self.client = ApiClient(sadcaptcha_api_key)
        self.headers = headers
        self.proxy = proxy

    def captcha_is_present(self, timeout: int = 15) -> bool:
        for _ in range(timeout * 2):
            if self._any_selector_in_list_present(CAPTCHA_WRAPPERS):
                print("Captcha detected")
                return True
            time.sleep(0.5)
        logging.debug("Captcha not found")
        return False

    def captcha_is_not_present(self, timeout: int = 15) -> bool:
        for _ in range(timeout * 2):
            if len(self.chromedriver.find_elements(By.CSS_SELECTOR, CAPTCHA_WRAPPERS[0])) == 0:
                print("Captcha not present")
                return True
            time.sleep(0.5)
        logging.debug("Captcha not found")
        return False

    def identify_captcha(self) -> Literal["puzzle", "arced_slide"]:
        for _ in range(15):
            if self._any_selector_in_list_present(PUZZLE_SELECTORS):
                return "puzzle"
            elif ARCED_SLIDE_URL_PATTERN in self.chromedriver.current_url:
                return "arced_slide"
            else:
                time.sleep(2)
        raise ValueError("Neither puzzle, shapes, or rotate captcha was present.")

    def solve_puzzle(self) -> None:
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

    def get_b64_img_from_src(self, selector: str) -> str:
        """Get the source of b64 image element and return the portion after the data:image/png;base64,"""
        e = self.chromedriver.find_element(By.CSS_SELECTOR, selector)
        url = e.get_attribute("src")
        if not url:
            raise ValueError("Could not get image source for " + selector)
        return url.split(",")[1]

    def _click_proportional(
            self,
            element: WebElement,
            proportion_x: float,
            proportion_y: float
        ) -> None:
        """Click an element inside its bounding box at a point defined by the proportions of x and y
        to the width and height of the entire element

        Args:
            element: WebElement to click inside
            proportion_x: float from 0 to 1 defining the proportion x location to click 
            proportion_y: float from 0 to 1 defining the proportion y location to click 
        """
        x_origin = element.location["x"]
        y_origin = element.location["y"]
        x_offset = (proportion_x * element.size["width"])
        y_offset = (proportion_y * element.size["height"]) 
        action = ActionBuilder(self.chromedriver)
        action.pointer_action \
            .move_to_location(x_origin + x_offset, y_origin + y_offset) \
            .pause(random.randint(1, 10) / 11) \
            .click() \
            .pause(random.randint(1, 10) / 11)
        action.perform()

    def _drag_element_horizontal_with_overshoot(self, css_selector: str, x: int) -> None:
        e = self.chromedriver.find_element(By.CSS_SELECTOR, css_selector)
        actions = ActionChains(self.chromedriver, duration=0)
        actions.click_and_hold(e)
        time.sleep(0.1)
        for _ in range(0, x - 15):
            actions.move_by_offset(1, 0)
        for _ in range(0, 20):
            actions.move_by_offset(1, 0)
            actions.pause(0.01)
        actions.pause(0.7)
        for _ in range(0, 5):
            actions.move_by_offset(-1, 0)
            actions.pause(0.05)
        actions.pause(0.1)
        actions.release().perform()

    def _any_selector_in_list_present(self, selectors: list[str]) -> bool:
        for selector in selectors:
            for ele in self.chromedriver.find_elements(By.CSS_SELECTOR, selector):
                if ele.is_displayed():
                    logging.debug("Detected selector: " + selector + " from list " + ", ".join(selectors))
                    return True
        logging.debug("No selector in list found: " + ", ".join(selectors))
        return False

    def _get_arced_slide_trajectory(self) -> list[ArcedSlideTrajectoryElement]:
        """Determines slider trajectory by dragging the slider element across the entire box,
        and computing the ArcedSlideTrajectoryElement at each location."""
        slide_button = self.chromedriver.find_element(By.CSS_SELECTOR, ARCED_SLIDE_BUTTON_SELECTOR)
        slider_piece = self.chromedriver.find_element(By.CSS_SELECTOR, ARCED_SLIDE_PIECE_SELECTOR)
        slide_bar = self.chromedriver.find_element(By.CSS_SELECTOR, ARCED_SLIDE_BAR_SELECTOR)
        puzzle = self.chromedriver.find_element(By.CSS_SELECTOR, ARCED_SLIDE_PUZZLE_IMAGE_SELECTOR)
        
        slide_bar_width = self._get_element_bounding_box(slide_bar)["width"]
        puzzle_img_bounding_box = self._get_element_bounding_box(puzzle)

        actions = ActionChains(self.chromedriver, duration=0)
        actions.click_and_hold(slide_button)
        pixel_step = 4
        trajectory: list[ArcedSlideTrajectoryElement] = []
        for pixel in range(0, int(slide_bar_width), pixel_step):
            actions.move_by_offset(pixel_step, 0)
            trajectory.append(
                self._get_arced_slide_trajectory_element(
                    pixel,
                    slide_bar_width,
                    puzzle_img_bounding_box,
                    slider_piece
                )
            )
        actions.release().perform()
        return trajectory

    def _get_arced_slide_trajectory_element(
            self,
            current_slider_pixel: int,
            slide_bar_width: float,
            large_img_bounding_box: FloatRect,
            slider_piece_locator: WebElement, 
        ) -> ArcedSlideTrajectoryElement:
        """Compute current slider trajectory element by extracting information on the 
        slide button location, the piece rotation, and the piece location"""
        slider_piece_bounding_box = self._get_element_bounding_box(slider_piece_locator)
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


    def _get_element_bounding_box(self, e: WebElement) -> FloatRect:
        loc = e.location
        size = e.size
        return {"x": loc["x"], "y": loc["y"], "width": size["width"], "height": size["height"]}

    def _compute_puzzle_slide_distance(self, proportion_x: float) -> int:
        e = self.page.locator("#captcha-verify-image")
        box = e.bounding_box()
        if box:
            return int(proportion_x * box["width"])
        raise AttributeError("#captcha-verify-image was found but had no bouding box")
