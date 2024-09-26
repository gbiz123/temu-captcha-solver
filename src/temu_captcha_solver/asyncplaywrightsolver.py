"""This class handles the captcha solving for playwright users"""

import json
import base64
import logging
from math import pi
import random
from typing import Any, Literal, override
from playwright.async_api import FloatRect, Locator, Page, expect
from playwright.async_api import TimeoutError
import asyncio

from .selectors import (
    ARCED_SLIDE_BAR_SELECTOR,
    ARCED_SLIDE_BUTTON_SELECTOR,
    ARCED_SLIDE_PIECE_CONTAINER_SELECTOR,
    ARCED_SLIDE_PIECE_IMAGE_SELECTOR,
    ARCED_SLIDE_PUZZLE_IMAGE_SELECTOR,
    ARCED_SLIDE_SELECTORS,
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

from .downloader import download_image_b64
from .asyncsolver import AsyncSolver
from .api import ApiClient


class AsyncPlaywrightSolver(AsyncSolver):

    client: ApiClient
    page: Page

    def __init__(
            self,
            page: Page,
            sadcaptcha_api_key: str,
            headers: dict[str, Any] | None = None, 
            proxy: str | None = None
        ) -> None:
        self.page = page
        self.client = ApiClient(sadcaptcha_api_key)
        self.headers = headers
        self.proxy = proxy

    @override
    async def captcha_is_present(self, timeout: int = 15) -> bool:
        try:
            captcha_locator = self.page.locator(CAPTCHA_WRAPPERS[0])
            await expect(captcha_locator.first).to_have_count(1, timeout=timeout * 1000)
            return True
        except (TimeoutError, AssertionError):
            return False

    @override
    async def captcha_is_not_present(self, timeout: int = 15) -> bool:
        try:
            captcha_locator = self.page.locator(CAPTCHA_WRAPPERS[0])
            await expect(captcha_locator.first).to_have_count(0, timeout=timeout * 1000)
            return True
        except (TimeoutError, AssertionError):
            return False

    @override
    async def identify_captcha(self) -> Literal["puzzle", "arced_slide"]:
        for _ in range(15):
            if await self._any_selector_in_list_present(PUZZLE_SELECTORS):
                logging.debug("detected puzzle")
                return "puzzle"
            elif await self._any_selector_in_list_present(ARCED_SLIDE_SELECTORS):
                logging.debug("detected arced slide")
                return "arced_slide"
            else:
                await asyncio.sleep(2)
        raise ValueError("Neither puzzle, or arced slide was present")

    @override
    async def solve_puzzle(self, retries: int = 3) -> None:
        """Temu puzzle is special because the pieces shift when pressing the slider button.
        Therefore we must send the pictures after pressing the button. """
        raise NotImplementedError()

    @override
    async def solve_arced_slide(self) -> None:
        """Solves the arced slide puzzle. This challenge is similar to the puzzle
        challenge, but the puzzle piece travels in an arc, hence then name arced slide.
        The API expects the b64 encoded puzzle and piece images, along with data about the piece's
        trajectory in a list of ArcedSlideTrajectoryElements.

        This function will get the b64 encoded images, and will 'sweep' the slide
        bar to determine the piece's trajectory. Then it sends the data to the API
        and consumes the response.
        
        Determines slider trajectory by dragging the slider element across the entire box,
        and computing the ArcedSlideTrajectoryElement at each location."""
        if not await self._any_selector_in_list_present([ARCED_SLIDE_PUZZLE_IMAGE_SELECTOR]):
            logging.debug("Went to solve arced slide but " + ARCED_SLIDE_PUZZLE_IMAGE_SELECTOR + "was not present")
            return
        slide_button_locator = self.page.locator(ARCED_SLIDE_BUTTON_SELECTOR)
        slider_piece_locator = self.page.locator(ARCED_SLIDE_PIECE_CONTAINER_SELECTOR)
        slide_bar_bounding_box = await self._get_element_bounding_box(ARCED_SLIDE_BAR_SELECTOR)
        slide_bar_width = slide_bar_bounding_box["width"]
        puzzle_img_bounding_box = await self._get_element_bounding_box(ARCED_SLIDE_PUZZLE_IMAGE_SELECTOR)
        await self._move_mouse_to_element_center(slide_button_locator)
        await self.page.mouse.down()
        trajectory: list[ArcedSlideTrajectoryElement] = []
        step_size_pixels = 1

        # get trajectory
        slide_button_box = await self._get_element_bounding_box(ARCED_SLIDE_BUTTON_SELECTOR)
        start_x = slide_button_box["x"]
        start_y = slide_button_box["y"]
        for pixel in range(0, int(slide_bar_width), step_size_pixels):
            await self.page.mouse.move(start_x + pixel, start_y)
            trajectory.append(
                await self._get_arced_slide_trajectory_element(
                    pixel,
                    puzzle_img_bounding_box,
                    slider_piece_locator
                )
            )

        # move back to piece center
        # await self._move_mouse_to_element_center(slide_button_locator) 
        #
        # send request
        puzzle = await self.get_b64_img_from_src(ARCED_SLIDE_PUZZLE_IMAGE_SELECTOR)
        piece = await self.get_b64_img_from_src(ARCED_SLIDE_PIECE_IMAGE_SELECTOR)
        request = ArcedSlideCaptchaRequest(
            puzzle_image_b64=puzzle,
            piece_image_b64=piece,
            slide_piece_trajectory=trajectory
        )
        with open("myreq.json", "w") as f:
            json.dump(request.model_dump(), f)
        solution = self.client.arced_slide(request)

        # move mouse back to correct location
        # slide_x_proportion is just the number of pixels traveled to get to the solution. 
        # The name will be changed to "x_location" or something
        await self.page.mouse.move(start_x + solution.slide_x_proportion, start_y, steps=100)

        await self.page.mouse.up()
        if await self.captcha_is_not_present(timeout=5):
            return
        else:
            await asyncio.sleep(5)

    async def _click_proportional(
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
        await self.page.mouse.move(x_origin + x_offset, y_origin + y_offset)
        await asyncio.sleep(random.randint(1, 10) / 11)
        await self.page.mouse.down()
        await asyncio.sleep(0.001337)
        await self.page.mouse.up()
        await asyncio.sleep(random.randint(1, 10) / 11)

    async def _drag_element_horizontal_with_overshoot(self, css_selector: str, x: int, frame_selector: str | None = None) -> None:
        if frame_selector:
            e = self.page.frame_locator(frame_selector).locator(css_selector)
        else:
            e = self.page.locator(css_selector)
        box = await e.bounding_box()
        if not box:
            raise AttributeError("Element had no bounding box")
        start_x = (box["x"] + (box["width"] / 1.337))
        start_y = (box["y"] +  (box["height"] / 1.337))
        await self.page.mouse.move(start_x, start_y)
        await asyncio.sleep(random.randint(1, 10) / 11)
        await self.page.mouse.down()
        await asyncio.sleep(random.randint(1, 10) / 11)
        await self.page.mouse.move(start_x + x, start_y, steps=100)
        overshoot = random.choice([1, 2, 3, 4])
        await self.page.mouse.move(start_x + x + overshoot, start_y + overshoot, steps=100) # overshoot forward
        await self.page.mouse.move(start_x + x, start_y, steps=75) # overshoot back
        await asyncio.sleep(0.001)
        await self.page.mouse.up()

    async def _any_selector_in_list_present(self, selectors: list[str]) -> bool:
        for selector in selectors:
            for ele in await self.page.locator(selector).all():
                if await ele.is_visible():
                    logging.debug("Detected selector: " + selector + " from list " + ", ".join(selectors))
                    return True
        logging.debug("No selector in list found: " + ", ".join(selectors))
        return False

    async def _get_arced_slide_trajectory_element(
            self,
            current_slider_pixel: int,
            large_img_bounding_box: FloatRect,
            slider_piece_locator: Locator, 
        ) -> ArcedSlideTrajectoryElement:
        """Compute current slider trajectory element by extracting information on the 
        slide button location, the piece rotation, and the piece location"""
        slider_piece_bounding_box = await slider_piece_locator.bounding_box()
        if not slider_piece_bounding_box:
            raise ValueError("Bouding box for slider image was None")
        slider_piece_style = await slider_piece_locator.get_attribute("style")
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
        logging.debug(f"top_corner={piece_left}, {piece_top}, center={piece_center_x}, {piece_center_y}, ctr_in_container={x_in_container}, {y_in_container}  prop_center={piece_center.proportion_x}, {piece_center.proportion_y}, container_size={container_width}, {container_height}")
        return ArcedSlideTrajectoryElement(
            slider_button_proportion_x=current_slider_pixel,
            piece_rotation_angle=rotate_angle,
            piece_center=piece_center
        )

    async def _get_element_bounding_box(self, selector: str) -> FloatRect:
        box = await self.page.locator(selector).bounding_box()
        if box is None:
            raise ValueError("Bounding box for slide bar was none")
        return box

    async def _move_mouse_to_element_center(self, ele: Locator, x_offset: float = 0, y_offset: int = 0) -> None:
        box = await ele.bounding_box()
        if box is None:
            raise ValueError("Bounding box for element was none")
        x, y = get_center(box["x"], box["y"], box["width"], box["height"])
        await self.page.mouse.move(x + x_offset, y + y_offset)

    @override
    async def get_b64_img_from_src(self, selector: str) -> str:
        """Get the source of b64 image element and return the portion after the data:image/png;base64,"""
        e = self.page.locator(selector)
        url = await e.get_attribute("src")
        if not url:
            raise ValueError("element " + selector + " had no url")
        _, data = url.split(",")
        return data

    async def _compute_puzzle_slide_distance(self, proportion_x: float) -> int:
        e = self.page.locator("#captcha-verify-image")
        box = await e.bounding_box()
        if box:
            return int(proportion_x * box["width"])
        raise AttributeError("#captcha-verify-image was found but had no bouding box")

    async def _get_element_width(self, selector: str) -> float:
        e = self.page.locator(selector)
        box = await e.bounding_box()
        if box:
            return int(box["width"])
        raise AttributeError(".captcha_verify_slide--slidebar was found but had no bouding box")

