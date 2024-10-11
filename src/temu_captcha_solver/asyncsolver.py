"""Abstract base class for Temu Captcha Async Solvers"""

import logging
import asyncio
from abc import ABC, abstractmethod


from temu_captcha_solver.captchatype import CaptchaType
from temu_captcha_solver.selectors import ARCED_SLIDE_UNIQUE_IDENTIFIERS, PUZZLE_UNIQUE_IDENTIFIERS

LOGGER = logging.getLogger(__name__)

class AsyncSolver(ABC):

    async def solve_captcha_if_present(self, captcha_detect_timeout: int = 15, retries: int = 3) -> None:
        """Solves any captcha that is present, if one is detected

        Args:
            captcha_detect_timeout: return if no captcha is detected in this many seconds
            retries: number of times to retry captcha
        """
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
            if await self.captcha_is_not_present(timeout=5):
                return
            else:
                await asyncio.sleep(5)

    async def identify_captcha(self) -> CaptchaType:
        for _ in range(30):
            if await self.any_selector_in_list_present(PUZZLE_UNIQUE_IDENTIFIERS):
                LOGGER.debug("detected puzzle")
                return CaptchaType.PUZZLE
            elif await self.any_selector_in_list_present(ARCED_SLIDE_UNIQUE_IDENTIFIERS):
                LOGGER.debug("detected arced slide")
                return CaptchaType.ARCED_SLIDE
            else:
                await asyncio.sleep(1)
        raise ValueError("Neither puzzle, or arced slide was present")

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
    async def get_b64_img_from_src(self, selector: str) -> str:
        pass

    @abstractmethod
    async def any_selector_in_list_present(self, selectors: list[str]) -> bool:
        pass
