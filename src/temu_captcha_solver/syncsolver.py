"""Abstract base class for temu Captcha Solvers"""

import time
from abc import ABC, abstractmethod
from typing import Literal

from undetected_chromedriver import logging

class SyncSolver(ABC):

    def solve_captcha_if_present(self, captcha_detect_timeout: int = 15, retries: int = 3) -> None:
        """Solves any captcha that is present, if one is detected

        Args:
            captcha_detect_timeout: return if no captcha is detected in this many seconds
            retries: number of times to retry captcha
        """
        for _ in range(retries):
            if not self.captcha_is_present(captcha_detect_timeout):
                logging.debug("Captcha is not present")
                return
            else:
                match self.identify_captcha():
                    case "arced_slide": 
                        self.solve_arced_slide()
                    case "puzzle": 
                        self.solve_puzzle()
            if self.captcha_is_not_present(timeout=5):
                return
            else:
                time.sleep(5)

    @abstractmethod
    def captcha_is_present(self, timeout: int = 15) -> bool:
        pass

    @abstractmethod
    def captcha_is_not_present(self, timeout: int = 15) -> bool:
        pass

    @abstractmethod
    def identify_captcha(self) -> Literal["arced_slide", "puzzle"]:
        pass

    @abstractmethod
    def solve_arced_slide(self) -> None:
        pass

    @abstractmethod
    def solve_puzzle(self) -> None:
        pass

    @abstractmethod
    def get_b64_img_from_src(self, selector: str) -> str:
        pass
