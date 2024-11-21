import asyncio
import logging
import os

from playwright.async_api import Page, async_playwright, expect
from playwright_stealth import stealth_async, StealthConfig
import pytest

from ..asyncplaywrightsolver import AsyncPlaywrightSolver

proxy = {
    "server": "45.67.2.115:5689",
    "username": "aupzmsxp",
    "password": "vszgekgiz6ax"
}

# @pytest.mark.asyncio
# async def test_does_not_false_positive(caplog):
#     async with async_playwright() as p:
#         browser = await p.chromium.launch(headless=False)
#         page = await browser.new_page()
#         config = StealthConfig(navigator_languages=False, navigator_vendor=False, navigator_user_agent=False)
#         await stealth_async(page, config)
#         await page.goto("https://www.temu.com")
#         sadcaptcha = AsyncPlaywrightSolver(page, os.environ["API_KEY"])
#         assert await sadcaptcha.captcha_is_not_present()

# @pytest.mark.asyncio
# async def test_solve_puzzle_slide(caplog):
#     async with async_playwright() as p:
#         browser = await p.chromium.launch(headless=False, proxy=proxy)
#         page = await browser.new_page()
#         config = StealthConfig(navigator_languages=False, navigator_vendor=False, navigator_user_agent=False)
#         await stealth_async(page, config)
#         await page.goto("https://www.temu.com/goods.html?_bg_fs=1&goods_id=601099520319675&refer_page_el_sn=200024&_x_sessn_id=k3iqtbifnd&refer_page_name=goods&refer_page_id=10032_1729021787501_0xrr1i7i7w&refer_page_sn=10032 ")
#         sadcaptcha = AsyncPlaywrightSolver(page, os.environ["API_KEY"])
#         input()
#         await sadcaptcha.solve_captcha_if_present()
#         assert await sadcaptcha.captcha_is_not_present()

@pytest.mark.asyncio
async def test_solve_captcha_at_temu_open_no_stealth(caplog):
    caplog.set_level(logging.DEBUG)
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False, proxy=proxy)
        page = await browser.new_page()
        config = StealthConfig(navigator_languages=False, navigator_vendor=False, navigator_user_agent=False)
        # await stealth_async(page, config)
        await page.goto("https://www.temu.com")
        sadcaptcha = AsyncPlaywrightSolver(page, os.environ["API_KEY"], dump_requests=True)
        input()
        await sadcaptcha.solve_captcha_if_present()
        assert await sadcaptcha.captcha_is_not_present()


@pytest.mark.asyncio
async def test_solve_captcha_at_temu_open(caplog):
    caplog.set_level(logging.DEBUG)
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False, proxy=proxy)
        page = await browser.new_page()
        config = StealthConfig(navigator_languages=False, navigator_vendor=False, navigator_user_agent=False)
        await stealth_async(page, config)
        await page.goto("https://www.temu.com")
        sadcaptcha = AsyncPlaywrightSolver(page, os.environ["API_KEY"])
        input()
        await sadcaptcha.solve_captcha_if_present()
        assert await sadcaptcha.captcha_is_not_present()

