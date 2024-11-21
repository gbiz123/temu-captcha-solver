import json
import logging
import time
import os

from playwright.sync_api import Page, sync_playwright, expect
from playwright_stealth import stealth_sync, StealthConfig

from .. import selectors
from ..playwrightsolver import PlaywrightSolver

# def test_does_not_false_positive(caplog):
#     caplog.set_level(logging.DEBUG)
#     with sync_playwright() as p:
#         browser = p.chromium.launch(headless=False)
#         page = browser.new_page()
#         config = StealthConfig(navigator_languages=False, navigator_vendor=False, navigator_user_agent=False)
#         stealth_sync(page, config)
#         page.goto("https://www.temu.com")
#         sadcaptcha = PlaywrightSolver(page, os.environ["API_KEY"], dump_requests=True)
#         assert sadcaptcha.captcha_is_not_present()


proxy = {
    "server": "45.67.2.115:5689",
    "username": "aupzmsxp",
    "password": "vszgekgiz6ax"
}

def test_solve_captcha_on_temu_open_no_stealth(caplog):
    caplog.set_level(logging.DEBUG)
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False, proxy=proxy)
        page = browser.new_page()
        config = StealthConfig(navigator_languages=False, navigator_vendor=False, navigator_user_agent=False)
        # stealth_sync(page, config)
        page.goto("https://www.temu.com")
        sadcaptcha = PlaywrightSolver(page, os.environ["API_KEY"], dump_requests=True)
        input()
        sadcaptcha.solve_captcha_if_present()
        assert sadcaptcha.captcha_is_not_present()

# def test_scrape_shapes_challenges(caplog):
#     caplog.set_level(logging.DEBUG)
#     with sync_playwright() as p:
#         browser = p.chromium.launch(headless=False, proxy=proxy)
#         page = browser.new_page()
#         config = StealthConfig(navigator_languages=False, navigator_vendor=False, navigator_user_agent=False)
#         # stealth_sync(page, config)
#         page.goto("https://www.temu.com")
#         sadcaptcha = PlaywrightSolver(page, os.environ["API_KEY"], dump_requests=True)
#         input()
#         if os.path.exists("scraped_shapes_captcha.json"):
#             with open("scraped_shapes_captcha.json") as f:
#                 data = json.load(f)
#         else:
#             data = []
#
#         last_image = ""
#         while True:
#             time.sleep(3)
#
#             image = sadcaptcha.get_b64_img_from_src(
#                 selectors.SEMANTIC_SHAPES_IMAGE,
#                 selectors.SEMANTIC_SHAPES_IFRAME
#             )
#             text = sadcaptcha._get_element_text(
#                 selectors.SEMANTIC_SHAPES_CHALLENGE_TEXT,
#                 selectors.SEMANTIC_SHAPES_IFRAME
#             )
#
#             if image == last_image:
#                 time.sleep(3)
#                 continue
#             last_image = image
#
#             data.append({"image": image, "text": text})
#             with open("scraped_shapes_captcha.json", "w") as f:
#                 json.dump(data, f)
#             page.frame_locator(selectors.SEMANTIC_SHAPES_IFRAME).locator(selectors.SEMANTIC_SHAPES_REFRESH_BUTTON).click()


#
# def test_solve_captcha_on_temu_open(caplog):
#     caplog.set_level(logging.DEBUG)
#     with sync_playwright() as p:
#         browser = p.chromium.launch(headless=False, proxy=proxy)
#         page = browser.new_page()
#         config = StealthConfig(navigator_languages=False, navigator_vendor=False, navigator_user_agent=False)
#         stealth_sync(page, config)
#         page.goto("https://www.temu.com")
#         sadcaptcha = PlaywrightSolver(page, os.environ["API_KEY"], dump_requests=True)
#         input()
#         sadcaptcha.solve_captcha_if_present()
#         assert sadcaptcha.captcha_is_not_present()
