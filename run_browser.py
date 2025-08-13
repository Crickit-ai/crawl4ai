
import asyncio
import signal
from crawl4ai.browser_manager import ManagedBrowser
from crawl4ai.async_configs import BrowserConfig
from crawl4ai.async_logger import get_logger

async def main():
    """
    Launches and manages a persistent browser instance.
    """
    logger = get_logger()
    browser_config = BrowserConfig(
        use_managed_browser=True,
        headless=False,  # Set to False to see the browser UI
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
        logger.info("Press Ctrl+C to shut down the browser.")
        
        await stop_event.wait()
        
    finally:
        logger.info("Cleaning up browser instance...")
        await managed_browser.cleanup()
        logger.info("Browser shut down.")

if __name__ == "__main__":
    asyncio.run(main())
