"""Abstract base class for Temu Captcha Async Solvers"""

import logging
import asyncio
from abc import ABC, abstractmethod

from playwright.async_api import Locator, Page, TimeoutError
from playwright._impl._errors import TargetClosedError


from temu_captcha_solver.captchatype import CaptchaType
from temu_captcha_solver.selectors import ARCED_SLIDE_UNIQUE_IDENTIFIERS, PUZZLE_UNIQUE_IDENTIFIERS, SEMANTIC_SHAPES_UNIQUE_IDENTIFIERS, SWAP_TWO_UNIQUE_IDENTIFIERS, THREE_BY_THREE_UNIQUE_IDENTIFIERS

LOGGER = logging.getLogger(__name__)

class AsyncSolver(ABC):

    def __init__(self, dump_requests: bool = False):
        self.dump_requests = dump_requests
        self.page: Page

    async def solve_captcha_if_present(self, captcha_detect_timeout: int = 5, retries: int = 3) -> None:
        """Solves any captcha that is present, if one is detected

        Args:
            captcha_detect_timeout: return if no captcha is detected in this many seconds
            retries: number of times to retry captcha
        """
        await self.switch_to_popup_if_present()
        for _ in range(retries):
            if not await self.captcha_is_present(captcha_detect_timeout):
                LOGGER.debug("Captcha is not present")
                return
            else:
                match await self.identify_captcha():
                    case CaptchaType.ARCED_SLIDE: 
                        await self.solve_arced_slide()
                    case CaptchaType.PUZZLE: 
                        await self.solve_puzzle()
                    case CaptchaType.SEMANTIC_SHAPES: 
                        await self.solve_semantic_shapes()
                    case CaptchaType.THREE_BY_THREE:
                        await self.solve_three_by_three()
                    case CaptchaType.SWAP_TWO:
                        await self.solve_swap_two()
                    case CaptchaType.TWO_IMAGE:
                        await self.solve_two_image()
                    case CaptchaType.NONE:
                        LOGGER.warning("captcha was present (i think), but could not identify")
            if await self.captcha_is_not_present(timeout=5):
                return
            else:
                continue

    async def switch_to_popup_if_present(self):
        try:
            async with self.page.expect_popup(timeout=1000) as popup_info:
                try:
                    new_page = await popup_info.value
                    _ = new_page.locator("html").count()
                    self.page = new_page
                    LOGGER.debug("popup present, changing page to popup")
                except TargetClosedError as e:
                    LOGGER.debug("tried to switch to an already closed popup")
        except TimeoutError as e:
            LOGGER.debug("no popup present")
        except Exception as e:
            LOGGER.debug("detected a new tab, but could not switch to it")

    async def identify_captcha(self) -> CaptchaType:
        for _ in range(30):
            iframe_selector = "iframe" if await self.iframe_present() else None
            if await self.any_selector_in_list_present(PUZZLE_UNIQUE_IDENTIFIERS,
                                                       iframe_locator=iframe_selector):
                LOGGER.debug("detected puzzle")
                return CaptchaType.PUZZLE
            elif await self.any_selector_in_list_present(ARCED_SLIDE_UNIQUE_IDENTIFIERS,
                                                         iframe_locator=iframe_selector):
                LOGGER.debug("detected arced slide")
                return CaptchaType.ARCED_SLIDE
            elif await self.any_selector_in_list_present(SEMANTIC_SHAPES_UNIQUE_IDENTIFIERS,
                                                         iframe_locator=iframe_selector):
                LOGGER.debug("detected semantic shapes")
                return CaptchaType.SEMANTIC_SHAPES
            elif await self.any_selector_in_list_present(THREE_BY_THREE_UNIQUE_IDENTIFIERS,
                                                         iframe_locator=iframe_selector):
                LOGGER.debug("detected three by three")
                return CaptchaType.THREE_BY_THREE
            elif await self.any_selector_in_list_present(SWAP_TWO_UNIQUE_IDENTIFIERS,
                                                         iframe_locator=iframe_selector):
                LOGGER.debug("detected swap two")
                return CaptchaType.THREE_BY_THREE
            else:
                await asyncio.sleep(1)
        return CaptchaType.NONE

    @abstractmethod
    async def captcha_is_present(self, timeout: int = 15) -> bool:
        pass

    @abstractmethod
    async def captcha_is_not_present(self, timeout: int = 15) -> bool:
        pass

    @abstractmethod
    async def solve_arced_slide(self) -> None:
        pass

    @abstractmethod
    async def solve_puzzle(self) -> None:
        pass

    @abstractmethod
    async def solve_two_image(self) -> None:
        pass

    @abstractmethod
    async def solve_semantic_shapes(self) -> None:
        pass

    @abstractmethod
    async def solve_three_by_three(self) -> None:
        pass

    @abstractmethod
    async def solve_swap_two(self) -> None:
        pass

    @abstractmethod
    async def get_b64_img_from_src(self, element: str | Locator) -> str:
        pass

    @abstractmethod
    async def any_selector_in_list_present(self, selectors: list[str], iframe_locator: str | None = None) -> bool:
        pass

    @abstractmethod
    async def iframe_present(self) -> bool:
        pass
