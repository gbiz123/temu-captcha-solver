"""This class handles the captcha solving for selenium users"""

from contextlib import contextmanager
import logging
import math
import random
import time
from typing import Any, Generator
import warnings
from playwright.sync_api import FloatRect

from selenium.common.exceptions import TimeoutException
from selenium.webdriver import ActionChains, Chrome
from selenium.webdriver.common.actions.action_builder import ActionBuilder
from selenium.webdriver.common.actions.interaction import POINTER_MOUSE
from selenium.webdriver.common.actions.pointer_input import PointerInput
from selenium.webdriver.common.by import By
from selenium.webdriver.remote.webelement import WebElement
from selenium.webdriver.support import expected_conditions
from selenium.webdriver.support.ui import WebDriverWait

from temu_captcha_solver.parsers import get_list_of_objects_of_interest
from temu_captcha_solver.selenium_util import wait_for_element_to_be_stable
from temu_captcha_solver.solver_commons.two_image import identify_selector_of_image_to_click, two_image_challenge_is_supported

from .geometry import(
    get_box_center,
    get_center,
    piece_is_not_moving,
    rotate_angle_from_style,
    xy_to_proportional_point
) 

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
    TWO_IMAGE_CHALLENGE_TEXT,
    TWO_IMAGE_FIRST_IMAGE,
    TWO_IMAGE_REFRESH_BUTTON,
    TWO_IMAGE_SECOND_IMAGE,
) 
 
from .models import ArcedSlideCaptchaRequest, ArcedSlideTrajectoryElement, MultiPointResponse, ProportionalPoint, SemanticShapesRequest, SwapTwoRequest, ThreeByThreeCaptchaRequest, TwoImageCaptchaRequest, dump_to_json
from .api import ApiClient, BadRequest
from .syncsolver import SyncSolver

LOGGER = logging.getLogger(__name__)

class SeleniumSolver(SyncSolver):

    client: ApiClient
    chromedriver: Chrome

    def __init__(
            self, 
            chromedriver: Chrome,
            sadcaptcha_api_key: str,
            headers: dict[str, Any] | None = None,
            proxy: str | None = None,
            dump_requests: bool = False,
            mouse_step_size: int = 5
        ) -> None:
        warnings.warn(
            "SeleniumSolver is deprecated. Please use 'make_undetected_chromedriver_solver()' instead for a more reliable experience.")
        self.chromedriver = chromedriver
        self.client = ApiClient(sadcaptcha_api_key)
        self.headers = headers
        self.proxy = proxy
        self.mouse_step_size = mouse_step_size
        super().__init__(dump_requests)

    def captcha_is_present(self, timeout: int = 15) -> bool:
        for _ in range(timeout * 2):
            if self.any_selector_in_list_present(CAPTCHA_PRESENCE_INDICATORS):
                LOGGER.debug("Captcha detected")
                return True
            time.sleep(0.5)
        LOGGER.debug("Captcha not found")
        return False

    def captcha_is_not_present(self, timeout: int = 15) -> bool:
        captcha_not_present = True
        for _ in range(timeout * 2):
            for selector in CAPTCHA_PRESENCE_INDICATORS:
                if len(self.chromedriver.find_elements(By.CSS_SELECTOR, selector)) != 0:
                    LOGGER.debug("Captcha not present")
                    captcha_not_present = False
            time.sleep(0.5)
        LOGGER.debug("Captcha not found")
        return captcha_not_present

    def solve_puzzle(self) -> None:
        """Slide 10 pixels, then grab the puzzle and piece, then make API call and consume the response"""
        with self._in_iframe_if_present("iframe"):
            slide_button = self.chromedriver.find_element(By.CSS_SELECTOR, PUZZLE_BUTTON_SELECTOR)
            slide_button_box = self._get_element_bounding_box(self.chromedriver.find_element(By.CSS_SELECTOR, PUZZLE_BUTTON_SELECTOR))
            start_x, start_y = get_box_center(slide_button_box)
            input = PointerInput(POINTER_MOUSE, "default mouse")
            actions = ActionBuilder(self.chromedriver, duration=5, mouse=input)
            _ = actions.pointer_action \
                    .move_to_location(start_x, start_y) \
                    .pointer_down()
            start_distance = 10
            for pixel in range(start_distance):
                _ = actions.pointer_action.move_to_location(int(start_x + pixel), int(start_y + math.log(1 + pixel))) \
                        .pause(0.02)
            actions.perform()
            LOGGER.debug("dragged 10 pixels")
            puzzle_image = self.get_b64_img_from_src(PUZZLE_PUZZLE_IMAGE_SELECTOR)
            piece_image = self.get_b64_img_from_src(PUZZLE_PIECE_IMAGE_SELECTOR)
            resp = self.client.puzzle(puzzle_image, piece_image)
            slide_bar_width = self._get_puzzle_slide_bar_width()
            pixel_distance = int(resp.slide_x_proportion * slide_bar_width)
            LOGGER.debug(f"will continue to drag {pixel_distance} more pixels")
            actions = ActionBuilder(self.chromedriver, duration=1, mouse=input)
            for pixel in range(start_distance, pixel_distance):
                _ = actions.pointer_action.move_to_location(int(start_x + pixel), int(start_y + math.log(1 + pixel))) \
                        .pause(0.01)
            actions.pointer_action.pause(0.5)
            _ = actions.pointer_action.pointer_up()
            actions.perform()
            LOGGER.debug("done")

    def solve_semantic_shapes(self) -> None:
        """Solves the shapes challenge where an image and some text are presented.
        Implements various checks to deal with strange behavior from temu captcha.
        For example, temu shows a loading icon which makes the challenge impossible to click."""
        for _ in range(3):
            with self._in_iframe_if_present("iframe"):
                try:
                    for i in range(-3, 0):
                        LOGGER.debug(f"solving shapes in in {-1 * i}")
                        time.sleep(1)

                    image_b64 = self.get_b64_img_from_src(SEMANTIC_SHAPES_IMAGE)
                    challenge = self._get_element_text(SEMANTIC_SHAPES_CHALLENGE_TEXT)
                    request = SemanticShapesRequest(image_b64=image_b64, challenge=challenge)
                    
                    if self.dump_requests:
                        dump_to_json(request, "semantic_shapes_request.json")
                    
                    resp = self.client.semantic_shapes(request)
                    challenge_current = self._get_element_text(SEMANTIC_SHAPES_CHALLENGE_TEXT)
                    
                    if challenge != challenge_current:
                        LOGGER.debug("challenge text has changed since making the initial request. refreshing to avoid clicking incorrect location")
                        self._get_element(SEMANTIC_SHAPES_REFRESH_BUTTON).click()
                        continue

                    self._click_proportional_points(SEMANTIC_SHAPES_IMAGE, resp.proportional_points)
                    time.sleep(1)
                    LOGGER.debug("clicked answer...")
                    
                    for i in range(-5, 0):
                        LOGGER.debug(f"validating answer in {-1 * i}")
                        time.sleep(1)

                    if self.captcha_is_present(1):
                        LOGGER.debug("captcha was still present after solving. retrying")
                        self._get_element(SEMANTIC_SHAPES_REFRESH_BUTTON).click()
                        continue
                    
                    LOGGER.debug("solved semantic shapes")
                    return

                except BadRequest as e:
                    LOGGER.debug("API was unable to solve, retrying. error message: " + str(e))
                    self._get_element(SEMANTIC_SHAPES_REFRESH_BUTTON).click()
                    time.sleep(3)

    def solve_arced_slide(self) -> None:
        """Solves the arced slide puzzle. This challenge is similar to the puzzle
        challenge, but the puzzle piece travels in an arc, hence then name arced slide.
        The API expects the b64 encoded puzzle and piece images, along with data about the piece's
        trajectory in a list of ArcedSlideTrajectoryElements.

        This function will get the b64 encoded images, and will 'sweep' the slide
        bar to determine the piece's trajectory. Then it sends the data to the API
        and consumes the response.
        """ 
        with self._in_iframe_if_present("iframe"):
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
                        .move_by_offset(-1, int(random.gauss(0, 5))) \
                        .pause(0.01)
            actions.release().perform()

    def solve_three_by_three(self) -> None:
        with self._in_iframe_if_present("iframe"):
            image_elements = self.chromedriver.find_elements(By.CSS_SELECTOR, THREE_BY_THREE_IMAGE)
            images_b64: list[str] = []
            for image_element in image_elements:
                images_b64.append(self.get_b64_img_from_src(image_element))
            challenge_text = self._get_element_text(THREE_BY_THREE_TEXT)
            objects = get_list_of_objects_of_interest(challenge_text)
            request = ThreeByThreeCaptchaRequest(objects_of_interest=objects, images=images_b64)
            if self.dump_requests:
                dump_to_json(request, "three_by_three_request.json")
            resp = self.client.three_by_three(request)
            for i in resp.solution_indices:
                image_element = self.chromedriver.find_element(By.CSS_SELECTOR, f"img[src*=\"{images_b64[i]}\"]") # Where src matches the desired image
                image_element.click()
                time.sleep(1.337)
            self._click_proportional(self.chromedriver.find_element(By.CSS_SELECTOR, THREE_BY_THREE_CONFIRM_BUTTON), 0.5, 0.5)

    def solve_swap_two(self) -> None:
        """Click and drag, swap two to restore the image"""
        with self._in_iframe_if_present("iframe"):
            image_b64 = self.get_b64_img_from_src(SWAP_TWO_IMAGE)
            request = SwapTwoRequest(image_b64=image_b64)
            if self.dump_requests:
                dump_to_json(request, "swap_two_request.json")
            resp = self.client.swap_two(request)
            self._drag_proportional(SWAP_TWO_IMAGE, resp)

    def solve_two_image(self) -> None:
        for _ in range(3):
            try:
                for i in range(-3, 0):
                    LOGGER.debug(f"solving two image in in {-1 * i}")
                    time.sleep(1)

                with self._in_iframe_if_present("iframe"):
                    challenge = self._get_element_text(TWO_IMAGE_CHALLENGE_TEXT)

                    if not two_image_challenge_is_supported(challenge):
                        LOGGER.warning("This text variation of Two Image is not supported yet. Refreshing until we see one that is supported. Please be aware that English Only is supported!!!")
                        self._get_element(TWO_IMAGE_REFRESH_BUTTON).click()
                        continue

                    first_image = self.get_b64_img_from_src(TWO_IMAGE_FIRST_IMAGE)
                    second_image = self.get_b64_img_from_src(TWO_IMAGE_SECOND_IMAGE)
                    request = TwoImageCaptchaRequest(
                        images_b64=[first_image, second_image],
                        challenge=challenge
                    )
                    
                    if self.dump_requests:
                        dump_to_json(request, "two_image_request.json")
                    
                    resp = self.client.two_image(request)
                    challenge_current = self._get_element_text(TWO_IMAGE_CHALLENGE_TEXT)
                    
                    if challenge != challenge_current:
                        LOGGER.debug("challenge text has changed since making the initial request. refreshing to avoid clicking incorrect location")
                        self._get_element(TWO_IMAGE_REFRESH_BUTTON).click()
                        continue

                    target_image_selector = identify_selector_of_image_to_click(challenge)
                    self._click_proportional_points(target_image_selector, resp.proportional_points)
                    time.sleep(1)
                    LOGGER.debug("clicked answer...")
                    
                    for i in range(-5, 0):
                        LOGGER.debug(f"validating answer in {-1 * i}")
                        time.sleep(1)

                    if self.captcha_is_present(1):
                        LOGGER.debug("captcha was still present after solving. This is normally because it's impossible to click in the region over the solution, and the click was not registered")
                        self._get_element(TWO_IMAGE_REFRESH_BUTTON).click()
                        continue
                    
                    LOGGER.debug("solved two image")
                    return

            except BadRequest as e:
                LOGGER.debug("API was unable to solve, retrying. error message: " + str(e))
                self._get_element(SEMANTIC_SHAPES_REFRESH_BUTTON).click()
                time.sleep(3)

    def get_b64_img_from_src(self, element: str | WebElement, iframe_selector: str | None = None) -> str:
        """Get the source of b64 image element and return the portion after the data:image/png;base64,"""
        if iframe_selector:
            with self._in_iframe_if_present(iframe_selector):
                if isinstance(element, str):
                    e = self.chromedriver.find_element(By.CSS_SELECTOR, element)
                else:
                    e = element
                url = e.get_attribute("src")
                if not url:
                    raise ValueError("Could not get image source for element")
                return url.split(",")[1]
        else:
            if isinstance(element, str):
                e = self.chromedriver.find_element(By.CSS_SELECTOR, element)
            else:
                e = element
            url = e.get_attribute("src")
            if not url:
                raise ValueError("Could not get image source for elemenmt")
            return url.split(",")[1]

    def switch_to_new_tab_if_present(self) -> None:
        wait = WebDriverWait(self.chromedriver, 1)
        original_window_count = len(self.chromedriver.window_handles)
        original_windows = self.chromedriver.window_handles
        try:
            _ = wait.until(expected_conditions.number_of_windows_to_be(original_window_count + 1))
            new_window = [win for win in self.chromedriver.window_handles if win not in original_windows][0]
            self.chromedriver.switch_to.window(new_window)
            LOGGER.debug("popup present, changing page to popup")
        except TimeoutException:
            LOGGER.debug("no popup present")

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

    
    def any_selector_in_list_present(self, selectors: list[str], iframe_locator: str | None = None) -> bool:
        with self._in_iframe_if_present(
            iframe_selector=iframe_locator if iframe_locator else "iframe",
            remain_in_frame=True
        ):
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
        request = ArcedSlideCaptchaRequest(
            puzzle_image_b64=puzzle,
            piece_image_b64=piece,
            slide_piece_trajectory=trajectory
        )
        if self.dump_requests:
            dump_to_json(request, "arced_slide_request.json")
        return request

    def _get_slide_piece_trajectory(self, actions: ActionChains) -> list[ArcedSlideTrajectoryElement]:
        """Determines slider trajectory by dragging the slider element across the entire box,
        and computing the ArcedSlideTrajectoryElement at each location."""
        slide_button = self.chromedriver.find_element(By.CSS_SELECTOR, ARCED_SLIDE_BUTTON_SELECTOR)
        slider_piece = self.chromedriver.find_element(By.CSS_SELECTOR, ARCED_SLIDE_PIECE_CONTAINER_SELECTOR)
        puzzle = self.chromedriver.find_element(By.CSS_SELECTOR, ARCED_SLIDE_PUZZLE_IMAGE_SELECTOR)
        
        slide_bar_width = self._get_arced_slide_bar_width()
        puzzle_img_bounding_box = self._get_element_bounding_box(puzzle)

        _ = actions.click_and_hold(slide_button)
        trajectory: list[ArcedSlideTrajectoryElement] = []
        times_piece_did_not_move = 0
        for pixel in range(0, int(slide_bar_width), self.mouse_step_size):
            actions \
                .move_by_offset(self.mouse_step_size, int(random.gauss(0, 5))) \
                .perform()
            wait_for_element_to_be_stable(self.chromedriver, slider_piece)
            trajectory.append(
                self._get_arced_slide_trajectory_element(
                    pixel,
                    puzzle_img_bounding_box,
                    slider_piece
                )
            )
            if not len(trajectory) > 100 / self.mouse_step_size:
                continue
            if piece_is_not_moving(trajectory):
                times_piece_did_not_move += 1
            else:
                times_piece_did_not_move = 0
            if times_piece_did_not_move >= 10:
                break
        actions.perform()
        return trajectory

    def _get_puzzle_slide_bar_width(self) -> float:
        """Gets the width of the puzzle slide bar from the width of the image. 
        The slide bar is always the same as the image. 
        We do not get the width of the bar element itself, because the css selector varies from region to region."""
        bg_image_bounding_box = self._get_element_bounding_box(self.chromedriver.find_element(By.CSS_SELECTOR, PUZZLE_PUZZLE_IMAGE_SELECTOR))
        slide_bar_width = bg_image_bounding_box["width"]
        return slide_bar_width

    def _get_arced_slide_bar_width(self) -> float:
        """Gets the width of the arced slide bar from the width of the image. 
        The slide bar is always the same as the image. 
        We do not get the width of the bar element itself, because the css selector varies from region to region."""
        bg_image_bounding_box = self._get_element_bounding_box(self.chromedriver.find_element(By.CSS_SELECTOR, ARCED_SLIDE_PUZZLE_IMAGE_SELECTOR))
        slide_bar_width = bg_image_bounding_box["width"]
        return slide_bar_width

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
        
    def _get_element_text(self, selector: str) -> str:
        """Get the text of an element"""
        e = self._get_element(selector)
        text_content = e.text
        if not text_content:
            raise ValueError("element " + selector + " had no text content")
        return text_content

    def _get_element(self, selector: str, iframe_selector: str | None = None) -> WebElement:
        if iframe_selector:
            with self._in_iframe_if_present(iframe_selector):
                return self.chromedriver.find_element(By.CSS_SELECTOR, selector)
        else:
            return self.chromedriver.find_element(By.CSS_SELECTOR, selector)

    @contextmanager
    def _in_iframe_if_present(self, iframe_selector: str, remain_in_frame: bool = False) -> Generator[Any, Any, Any]:
        """Context manager to  perform action in iframe

        if remain_in_frame is true, it will not switch back to default context"""
        try:
            if self.iframe_present():
                frame = self.chromedriver.find_element(By.CSS_SELECTOR, iframe_selector)
                self.chromedriver.switch_to.frame(frame)
                LOGGER.debug(f"iframe {iframe_selector} detected")
                yield
            else:
                LOGGER.debug(f"iframe not detected")
                yield
        finally:
            if not remain_in_frame:
                LOGGER.debug("Leaving iframe!")
                self.chromedriver.switch_to.default_content()
            else:
                LOGGER.debug("Staying in iframe!")

    def iframe_present(self) -> bool:
        if len(self.chromedriver.find_elements(By.CSS_SELECTOR, "iframe")) > 0:
            return True
        else:
            return False

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

    def _click_proportional_points(self, selector: str, points: list[ProportionalPoint]) -> None:
        for point in points:
            red_dot_count = self._count_eles_inside_challenge()
            for i in range(5):
                self._click_proportional(
                    self.chromedriver.find_element(By.CSS_SELECTOR, selector),
                    point.proportion_x + (i / 50), # each iteration try click a different place if no red dot appears
                    point.proportion_y + (i / 50),
                )                
                if red_dot_count == self._count_eles_inside_challenge():
                    LOGGER.debug("A new red dot did not appear. trying to click again in a slightly different location")
                    time.sleep(0.5)
                    continue
                else:
                    LOGGER.debug("A new red dot appeared")
                    break

    def _drag_proportional(
            self,
            selector: str,
            points: MultiPointResponse
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
        with self._in_iframe_if_present("iframe"):
            bounding_box = self._get_element_bounding_box(selector)
            start_x = bounding_box["x"] + (points.proportional_points[0].proportion_x * bounding_box["width"]) 
            start_y = bounding_box["y"] + (points.proportional_points[0].proportion_x * bounding_box["height"]) 
            end_x = bounding_box["x"] + (points.proportional_points[1].proportion_x * bounding_box["width"]) 
            end_y = bounding_box["y"] + (points.proportional_points[1].proportion_x * bounding_box["height"]) 
            action = ActionBuilder(self.chromedriver)
            action.pointer_action \
                    .move_to_location(start_x, start_y) \
                    .pointer_down() \
                    .pause(0.3) \
                    .move_to_location(end_x, end_y) \
                    .pointer_up() \
                    .perform()
            LOGGER.debug(f"dragged from ({start_x}, {start_y}) to ({end_x}, {end_y})")

    def _get_element_bounding_box(self, e: WebElement) -> FloatRect:
        loc = e.location
        size = e.size
        return {"x": loc["x"], "y": loc["y"], "width": size["width"], "height": size["height"]}

    def _count_eles_inside_challenge(self) -> int:
        """Cound the red dots that appear when solving a shapes captcha"""
        dots = self.chromedriver.find_elements(By.CSS_SELECTOR, SEMANTIC_SHAPES_ELEMENTS_INSIDE_CHALLENGE)
        count = len(dots)
        LOGGER.debug(f"{count} red dots are present")
        return count
