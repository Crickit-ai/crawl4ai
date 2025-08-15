import asyncio
import signal
from crawl4ai.browser_manager import ManagedBrowser
from crawl4ai.async_configs import BrowserConfig
from crawl4ai.async_logger import AsyncLogger
from playwright.async_api import async_playwright

async def main():
    """
    Launches and manages a persistent browser instance.
    """
    logger = AsyncLogger()
    browser_config = BrowserConfig(
        use_managed_browser=True,
        headless=True,
        debugging_port=9222,
    )
    
    managed_browser = ManagedBrowser(
        browser_config=browser_config,
        logger=logger,
    )

    stop_event = asyncio.Event()

    def signal_handler():
        logger.info("Stop signal received, shutting down browser.")
        stop_event.set()

    loop = asyncio.get_running_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig, signal_handler)

    try:
        cdp_url = await managed_browser.start()
        logger.info(f"Browser started successfully.")
        logger.info(f"Connect to it using the following CDP endpoint: {cdp_url}")
        
        async with async_playwright() as p:
            browser = None
            for i in range(5): # Retry 5 times
                try:
                    browser = await p.chromium.connect_over_cdp(cdp_url)
                    logger.info("Successfully connected to the browser.")
                    break # Success
                except Exception as e:
                    logger.warning(f"Failed to connect to browser, retrying in 2 seconds... ({i+1}/5)")
                    await asyncio.sleep(2) # Wait 2 seconds before retrying
            
            if not browser:
                logger.error("Could not connect to browser after multiple retries. Exiting.")
                return
            
            # Check if there are any existing contexts
            if browser.contexts:
                context = browser.contexts[0]
            else:
                # If no contexts, create a new one
                context = await browser.new_context()

            def on_page(page):
                logger.info(f"New page created for URL: {page.url}", tag="BROWSER")
                
                async def log_close():
                    await asyncio.sleep(1) # Give a moment for the url to be available
                    logger.info(f"Page closed for URL: {page.url}", tag="BROWSER")

                page.on("close", lambda: asyncio.create_task(log_close()))

            context.on("page", on_page)

            # Log existing pages
            for page in context.pages:
                logger.info(f"Existing page: {page.url}", tag="BROWSER")


            logger.info("Monitoring for new pages. Press Ctrl+C to shut down the browser.")
            
            await stop_event.wait()
            
    finally:
        logger.info("Cleaning up browser instance...")
        await managed_browser.cleanup()
        logger.info("Browser shut down.")

if __name__ == "__main__":
    asyncio.run(main())