import logging
import time
import os

from playwright.sync_api import Page, sync_playwright, expect
from playwright_stealth import stealth_sync, StealthConfig

from ..playwrightsolver import PlaywrightSolver

def test_does_not_false_positive(caplog):
    raise NotImplementedError()


proxy = {
    "server": "pr.oxylabs.io:7777",
    "username": "customer-toughdata-cc-us",
    "password": "toughproxies"
}

def test_solve_captcha_on_temu_open(caplog):
    caplog.set_level(logging.DEBUG)
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False, proxy=proxy)
        page = browser.new_page()
        config = StealthConfig(navigator_languages=False, navigator_vendor=False, navigator_user_agent=False)
        stealth_sync(page, config)
        page.goto("https://www.temu.com")
        sadcaptcha = PlaywrightSolver(page, os.environ["API_KEY"])
        input()
        sadcaptcha.solve_captcha_if_present()
        assert sadcaptcha.captcha_is_not_present()
