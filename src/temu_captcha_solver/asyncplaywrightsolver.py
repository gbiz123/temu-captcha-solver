"""This class handles the captcha solving for playwright users"""

import logging
import random
from typing import Literal
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

from .asyncsolver import AsyncSolver
from .api import ApiClient
from .downloader import download_image_b64
from .urls import ARCED_SLIDE_URL_PATTERN


class AsyncPlaywrightSolver(AsyncSolver):

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

    async def captcha_is_present(self, timeout: int = 15) -> bool:
        try:
            captcha_locator = self.page.locator(CAPTCHA_WRAPPERS[0])
            await expect(captcha_locator.first).to_have_count(1, timeout=timeout * 1000)
            return True
        except (TimeoutError, AssertionError):
            return False

    async def captcha_is_not_present(self, timeout: int = 15) -> bool:
        try:
            captcha_locator = self.page.locator(CAPTCHA_WRAPPERS[0])
            await expect(captcha_locator.first).to_have_count(0, timeout=timeout * 1000)
            return True
        except (TimeoutError, AssertionError):
            return False

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

    async def solve_puzzle(self, retries: int = 3) -> None:
        """Temu puzzle is special because the pieces shift when pressing the slider button.
        Therefore we must send the pictures after pressing the button. """
        raise NotImplementedError()

    async def solve_arced_slide(self) -> None:
        """Solves the arced slide puzzle. This challenge is similar to the puzzle
        challenge, but the puzzle piece travels in an arc, hence then name arced slide.
        The API expects the b64 encoded puzzle and piece images, along with data about the piece's
        trajectory in a list of ArcedSlideTrajectoryElements.

        This function will get the b64 encoded images, and will 'sweep' the slide
        bar to determine the piece's trajectory. Then it sends the data to the API
        and consumes the response.
        """
        if not await self._any_selector_in_list_present([ARCED_SLIDE_PUZZLE_IMAGE_SELECTOR]):
            logging.debug("Went to solve arced slide but " + ARCED_SLIDE_PUZZLE_IMAGE_SELECTOR + "was not present")
            return
        puzzle = await self.get_b64_img_from_src(ARCED_SLIDE_PUZZLE_IMAGE_SELECTOR)
        piece = await self.get_b64_img_from_src(ARCED_SLIDE_PIECE_IMAGE_SELECTOR)
        trajectory = await self._get_arced_slide_trajectory()
        request = ArcedSlideCaptchaRequest(
            puzzle_image_b64=puzzle,
            piece_image_b64=piece,
            slide_piece_trajectory=trajectory
        )
        solution = self.client.arced_slide(request)
        distance = await self._compute_puzzle_slide_distance(solution.slide_x_proportion)
        await self._drag_element_horizontal_with_overshoot(ARCED_SLIDE_BUTTON_SELECTOR, distance)
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

    async def _get_arced_slide_trajectory(self) -> list[ArcedSlideTrajectoryElement]:
        """Determines slider trajectory by dragging the slider element across the entire box,
        and computing the ArcedSlideTrajectoryElement at each location."""
        slide_button_locator = self.page.locator(ARCED_SLIDE_BUTTON_SELECTOR)
        slider_piece_locator = self.page.locator(ARCED_SLIDE_PIECE_CONTAINER_SELECTOR)
        slide_bar_width = await self._get_element_width(ARCED_SLIDE_BAR_SELECTOR)
        puzzle_img_bounding_box = await self._get_element_bounding_box(ARCED_SLIDE_PUZZLE_IMAGE_SELECTOR)
        await self._move_mouse_to_element_center(slide_button_locator)
        await self.page.mouse.down()
        trajectory: list[ArcedSlideTrajectoryElement] = []
        for pixel in range(0, int(slide_bar_width), 4):
            await self._move_mouse_to_element_center(slide_button_locator, x_offset=pixel)
            trajectory.append(
                await self._get_arced_slide_trajectory_element(
                    pixel,
                    slide_bar_width,
                    puzzle_img_bounding_box,
                    slider_piece_locator
                )
            )
        await self.page.mouse.up()
        return trajectory

    async def _get_arced_slide_trajectory_element(
            self,
            current_slider_pixel: int,
            slide_bar_width: float,
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
        top = slider_piece_bounding_box["x"]
        left = slider_piece_bounding_box["y"]
        width = slider_piece_bounding_box["width"]
        height = slider_piece_bounding_box["height"]
        container_width = large_img_bounding_box["width"]
        container_height = large_img_bounding_box["height"]
        piece_center_x, piece_center_y = get_center(left, top, width, height)
        piece_center = xy_to_proportional_point(piece_center_x, piece_center_y, container_width, container_height)
        return ArcedSlideTrajectoryElement(
            slider_button_proportion_x=current_slider_pixel / slide_bar_width,
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
        await self.page.mouse.move(
            *get_center(
                box["x"] + x_offset,
                box["y"] + y_offset,
                box["width"],
                box["height"]
            )
        )

    async def get_b64_img_from_src(self, selector: str) -> str:
        """Get the source of b64 image element and return the portion after the data:image/png;base64,"""
        e = self.page.locator(selector)
        url = await e.get_attribute("src")
        if not url:
            raise ValueError("element " + selector + " had no url")
        return url.split(",", 1)[1]

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

