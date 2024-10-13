# Temu Captcha Solver API
This project is the [SadCaptcha Temu Captcha Solver](https://www.sadcaptcha.com?ref=temughclientrepo) API client.
The purpose is to make integrating SadCaptcha into your Selenium, Playwright, or Async Playwright app as simple as one line of code.
Instructions for integrating with Selenium, Playwright, and Async Playwright are described below in their respective sections.

The end goal of this tool is to solve every single Temu captcha. 
Currently we are able to solve the arced slide and the puzzle slide:

<div align="center">
    <img src="https://sadcaptcha.b-cdn.net/arced-slide-temu-captcha.png" width="200px" height="150px" alt="TikTok Captcha Solver">
    <img src="https://sadcaptcha.b-cdn.net/temu-puzzle.webp" width="200px" height="150px" alt="TikTok Captcha Solver">
</div>

The Arced Slide challenge is the one where there is a puzzle piece that travels in an unpredictable trajectory, and there are two possible locations where the solution may be.
The puzzle slide is unique in that the pieces relocate after you drag the slider.
    
## Requirements
- Python >= 3.10
- **If using Selenium** - Selenium properly installed and in `PATH`
- **If using Playwright** - Playwright must be properly installed with `playwright install`
- **Stealth plugin** - You must use the appropriate `stealth` plugin for whichever browser automation framework you are using.
    - For Selenium, you can use [undetected-chromedriver](https://github.com/ultrafunkamsterdam/undetected-chromedriver)
    - For Playwright, you can use [playwright-stealth](https://pypi.org/project/playwright-stealth/)

## Installation
This project can be installed with `pip`. Just run the following command:
```
pip install temu-captcha-solver
```

## Selenium Client 
Import the package, set up the `SeleniumSolver` class, and call it whenever you need.
This turns the entire captcha detection, solution, retry, and verification process into a single line of code.
It is the recommended method if you are using Playwright.

```py
from temu_captcha_solver import SeleniumSolver
from selenium_stealth import stealth
import undetected_chromedriver as uc

driver = uc.Chrome(headless=False) # Use default undetected_chromedriver configuration!
api_key = "YOUR_API_KEY_HERE"
sadcaptcha = SeleniumSolver(driver, api_key)

# Selenium code that causes a Temu captcha...

sadcaptcha.solve_captcha_if_present(retries=5)
```

It is crucial that you use `undetected_chromedriver` with the default configuration, instead of the standard Selenium chromedriver.
Failure to use the `undetected_chromedriver` will result in "Verification failed" when attempting to solve the captcha.

## Playwright Client
Import the package, set up the `PlaywrightSolver` class, and call it whenever you need.
This turns the entire captcha detection, solution, retry, and verification process into a single line of code.
It is the recommended method if you are using playwright.


```py
from temu_captcha_solver import PlaywrightSolver
from playwright.sync_api import Page, sync_playwright
from playwright_stealth import stealth_sync, StealthConfig

api_key = "YOUR_API_KEY_HERE"

with sync_playwright() as p:
    browser = p.chromium.launch(headless=False)
    page = browser.new_page()
    config = StealthConfig(navigator_languages=False, navigator_vendor=False, navigator_user_agent=False)
    stealth_sync(page, config) # Use correct playwright_stealth configuration!
    
    # Playwright code that causes a Temu captcha...

    sadcaptcha = PlaywrightSolver(page, api_key)
    sadcaptcha.solve_captcha_if_present(retries=5)
```
It is crucial that users of the Playwright client also use `playwright-stealth` with the configuration specified above.
Failure to use the `playwright-stealth` plugin will result in "Verification failed" when attempting to solve the captcha.

## Async Playwright Client
Import the package, set up the `AsyncPlaywrightSolver` class, and call it whenever you need.
This turns the entire captcha detection, solution, retry, and verification process into a single line of code.
It is the recommended method if you are using async playwright.



```py
import asyncio
from temu_captcha_solver import AsyncPlaywrightSolver
from playwright.async_api import Page, async_playwright
from playwright_stealth import stealth_async, StealthConfig

api_key = "YOUR_API_KEY_HERE"

async def main()
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        page = await browser.new_page()
        config = StealthConfig(navigator_languages=False, navigator_vendor=False, navigator_user_agent=False)
        await stealth_async(page, config) # Use correct playwright_stealth configuration!
        
        # Playwright code that causes a Temu captcha...

        sadcaptcha = AsyncPlaywrightSolver(page, api_key)
        await sadcaptcha.solve_captcha_if_present(retries=5)

asyncio.run(main())
```
It is crucial that users of the Playwright client also use `playwright-stealth` with the stealth configuration specified above.
Failure to use the `playwright-stealth` plugin will result in "Verification failed" when attempting to solve the captcha.

## Using Proxies and Custom Headers
SadCaptcha supports using proxies and custom headers such as user agent.
This is useful to avoid detection.
To implement this feature, pass your proxy URL and headers dictionary as a keyword argument to the constructor of the solver.
```py
api_key = "YOUR_API_KEY_HERE"
proxy = "http://username:password@123.0.1.2:80"
headers = {"User-Agent": "Chrome"}

# With Selenium Solver
driver = uc.Chrome(headless=False) # Use default undetected_chromedriver configuration!
api_key = "YOUR_API_KEY_HERE"
sadcaptcha = SeleniumSolver(driver, api_key, proxy=proxy, headers=headers)

# With Playwright Solver
with sync_playwright() as p:
    browser = p.chromium.launch(headless=False)
    page = browser.new_page()
    stealth_sync(page) # Use default playwright_stealth configuration!
    sadcaptcha = PlaywrightSolver(page, api_key, proxy=proxy, headers=headers)
    sadcaptcha.solve_captcha_if_present(retries=5)

# With Async PlaywrightSolver
async def main()
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        page = await browser.new_page()
        await stealth_async(page) # Use default playwright_stealth configuration!
        sadcaptcha = AsyncPlaywrightSolver(page, api_key, headers=headers, proxy=proxy)
        await sadcaptcha.solve_captcha_if_present(retries=5)
```

## Contact
- Homepage: https://www.sadcaptcha.com/
- Email: greg@sadcaptcha.com
- Telegram @toughdata
