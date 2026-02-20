"""Browser automation - Playwright for screenshots and automation."""
from pathlib import Path
from typing import AsyncGenerator

# Playwright is optional - import only when used
playwright = None

def _get_playwright():
    global playwright
    if playwright is None:
        try:
            from playwright.async_api import async_playwright
            playwright = async_playwright
        except ImportError:
            raise ImportError("Install playwright: pip install playwright && playwright install chromium")
    return playwright


async def take_screenshot(url: str, output_path: Path, headless: bool = True) -> Path:
    """Take screenshot of URL and save to output_path."""
    p = _get_playwright()
    async with p() as pw:
        browser = await pw.chromium.launch(headless=headless)
        page = await browser.new_page()
        await page.goto(url)
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        await page.screenshot(path=str(output_path))
        await browser.close()
    return output_path


async def get_page_content(url: str) -> str:
    """Fetch page HTML content."""
    p = _get_playwright()
    async with p() as pw:
        browser = await pw.chromium.launch(headless=True)
        page = await browser.new_page()
        await page.goto(url)
        content = await page.content()
        await browser.close()
    return content
