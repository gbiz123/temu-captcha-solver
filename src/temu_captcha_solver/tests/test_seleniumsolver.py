import time
import logging
import os

from webdriver_manager.chrome import ChromeDriverManager
from selenium import webdriver
from selenium.webdriver.common.by import By
import undetected_chromedriver as uc

from ..seleniumsolver import SeleniumSolver

options = webdriver.ChromeOptions()
options.add_argument("--headless=0")
options.binary_location = "/usr/bin/google-chrome-stable"


def make_driver() -> uc.Chrome:
    return uc.Chrome(service=ChromeDriverManager().install(), headless=False, use_subprocess=False, browser_executable_path="/usr/bin/google-chrome-stable")

def test_solve_captcha_at_temu_open(caplog):
    caplog.set_level(logging.DEBUG)
    driver = make_driver()
    try:
        driver.get("https://www.temu.com")
        input()
        sadcaptcha = SeleniumSolver(driver, os.environ["API_KEY"])
        sadcaptcha.solve_captcha_if_present()
        assert sadcaptcha.captcha_is_not_present()
    finally:
        driver.quit()
