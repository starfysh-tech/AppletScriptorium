#!/usr/bin/env python3
"""Debug Playwright headed browser for news10.com with step-by-step logging."""
import asyncio
from pathlib import Path

from playwright.async_api import async_playwright


async def debug_fetch_news10():
    """Manually debug news10.com fetch with headed browser and detailed logging."""
    url = "https://www.news10.com/news/local-news/"
    screenshots_dir = Path("/tmp/playwright-debug")
    screenshots_dir.mkdir(exist_ok=True)

    print(f"\n{'='*80}")
    print(f"DEBUG: Fetching {url}")
    print(f"Screenshots will be saved to: {screenshots_dir}")
    print(f"{'='*80}\n")

    async with async_playwright() as p:
        # Launch browser in headed mode (visible window)
        print("[1/10] Launching Chromium browser (HEADED mode)...")
        browser = await p.chromium.launch(headless=False)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 14_0) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Safari/605.1.15"
        )
        page = await context.new_page()

        # Set default timeout
        page.set_default_timeout(60000)  # 60s

        print(f"[2/10] Navigating to {url}...")
        await page.goto(url, wait_until="load", timeout=60000)
        await page.screenshot(path=screenshots_dir / "01-initial-load.png")
        print(f"      Screenshot: 01-initial-load.png")

        # Check for challenges
        print("[3/10] Checking for Cloudflare/PerimeterX challenges...")
        challenge_selectors = [
            "div.cf-browser-verification",
            "div#cf-wrapper",
            "div.cf-error-title",
            "#challenge-running",
            "#px-captcha",
            "iframe[src*='perimeterx']",
            "body",  # Catch-all to see what's on page
        ]

        for selector in challenge_selectors:
            element = await page.query_selector(selector)
            if element:
                print(f"      Found: {selector}")
                if selector == "body":
                    # Get page title and first 500 chars of body text
                    title = await page.title()
                    body_text = await page.evaluate("document.body.innerText.substring(0, 500)")
                    print(f"      Title: {title}")
                    print(f"      Body preview: {body_text[:200]}...")

        await page.screenshot(path=screenshots_dir / "02-after-check.png")
        print(f"      Screenshot: 02-after-check.png")

        print("[4/10] Waiting 5 seconds for initial content...")
        await asyncio.sleep(5)
        await page.screenshot(path=screenshots_dir / "03-after-5s-wait.png")
        print(f"      Screenshot: 03-after-5s-wait.png")

        print("[5/10] Checking for human verification challenges...")
        # Look for common verification patterns
        verification_indicators = [
            "text=Verify you are human",
            "text=Checking your browser",
            "text=Security check",
            "text=Press & Hold",
            "[aria-label*='verification']",
            "[aria-label*='captcha']",
        ]

        for indicator in verification_indicators:
            try:
                element = await page.query_selector(indicator)
                if element:
                    print(f"      !!! FOUND VERIFICATION: {indicator}")
                    is_visible = await element.is_visible()
                    print(f"          Visible: {is_visible}")
            except Exception as e:
                # Selector might not be valid, continue
                pass

        # Get all text content
        all_text = await page.evaluate("document.body.innerText")
        if "verify" in all_text.lower() or "human" in all_text.lower() or "captcha" in all_text.lower():
            print(f"      !!! Page contains verification keywords")
            # Show first 1000 chars
            print(f"      Text preview:\n{all_text[:1000]}")

        await page.screenshot(path=screenshots_dir / "04-after-verification-check.png")
        print(f"      Screenshot: 04-after-verification-check.png")

        print("[6/10] Waiting 10 seconds (observe browser window for challenges)...")
        await asyncio.sleep(10)
        await page.screenshot(path=screenshots_dir / "05-after-10s-wait.png")
        print(f"      Screenshot: 05-after-10s-wait.png")

        print("[7/10] Attempting to wait for networkidle...")
        try:
            await page.wait_for_load_state("networkidle", timeout=10000)
            print("      Network idle achieved")
        except Exception as e:
            print(f"      Network idle timeout (normal): {e}")

        await page.screenshot(path=screenshots_dir / "06-after-networkidle.png")
        print(f"      Screenshot: 06-after-networkidle.png")

        print("[8/10] Extracting HTML content...")
        html = await page.content()
        print(f"      HTML length: {len(html):,} chars")

        # Save HTML
        html_file = screenshots_dir / "page-content.html"
        html_file.write_text(html, encoding="utf-8")
        print(f"      HTML saved: {html_file}")

        # Check for article indicators
        print("[9/10] Checking for article content...")
        article_indicators = [
            "article",
            "main",
            "[role='main']",
            ".article",
            "#main-content",
        ]

        for selector in article_indicators:
            element = await page.query_selector(selector)
            if element:
                text = await element.inner_text()
                print(f"      Found {selector}: {len(text)} chars")

        await page.screenshot(path=screenshots_dir / "07-final-state.png")
        print(f"      Screenshot: 07-final-state.png")

        print("[10/10] Keeping browser open for 30 seconds for manual inspection...")
        print("         Press Ctrl+C to close early\n")
        try:
            await asyncio.sleep(30)
        except KeyboardInterrupt:
            print("\n      User interrupted")

        await browser.close()

    print(f"\n{'='*80}")
    print("DEBUG COMPLETE")
    print(f"Review files in: {screenshots_dir}")
    print(f"{'='*80}\n")


if __name__ == "__main__":
    asyncio.run(debug_fetch_news10())
