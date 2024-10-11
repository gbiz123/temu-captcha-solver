import asyncio
import logging
import os

from playwright.async_api import Page, async_playwright, expect
from playwright_stealth import stealth_async, StealthConfig
import pytest

from ..asyncplaywrightsolver import AsyncPlaywrightSolver

proxy = {
    "server": "pr.oxylabs.io:7777",
    "username": "customer-toughdata-cc-br",
    "password": "Toughproxies_123"
}

@pytest.mark.asyncio
async def test_does_not_false_positive(caplog):
    raise NotImplementedError()

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

