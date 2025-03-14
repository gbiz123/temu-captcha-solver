"""This class handles the captcha solving for playwright users"""

import logging
import math
import random
from typing import Any
import warnings
from playwright.async_api import FloatRect, Locator, Page, expect
from playwright.async_api import TimeoutError
import asyncio

from temu_captcha_solver.async_plawright_util import wait_for_locator_to_be_stable
from temu_captcha_solver.parsers import get_list_of_objects_of_interest

from .selectors import (
    ARCED_SLIDE_BUTTON_SELECTOR,
    ARCED_SLIDE_PIECE_CONTAINER_SELECTOR,
    ARCED_SLIDE_PIECE_IMAGE_SELECTOR,
    ARCED_SLIDE_PUZZLE_IMAGE_SELECTOR,
    CAPTCHA_PRESENCE_INDICATORS,
    PUZZLE_BUTTON_SELECTOR,
    PUZZLE_PIECE_IMAGE_SELECTOR,
    PUZZLE_PUZZLE_IMAGE_SELECTOR,
    SEMANTIC_SHAPES_CHALLENGE_TEXT,
    SEMANTIC_SHAPES_IMAGE,
    SEMANTIC_SHAPES_ELEMENTS_INSIDE_CHALLENGE,
    SEMANTIC_SHAPES_REFRESH_BUTTON,
    SWAP_TWO_IMAGE,
    THREE_BY_THREE_CONFIRM_BUTTON,
    THREE_BY_THREE_IMAGE,
    THREE_BY_THREE_TEXT,
) 

from .geometry import (
    get_box_center,
    get_center,
    piece_is_not_moving,
    rotate_angle_from_style,
    xy_to_proportional_point
) 

from .models import (
    ArcedSlideCaptchaRequest,
    ArcedSlideTrajectoryElement,
    MultiPointResponse,
    SemanticShapesRequest,
    SwapTwoRequest,
    ThreeByThreeCaptchaRequest,
    dump_to_json
) 

from .asyncsolver import AsyncSolver
from .api import ApiClient, BadRequest


LOGGER = logging.getLogger(__name__)

class AsyncPlaywrightSolver(AsyncSolver):

    client: ApiClient
    page: Page

    def __init__(
            self,
            page: Page,
            sadcaptcha_api_key: str,
            headers: dict[str, Any] | None = None, 
            proxy: str | None = None,
            dump_requests: bool = False,
            mouse_step_size: int = 5
        ) -> None:
        warnings.warn(
            "AsyncPlaywrightSolver is deprecated. Please use 'make_async_playwright_solver_context()' instead for a more reliable experience.")
        self.page = page
        self.client = ApiClient(sadcaptcha_api_key)
        self.headers = headers
        self.proxy = proxy
        self.mouse_step_size = mouse_step_size
        super().__init__(dump_requests)

    
    async def captcha_is_present(self, timeout: int = 15) -> bool:
        try:
            captcha_locator = self.page.locator(CAPTCHA_PRESENCE_INDICATORS[0])
            for selector in CAPTCHA_PRESENCE_INDICATORS:
                captcha_locator = captcha_locator.or_(self.page.locator(selector))
            await expect(captcha_locator.first).to_have_count(1, timeout=timeout * 1000)
            return True
        except (TimeoutError, AssertionError):
            return False

    
    async def captcha_is_not_present(self, timeout: int = 15) -> bool:
        try:
            captcha_locator = self.page.locator(CAPTCHA_PRESENCE_INDICATORS[0])
            for selector in CAPTCHA_PRESENCE_INDICATORS:
                captcha_locator = captcha_locator.or_(self.page.locator(selector))
            await expect(captcha_locator.first).to_have_count(0, timeout=timeout * 1000)
            return True
        except (TimeoutError, AssertionError):
            return False

    
    async def solve_puzzle(self, retries: int = 3) -> None:
        """Temu puzzle is special because the pieces shift when pressing the slider button.
        Therefore we must send the pictures after pressing the button. """
        iframe_selector = "iframe" if await self.iframe_present() else None
        button_bbox = await self._get_element_bounding_box(PUZZLE_BUTTON_SELECTOR, iframe_selector=iframe_selector)
        start_x, start_y = get_box_center(button_bbox)
        await self.page.mouse.move(start_x, start_y)
        await self.page.mouse.down()
        start_distance = 10
        for pixel in range(start_distance):
            await self.page.mouse.move(start_x + start_distance, start_y + math.log(1 + pixel))
            await asyncio.sleep(0.05)
        LOGGER.debug("dragged 10 pixels")
        puzzle_image = await self.get_b64_img_from_src(PUZZLE_PUZZLE_IMAGE_SELECTOR, iframe_selector=iframe_selector)
        piece_image = await self.get_b64_img_from_src(PUZZLE_PIECE_IMAGE_SELECTOR, iframe_selector=iframe_selector)
        resp = self.client.puzzle(puzzle_image, piece_image)
        slide_bar_width = await self._get_puzzle_slide_bar_width(iframe_selector=iframe_selector)
        pixel_distance = int(resp.slide_x_proportion * slide_bar_width)
        LOGGER.debug(f"will continue to drag {pixel_distance} more pixels")
        for pixel in range(start_distance, pixel_distance):
            await self.page.mouse.move(start_x + pixel, start_y + math.log(1 + pixel))
            await asyncio.sleep(0.02)
        await self.page.mouse.up()
        LOGGER.debug("done")

    
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
        slide_button_locator = self.page.locator(ARCED_SLIDE_BUTTON_SELECTOR)
        await self._move_mouse_to_element_center(slide_button_locator)
        await self.page.mouse.down()
        slide_button_box = await self._get_element_bounding_box(ARCED_SLIDE_BUTTON_SELECTOR)
        start_x = slide_button_box["x"]
        start_y = slide_button_box["y"]
        request = await self._gather_arced_slide_request_data(start_x, start_y)
        solution = self.client.arced_slide(request)
        await self._drag_mouse_horizontal_with_overshoot(solution.pixels_from_slider_origin, start_x, start_y)
        await self.page.mouse.up()
    

    async def solve_three_by_three(self) -> None:
        image_locators = await self.page.locator(THREE_BY_THREE_IMAGE).all()
        images_b64: list[str] = []
        for image_locator in image_locators:
            images_b64.append(await self.get_b64_img_from_src(image_locator))
        challenge_text = await self._get_element_text(THREE_BY_THREE_TEXT)
        objects = get_list_of_objects_of_interest(challenge_text)
        request = ThreeByThreeCaptchaRequest(objects_of_interest=objects, images=images_b64)
        if self.dump_requests:
            dump_to_json(request, "three_by_three_request.json")
        resp = self.client.three_by_three(request)
        for i in resp.solution_indices:
            image_locator = self.page.locator(f"img[src*=\"{images_b64[i]}\"]") # Where src matches the desired image
            await image_locator.click()
            await asyncio.sleep(1.337)
        await self._click_proportional(THREE_BY_THREE_CONFIRM_BUTTON, 0.5, 0.5)

    async def solve_swap_two(self) -> None:
        """Click and drag, swap two to restore the image"""
        iframe_selector = "iframe" if await self.iframe_present() else None
        image_b64 = await self.get_b64_img_from_src(SWAP_TWO_IMAGE, iframe_selector=iframe_selector)
        request = SwapTwoRequest(image_b64=image_b64)
        if self.dump_requests:
            dump_to_json(request, "swap_two_request.json")
        resp = self.client.swap_two(request)
        await self._drag_proportional(SWAP_TWO_IMAGE, resp, iframe_selector=iframe_selector)

    async def solve_semantic_shapes(self) -> None:
        """Solves the shapes challenge where an image and some text are presented.
        Implements various checks to deal with strange behavior from temu captcha.
        For example, temu shows a loading icon which makes the challenge impossible to click."""
        for _ in range(3):
            iframe_selector = "iframe" if await self.iframe_present() else None
            try:
                for i in range(-3, 0):
                    LOGGER.debug(f"solving shapes in in {-1 * i}")
                    await asyncio.sleep(1)

                image_b64 = await self.get_b64_img_from_src(SEMANTIC_SHAPES_IMAGE, iframe_selector=iframe_selector)
                challenge = await self._get_element_text(SEMANTIC_SHAPES_CHALLENGE_TEXT, iframe_selector=iframe_selector)
                request = SemanticShapesRequest(image_b64=image_b64, challenge=challenge)
                
                if self.dump_requests:
                    dump_to_json(request, "semantic_shapes_request.json")
                
                resp = self.client.semantic_shapes(request)
                challenge_current = await self._get_element_text(SEMANTIC_SHAPES_CHALLENGE_TEXT, iframe_selector=iframe_selector)
                
                if challenge != challenge_current:
                    LOGGER.debug("challenge text has changed since making the initial request. refreshing to avoid clicking incorrect location")
                    await self._get_locator(SEMANTIC_SHAPES_REFRESH_BUTTON, iframe_selector=iframe_selector).click(force=True)
                    continue

                for point in resp.proportional_points:
                    red_dot_count = await self._count_red_dots(iframe_selector=iframe_selector)
                    for i in range(3):
                        await self._click_proportional(
                            SEMANTIC_SHAPES_IMAGE,
                            point.proportion_x,
                            point.proportion_y,
                            iframe_selector=iframe_selector 
                        )                
                        if red_dot_count == await self._count_red_dots(iframe_selector=iframe_selector):
                            LOGGER.debug("A new red dot did not appear. trying to click again in a slightly different location")
                            continue
                        else:
                            LOGGER.debug("A new red dot appeared")
                            break
                    await asyncio.sleep(1)
                    LOGGER.debug("clicked answer...")
                
                for i in range(-5, 0):
                    LOGGER.debug(f"validating answer in {-1 * i}")
                    await asyncio.sleep(1)

                if await self.captcha_is_present(1):
                    LOGGER.debug("captcha was still present after solving. This is normally because it's impossible to click in the region over the solution, and the click was not registered")
                    await self._get_locator(SEMANTIC_SHAPES_REFRESH_BUTTON, iframe_selector=iframe_selector).click(force=True)
                    continue
                
                LOGGER.debug("solved semantic shapes")
                return

            except BadRequest as e:
                LOGGER.debug("API was unable to solve, retrying. error message: " + str(e))
                await self._get_locator(SEMANTIC_SHAPES_REFRESH_BUTTON, iframe_selector=iframe_selector).click(force=True)
                await asyncio.sleep(3)

    
    async def any_selector_in_list_present(self, selectors: list[str], iframe_locator: str | None = None) -> bool:
        for selector in selectors:
            e = self._get_locator(selector, iframe_selector=iframe_locator)
            for ele in await e.all():
                if await ele.is_visible():
                    LOGGER.debug("Detected selector: " + selector + " from list " + ", ".join(selectors))
                    return True
        LOGGER.debug("No selector in list found: " + ", ".join(selectors))
        return False

    
    async def _gather_arced_slide_request_data(self, slide_button_center_x: float, slide_button_center_y: float) -> ArcedSlideCaptchaRequest:
        """Get the images and trajectory for arced slide request"""
        puzzle = await self.get_b64_img_from_src(ARCED_SLIDE_PUZZLE_IMAGE_SELECTOR)
        piece = await self.get_b64_img_from_src(ARCED_SLIDE_PIECE_IMAGE_SELECTOR)
        trajectory = await self._get_slide_piece_trajectory(slide_button_center_x, slide_button_center_y)
        return ArcedSlideCaptchaRequest(
            puzzle_image_b64=puzzle,
            piece_image_b64=piece,
            slide_piece_trajectory=trajectory
        )


    async def _get_slide_piece_trajectory(self, slide_button_center_x: float, slide_button_center_y: float) -> list[ArcedSlideTrajectoryElement]:
        """Sweep the button across the bar to determine the trajectory of the slide piece.
        Clicks and drags box, but does not release. Must pass the coordinates of the slide button."""
        slider_piece_locator = self.page.locator(ARCED_SLIDE_PIECE_CONTAINER_SELECTOR)
        slide_bar_width = await self._get_arced_slide_bar_width()
        puzzle_img_bounding_box = await self._get_element_bounding_box(ARCED_SLIDE_PUZZLE_IMAGE_SELECTOR)
        trajectory: list[ArcedSlideTrajectoryElement] = []

        times_piece_did_not_move = 0
        for pixel in range(0, int(slide_bar_width), self.mouse_step_size):
            await self.page.mouse.move(slide_button_center_x + pixel, slide_button_center_y - pixel)  # - pixel is to drag it diagonally
            await wait_for_locator_to_be_stable(slider_piece_locator)
            trajectory_element = await self._get_arced_slide_trajectory_element(
                pixel,
                puzzle_img_bounding_box,
                slider_piece_locator
            )
            trajectory.append(trajectory_element)
            if not len(trajectory) > 100 / self.mouse_step_size:
                continue
            if piece_is_not_moving(trajectory):
                times_piece_did_not_move += 1
            else:
                times_piece_did_not_move = 0
            if times_piece_did_not_move >= 10:
                break
        return trajectory

    async def _get_puzzle_slide_bar_width(self, iframe_selector: str | None = None) -> float:
        """Gets the width of the puzzle slide bar from the width of the image. 
        The slide bar is always the same as the image. 
        We do not get the width of the bar element itself, because the css selector varies from region to region."""
        bg_image_bounding_box = await self._get_element_bounding_box(PUZZLE_PUZZLE_IMAGE_SELECTOR,
                                                                     iframe_selector=iframe_selector)
        slide_bar_width = bg_image_bounding_box["width"]
        return slide_bar_width

    async def _get_arced_slide_bar_width(self, iframe_selector: str | None = None) -> float:
        """Gets the width of the arced slide bar from the width of the image. 
        The slide bar is always the same as the image. 
        We do not get the width of the bar element itself, because the css selector varies from region to region."""
        bg_image_bounding_box = await self._get_element_bounding_box(ARCED_SLIDE_PUZZLE_IMAGE_SELECTOR,
                                                                     iframe_selector=iframe_selector)
        slide_bar_width = bg_image_bounding_box["width"]
        return slide_bar_width

    async def _click_proportional(
            self,
            selector: str,
            proportion_x: float,
            proportion_y: float,
            iframe_selector: str | None = None
        ) -> None:
        """Click an element inside its bounding box at a point defined by the proportions of x and y
        to the width and height of the entire element

        Args:
            element: FloatRect to click inside
            proportion_x: float from 0 to 1 defining the proportion x location to click 
            proportion_y: float from 0 to 1 defining the proportion y location to click 
        """
        bounding_box = await self._get_element_bounding_box(selector, iframe_selector=iframe_selector)
        x_offset = (proportion_x * bounding_box["width"])
        y_offset = (proportion_y * bounding_box["height"]) 
        await self._get_locator(selector, iframe_selector=iframe_selector).click(position={"x": x_offset, "y": y_offset}, force=True)
        LOGGER.debug(f"clicked {selector} at offset {x_offset}, {y_offset}")
    

    async def _drag_mouse_horizontal_with_overshoot(self, x_distance: int, start_x_coord: float, start_y_coord: float) -> None:
        await self.page.mouse.move(start_x_coord + x_distance, start_y_coord, steps=100)
        overshoot = random.choice([1, 2, 3])
        await self.page.mouse.move(start_x_coord + x_distance + overshoot, start_y_coord + overshoot, steps=100) # overshoot forward
        await self.page.mouse.move(start_x_coord + x_distance, start_y_coord, steps=75) # overshoot back
        await asyncio.sleep(0.2)
        await self.page.mouse.up()

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
        LOGGER.debug(f"top_corner={piece_left}, {piece_top}, center={piece_center_x}, {piece_center_y}, ctr_in_container={x_in_container}, {y_in_container}  prop_center={piece_center.proportion_x}, {piece_center.proportion_y}, container_size={container_width}, {container_height}")
        return ArcedSlideTrajectoryElement(
            pixels_from_slider_origin=current_slider_pixel,
            piece_rotation_angle=rotate_angle,
            piece_center=piece_center
        )

    async def _get_element_bounding_box(self, selector: str, iframe_selector: str | None = None) -> FloatRect:
        box = await self._get_locator(selector, iframe_selector).bounding_box()
        if box is None:
            raise ValueError("Bounding box for slide bar was none")
        return box

    async def _move_mouse_to_element_center(self, ele: Locator, x_offset: float = 0, y_offset: int = 0) -> None:
        box = await ele.bounding_box()
        if box is None:
            raise ValueError("Bounding box for element was none")
        x, y = get_center(box["x"], box["y"], box["width"], box["height"])
        await self.page.mouse.move(x + x_offset, y + y_offset)

    async def get_b64_img_from_src(self, element: str | Locator, iframe_selector: str | None = None) -> str:
        """Get the source of b64 image element and return the portion after the data:image/png;base64,"""
        if isinstance(element, str):
            e = self._get_locator(element, iframe_selector=iframe_selector)
        else:
            e = element
        url = await e.get_attribute("src")
        if not url:
            raise ValueError("element had no url")
        _, data = url.split(",")
        LOGGER.debug("got b64 image from data url")
        return data

    def _get_locator_from_frame(self, selector: str, iframe_selector: str = "frame") -> Locator:
        return self.page.frame_locator(iframe_selector).locator(selector)

    def _get_locator(self, selector: str, iframe_selector: str | None = None) -> Locator:
        if iframe_selector:
            return self._get_locator_from_frame(selector, iframe_selector)
        else:
            return self.page.locator(selector)

    async def _get_element_text(self, selector: str, iframe_selector: str | None = None) -> str:
        """Get the text of an element"""
        e = self._get_locator(selector, iframe_selector=iframe_selector)
        text_content = await e.text_content()
        if not text_content:
            raise ValueError("element " + selector + " had no text content")
        LOGGER.debug(f"{selector} has text: {text_content}")
        return text_content

    async def _drag_proportional(
            self,
            selector: str,
            points: MultiPointResponse,
            iframe_selector: str | None = None
        ) -> None:
        """Drag from one point to another point inside an elements bounding box 
        to the width and height of the entire element

        Args:
            points: MultiPointResponse consisting of two points, where the first point is the point the mouse
                is initially pressed, and the second point is the point where the mouse is released.
        """
        if len(points.proportional_points) != 2:
            raise ValueError(
                    f"Expected proportional points in MultiPointResponse to have len == 2. Got len == {len(points.proportional_points)}")
        bounding_box = await self._get_element_bounding_box(selector, iframe_selector=iframe_selector)
        start_x = bounding_box["x"] + (points.proportional_points[0].proportion_x * bounding_box["width"]) 
        start_y = bounding_box["y"] + (points.proportional_points[0].proportion_x * bounding_box["height"]) 
        end_x = bounding_box["x"] + (points.proportional_points[1].proportion_x * bounding_box["width"]) 
        end_y = bounding_box["y"] + (points.proportional_points[1].proportion_x * bounding_box["height"]) 
        await self.page.mouse.move(start_x, start_y)
        await self.page.mouse.down()
        await self.page.mouse.move(end_x, end_y, steps=100)
        await self.page.mouse.up()
        LOGGER.debug(f"dragged from ({start_x}, {start_y}) to ({end_x}, {end_y})")

    async def iframe_present(self) -> bool:
        try:
            await expect(self.page.locator("iframe")).to_be_visible(timeout=1)
            LOGGER.debug("iframe is present")
            return True
        except (TimeoutError, AssertionError) as e:
            LOGGER.debug("iframe is not present")
            return False

    async def _count_red_dots(self, iframe_selector: str | None = None) -> int:
        """Cound the red dots that appear when solving a shapes captcha"""
        loc = self._get_locator(SEMANTIC_SHAPES_ELEMENTS_INSIDE_CHALLENGE, iframe_selector=iframe_selector)
        count = await loc.count()
        LOGGER.debug(f"{count} red dots are present")
        return count
