"""This class handles the captcha solving for selenium users"""

import logging
import math
import random
import time
from typing import Any, Literal, override
from playwright.sync_api import FloatRect

from selenium.webdriver import ActionChains, Chrome
from selenium.webdriver.common.actions.action_builder import ActionBuilder
from selenium.webdriver.common.by import By
from selenium.webdriver.remote.webelement import WebElement

from .captchatype import CaptchaType

from .geometry import(
    get_box_center,
    get_center,
    piece_is_not_moving,
    rotate_angle_from_style,
    xy_to_proportional_point
) 

from .selectors import (
    ARCED_SLIDE_BAR_SELECTOR,
    ARCED_SLIDE_BUTTON_SELECTOR,
    ARCED_SLIDE_PIECE_CONTAINER_SELECTOR,
    ARCED_SLIDE_PIECE_IMAGE_SELECTOR,
    ARCED_SLIDE_PUZZLE_IMAGE_SELECTOR,
    CAPTCHA_WRAPPERS,
    PUZZLE_BAR_SELECTOR,
    PUZZLE_BUTTON_SELECTOR,
    PUZZLE_PIECE_IMAGE_SELECTOR,
    PUZZLE_PUZZLE_IMAGE_SELECTOR,
) 
 
from .models import ArcedSlideCaptchaRequest, ArcedSlideTrajectoryElement
from .api import ApiClient
from .downloader import download_image_b64
from .syncsolver import SyncSolver

LOGGER = logging.getLogger(__name__)

class SeleniumSolver(SyncSolver):

    client: ApiClient
    chromedriver: Chrome

    STEP_SIZE_PIXELS = 1

    def __init__(
            self, 
            chromedriver: Chrome,
            sadcaptcha_api_key: str,
            headers: dict[str, Any] | None = None,
            proxy: str | None = None
        ) -> None:
        self.chromedriver = chromedriver
        self.client = ApiClient(sadcaptcha_api_key)
        self.headers = headers
        self.proxy = proxy

    def captcha_is_present(self, timeout: int = 15) -> bool:
        for _ in range(timeout * 2):
            if self.any_selector_in_list_present(CAPTCHA_WRAPPERS):
                print("Captcha detected")
                return True
            time.sleep(0.5)
        LOGGER.debug("Captcha not found")
        return False

    def captcha_is_not_present(self, timeout: int = 15) -> bool:
        for _ in range(timeout * 2):
            if len(self.chromedriver.find_elements(By.CSS_SELECTOR, CAPTCHA_WRAPPERS[0])) == 0:
                print("Captcha not present")
                return True
            time.sleep(0.5)
        LOGGER.debug("Captcha not found")
        return False

    def solve_puzzle(self) -> None:
        """Slide 10 pixels, then grab the puzzle and piece, then make API call and consume the response"""
        slide_button = self.chromedriver.find_element(By.CSS_SELECTOR, PUZZLE_BUTTON_SELECTOR)
        actions = ActionChains(self.chromedriver, duration=100)
        _ = actions.move_to_element(slide_button) \
                .click_and_hold()
        start_distance = 10
        for pixel in range(start_distance):
            _ = actions.move_by_offset(1, int(random.gauss(1, 5))) \
                    .pause(max(0, random.gauss(0.01, 0.005)))
        actions.perform()
        LOGGER.debug("dragged 10 pixels")
        puzzle_image = self.get_b64_img_from_src(PUZZLE_PUZZLE_IMAGE_SELECTOR)
        piece_image = self.get_b64_img_from_src(PUZZLE_PIECE_IMAGE_SELECTOR)
        resp = self.client.puzzle(puzzle_image, piece_image)
        slide_bar_width = self._get_element_bounding_box(self.chromedriver.find_element(By.CSS_SELECTOR, PUZZLE_BAR_SELECTOR))["width"]
        pixel_distance = int(resp.slide_x_proportion * slide_bar_width)
        LOGGER.debug(f"will continue to drag {pixel_distance} more pixels")
        actions = ActionChains(self.chromedriver, duration=5)
        for pixel in range(start_distance, pixel_distance):
            _ = actions.move_by_offset(1, int(random.gauss(1, 5))) \
                    .pause(max(0, random.gauss(0.01, 0.005)))
        actions.release().perform()
        LOGGER.debug("done")

    def solve_arced_slide(self) -> None:
        """Solves the arced slide puzzle. This challenge is similar to the puzzle
        challenge, but the puzzle piece travels in an arc, hence then name arced slide.
        The API expects the b64 encoded puzzle and piece images, along with data about the piece's
        trajectory in a list of ArcedSlideTrajectoryElements.

        This function will get the b64 encoded images, and will 'sweep' the slide
        bar to determine the piece's trajectory. Then it sends the data to the API
        and consumes the response.
        """ 
        slide_button_element = self.chromedriver.find_element(By.CSS_SELECTOR, ARCED_SLIDE_BUTTON_SELECTOR)
        slide_button_bbox = self._get_element_bounding_box(slide_button_element)
        start_x = slide_button_bbox["x"] + (slide_button_bbox["width"] / 2)
        actions = ActionChains(self.chromedriver, duration=0)

        # Forward pass
        _ = actions.click_and_hold(self.chromedriver.find_element(By.CSS_SELECTOR, ARCED_SLIDE_BUTTON_SELECTOR))
        request = self._gather_arced_slide_request_data(actions)
        solution = self.client.arced_slide(request)
        LOGGER.debug("Arced slide solution: " + str(solution.pixels_from_slider_origin))

        # Backward pass
        slide_button_bbox = self._get_element_bounding_box(slide_button_element)
        end_x = slide_button_bbox["x"] + (slide_button_bbox["width"] / 2)
        solution_distance_backwards = int(end_x - start_x - solution.pixels_from_slider_origin)
        LOGGER.debug(f"Moving mouse backwards by {solution_distance_backwards} pixels")
        actions.move_to_element(slide_button_element).perform() # Return mouse to button
        for _ in range(solution_distance_backwards):
            _ = actions \
                    .move_by_offset(-1, -1) \
                    .pause(0.01)
        actions.release().perform()

    def get_b64_img_from_src(self, selector: str) -> str:
        """Get the source of b64 image element and return the portion after the data:image/png;base64,"""
        e = self.chromedriver.find_element(By.CSS_SELECTOR, selector)
        url = e.get_attribute("src")
        if not url:
            raise ValueError("Could not get image source for " + selector)
        return url.split(",")[1]

    def _move_mouse_horizontal_with_overshoot(self, x: int, actions: ActionChains) -> None:
        time.sleep(0.1)
        for _ in range(0, x - 15):
            _ = actions.move_by_offset(1, 0)
        for _ in range(0, 20):
            _ = actions.move_by_offset(1, 0)
            _ = actions.pause(0.01)
        _ = actions.pause(0.7)
        for _ in range(0, 5):
            _ = actions.move_by_offset(-1, 0)
            _ = actions.pause(0.05)
        _ = actions.pause(0.1)
        actions.perform()

    
    def any_selector_in_list_present(self, selectors: list[str]) -> bool:
        for selector in selectors:
            for ele in self.chromedriver.find_elements(By.CSS_SELECTOR, selector):
                if ele.is_displayed():
                    LOGGER.debug("Detected selector: " + selector + " from list " + ", ".join(selectors))
                    return True
        LOGGER.debug("No selector in list found: " + ", ".join(selectors))
        return False

    def _gather_arced_slide_request_data(self, actions: ActionChains) -> ArcedSlideCaptchaRequest:
        """Get the images and trajectory for arced slide request"""
        puzzle = self.get_b64_img_from_src(ARCED_SLIDE_PUZZLE_IMAGE_SELECTOR)
        piece = self.get_b64_img_from_src(ARCED_SLIDE_PIECE_IMAGE_SELECTOR)
        trajectory = self._get_slide_piece_trajectory(actions)
        return ArcedSlideCaptchaRequest(
            puzzle_image_b64=puzzle,
            piece_image_b64=piece,
            slide_piece_trajectory=trajectory
        )

    def _get_slide_piece_trajectory(self, actions: ActionChains) -> list[ArcedSlideTrajectoryElement]:
        """Determines slider trajectory by dragging the slider element across the entire box,
        and computing the ArcedSlideTrajectoryElement at each location."""
        slide_button = self.chromedriver.find_element(By.CSS_SELECTOR, ARCED_SLIDE_BUTTON_SELECTOR)
        slider_piece = self.chromedriver.find_element(By.CSS_SELECTOR, ARCED_SLIDE_PIECE_CONTAINER_SELECTOR)
        slide_bar = self.chromedriver.find_element(By.CSS_SELECTOR, ARCED_SLIDE_BAR_SELECTOR)
        puzzle = self.chromedriver.find_element(By.CSS_SELECTOR, ARCED_SLIDE_PUZZLE_IMAGE_SELECTOR)
        
        slide_bar_width = self._get_element_bounding_box(slide_bar)["width"]
        puzzle_img_bounding_box = self._get_element_bounding_box(puzzle)

        _ = actions.click_and_hold(slide_button)
        trajectory: list[ArcedSlideTrajectoryElement] = []
        times_piece_did_not_move = 0
        for pixel in range(0, int(slide_bar_width), self.STEP_SIZE_PIXELS):
            actions \
                .move_by_offset(self.STEP_SIZE_PIXELS, 1) \
                .pause(0.01) \
                .perform()
            trajectory.append(
                self._get_arced_slide_trajectory_element(
                    pixel,
                    puzzle_img_bounding_box,
                    slider_piece
                )
            )
            if not len(trajectory) > 100:
                continue
            if piece_is_not_moving(trajectory):
                times_piece_did_not_move += 1
            else:
                times_piece_did_not_move = 0
            if times_piece_did_not_move >= 10:
                break
        actions.perform()
        return trajectory


    def _get_arced_slide_trajectory_element(
            self,
            current_slider_pixel: int,
            large_img_bounding_box: FloatRect,
            slider_piece_element: WebElement, 
        ) -> ArcedSlideTrajectoryElement:
        """Compute current slider trajectory element by extracting information on the 
        slide button location, the piece rotation, and the piece location"""
        slider_piece_bounding_box = self._get_element_bounding_box(slider_piece_element)
        slider_piece_style = slider_piece_element.get_attribute("style")
        if not slider_piece_style:
            raise ValueError("Slider piece style was None")
        rotate_angle = rotate_angle_from_style(slider_piece_style)
        piece_top = slider_piece_bounding_box["y"]
        piece_left = slider_piece_bounding_box["x"]
        width = slider_piece_bounding_box["width"]
        height = slider_piece_bounding_box["height"]
        piece_center_x, piece_center_y = get_center(piece_left, piece_top, width, height)
        container_x = large_img_bounding_box["x"]
        container_y = large_img_bounding_box["y"]
        container_width = large_img_bounding_box["width"]
        container_height = large_img_bounding_box["height"]
        x_in_container = piece_center_x - container_x
        y_in_container = piece_center_y - container_y
        piece_center = xy_to_proportional_point(x_in_container, y_in_container, container_width, container_height)
        LOGGER.debug(f"top_corner={piece_left}, {piece_top}, center={piece_center_x}, {piece_center_y}, ctr_in_container={x_in_container}, {y_in_container}  prop_center={piece_center.proportion_x}, {piece_center.proportion_y}, container_size={container_width}, {container_height}")
        return ArcedSlideTrajectoryElement(
            pixels_from_slider_origin=current_slider_pixel,
            piece_rotation_angle=rotate_angle,
            piece_center=piece_center
        )
        

    def _get_element_bounding_box(self, e: WebElement) -> FloatRect:
        loc = e.location
        size = e.size
        return {"x": loc["x"], "y": loc["y"], "width": size["width"], "height": size["height"]}
