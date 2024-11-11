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

def make_driver_no_stealth() -> webdriver.Chrome:
    options = webdriver.ChromeOptions()
    options.add_argument("--headless=0")
    options.binary_location = "/usr/bin/google-chrome-stable"
    driver = webdriver.Chrome(service=ChromeService(ChromeDriverManager().install()), options=options)

def test_solve_captcha_at_login(caplog):
    caplog.set_level(logging.DEBUG)
    driver = make_driver()
    try:
        driver.get("https://www.temu.com/login.html?from=https%3A%2F%2Fwww.temu.com%2F&login_scene=2&refer_page_name=home&refer_page_id=10005_1731338265086_3iiyzozg6w&refer_page_sn=10005&_x_sessn_id=rhvz007z73")
        input()
        sadcaptcha = SeleniumSolver(driver, os.environ["API_KEY"], dump_requests=True)
        sadcaptcha.solve_captcha_if_present()
        # assert sadcaptcha.captcha_is_not_present()
    finally:
        driver.quit()

def test_solve_captcha_at_temu_open(caplog):
    caplog.set_level(logging.DEBUG)
    driver = make_driver()
    try:
        driver.get("https://www.temu.com")
        input()
        sadcaptcha = SeleniumSolver(driver, os.environ["API_KEY"], dump_requests=True)
        sadcaptcha.solve_captcha_if_present()
        assert sadcaptcha.captcha_is_not_present()
    finally:
        driver.quit()
