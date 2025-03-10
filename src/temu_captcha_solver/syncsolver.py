"""Abstract base class for temu Captcha Solvers"""

import logging
import time
from abc import ABC, abstractmethod

from playwright.sync_api import Locator

from temu_captcha_solver.captchatype import CaptchaType
from temu_captcha_solver.selectors import ARCED_SLIDE_UNIQUE_IDENTIFIERS, PUZZLE_UNIQUE_IDENTIFIERS, SEMANTIC_SHAPES_UNIQUE_IDENTIFIERS, SWAP_TWO_UNIQUE_IDENTIFIERS, THREE_BY_THREE_UNIQUE_IDENTIFIERS

LOGGER = logging.getLogger(__name__)

class SyncSolver(ABC):

    def __init__(self, dump_requests: bool = False):
        self.dump_requests = dump_requests

    def solve_captcha_if_present(self, captcha_detect_timeout: int = 5, retries: int = 3) -> None:
        """Solves any captcha that is present, if one is detected

        Args:
            captcha_detect_timeout: return if no captcha is detected in this many seconds
            retries: number of times to retry captcha
        """
        self.switch_to_new_tab_if_present()
        for _ in range(retries):
            if not self.captcha_is_present(captcha_detect_timeout):
                LOGGER.debug("Captcha is not present")
                return
            else:
                match self.identify_captcha():
                    case CaptchaType.ARCED_SLIDE:
                        self.solve_arced_slide()
                    case CaptchaType.PUZZLE:
                        self.solve_puzzle()
                    case CaptchaType.SEMANTIC_SHAPES:
                        self.solve_semantic_shapes()
                    case CaptchaType.THREE_BY_THREE:
                        self.solve_three_by_three()
                    case CaptchaType.SWAP_TWO:
                        self.solve_swap_two()
                    case CaptchaType.TWO_IMAGE:
                        self.solve_two_image()
                    case CaptchaType.NONE:
                        LOGGER.warning("captcha was present (i think), but could not identify")
            if self.captcha_is_not_present(timeout=5):
                return
            else:
                continue

    def identify_captcha(self) -> CaptchaType:
        for _ in range(50):
            iframe_selector = "iframe" if self.iframe_present() else None
            if self.any_selector_in_list_present(PUZZLE_UNIQUE_IDENTIFIERS,
                                                 iframe_locator=iframe_selector):
                LOGGER.debug("detected puzzle")
                return CaptchaType.PUZZLE
            elif self.any_selector_in_list_present(ARCED_SLIDE_UNIQUE_IDENTIFIERS,
                                                   iframe_locator=iframe_selector):
                LOGGER.debug("detected arced slide")
                return CaptchaType.ARCED_SLIDE
            elif self.any_selector_in_list_present(SEMANTIC_SHAPES_UNIQUE_IDENTIFIERS,
                                                   iframe_locator=iframe_selector):
                LOGGER.debug("detected semantic shapes")
                return CaptchaType.SEMANTIC_SHAPES
            elif self.any_selector_in_list_present(THREE_BY_THREE_UNIQUE_IDENTIFIERS,
                                                   iframe_locator=iframe_selector):
                LOGGER.debug("detected three by three")
                return CaptchaType.THREE_BY_THREE
            elif self.any_selector_in_list_present(SWAP_TWO_UNIQUE_IDENTIFIERS,
                                                   iframe_locator=iframe_selector):
                LOGGER.debug("detected swap two")
                return CaptchaType.SWAP_TWO
            else:
                time.sleep(0.2)
        return CaptchaType.NONE

    @abstractmethod
    def switch_to_new_tab_if_present(self) -> None:
        pass

    @abstractmethod
    def captcha_is_present(self, timeout: int = 15) -> bool:
        pass

    @abstractmethod
    def captcha_is_not_present(self, timeout: int = 15) -> bool:
        pass

    @abstractmethod
    def solve_arced_slide(self) -> None:
        pass

    @abstractmethod
    def solve_puzzle(self) -> None:
        pass

    @abstractmethod
    def solve_semantic_shapes(self) -> None:
        pass

    @abstractmethod
    def solve_swap_two(self) -> None:
        pass

    @abstractmethod
    def solve_two_image(self) -> None:
        pass

    @abstractmethod
    def solve_three_by_three(self) -> None:
        pass

    @abstractmethod
    def get_b64_img_from_src(self, element: str | Locator) -> str:
        pass

    @abstractmethod
    def any_selector_in_list_present(self, selectors: list[str], iframe_locator: str | None = None) -> bool:
        pass

    @abstractmethod
    def iframe_present(self) -> bool:
        pass

