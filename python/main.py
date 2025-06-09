import asyncio
import json
import time
import os
import sys
import shutil
from datetime import datetime, timezone, timedelta
import pytz
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import TimeoutException, NoSuchElementException, ElementClickInterceptedException
import logging
import random
import undetected_chromedriver as uc
from selenium.webdriver.common.action_chains import ActionChains

from date_utils import DateUtilMixin
from form_utils import FormUtilMixin

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class AdvancedTicketBot(DateUtilMixin, FormUtilMixin):
    def __init__(self, config):
        self.config = config
        self.driver = None
        self.target_date = None
        self.test_mode = config.get('settings', {}).get('test_mode', False)
        self.skip_time_wait = config.get('settings', {}).get('skip_time_wait', False)
        self.test_settings = config.get('test_settings', {})
        self.screenshot_counter = 0
        self.selected_park = config.get('selected_park', 'joffre_lakes')
        self.parks = config.get('parks', {})
        self.cloudflare_bypass_enabled = config.get('settings', {}).get('cloudflare_bypass', True)

    def setup_driver(self):
        """Setup the driver, defaulting to the stealth version."""
        if self.cloudflare_bypass_enabled:
            logger.info("Attempting to set up stealth (undetected-chromedriver) driver.")
            return self.setup_stealth_driver()
        else:
            logger.error("Standard driver is not supported for this script. Aborting.")
            return False

    def setup_stealth_driver(self):
        """Setup with undetected-chromedriver and a persistent user profile."""
        try:
            options = uc.ChromeOptions()
            profile_path = self.config.get('settings', {}).get('cf-clearance_path', {})
            
            if not os.path.exists(profile_path):
                os.makedirs(profile_path)
            logger.info(f"Using persistent profile directory: {profile_path}")
            options.add_argument(f"--user-data-dir={profile_path}")
            options.add_argument(r'--profile-directory=Default')

            options.add_argument('--disable-blink-features=AutomationControlled')
            options.add_argument("--start-maximized")
            
            self.driver = uc.Chrome(options=options, use_subprocess=True)
            
            wait_timeout = self.config.get('settings', {}).get('wait_timeout', 15)
            self.driver.implicitly_wait(wait_timeout)
            logger.info("Stealth driver with persistent profile setup completed.")
            return True
        except Exception as e:
            logger.error(f"CRITICAL: Stealth driver setup failed. Error: {e}", exc_info=True)
            logger.error("This can happen if a Chrome process is already running using this profile. Close ALL Chrome windows and try again.")
            return False

    def calculate_target_date(self):
        """Calculate the date based on config."""
        today = datetime.now()
        days_ahead = self.config.get('settings', {}).get('days_ahead', 2)
        self.target_date = today + timedelta(days=days_ahead)
        logger.info(f"Target visit date: {self.target_date.strftime('%Y-%m-%d')}")

    def take_screenshot(self, step_name):
        """Take screenshot if enabled in test settings."""
        if self.test_settings.get('screenshot_steps', False):
            try:
                self.screenshot_counter += 1
                screenshots_dir = os.path.join(os.path.dirname(__file__), "..", "screenshots")
                os.makedirs(screenshots_dir, exist_ok=True)
                filename = os.path.join(screenshots_dir, f"screenshot_{self.screenshot_counter:02d}_{step_name}.png")
                self.driver.save_screenshot(filename)
                logger.info(f"Screenshot saved: {filename}")
            except Exception as e:
                logger.warning(f"Failed to take screenshot: {e}")

    def wait_for_user_input(self, step_name):
        """Wait for user input if step-by-step mode is enabled."""
        if self.test_settings.get('step_by_step', False):
            input(f"Press Enter to continue after '{step_name}' step...")

    def simulate_step(self, step_name, actual_function):
        """Simulate a step if simulate_steps is enabled, otherwise execute normally"""
        if self.test_settings.get('simulate_steps', False):
            logger.info(f"SIMULATING: {step_name}")
            time.sleep(1)
            return True
        else:
            return actual_function()

    async def wait_for_release_time(self):
        """Wait until the configured release time in Vancouver time zone."""
        if self.skip_time_wait:
            logger.info("SKIPPING time wait due to test mode settings.")
            return True
            
        vancouver_tz = pytz.timezone('America/Vancouver')
        release_time_str = self.config.get('settings', {}).get('vancouver_release_time', '07:00')
        hour, minute = map(int, release_time_str.split(':'))
        
        while True:
            now_vancouver = datetime.now(vancouver_tz)
            target_time = now_vancouver.replace(hour=hour, minute=minute, second=0, microsecond=0)
            
            if now_vancouver.time() >= target_time.time():
                logger.info(f"It's past {release_time_str} Vancouver time. Proceeding.")
                return True
            
            time_diff = (target_time - now_vancouver).total_seconds()
            
            if time_diff <= 10:
                logger.info(f"Getting ready... {time_diff:.1f} seconds remaining.")
                await asyncio.sleep(0.1)
            elif time_diff <= 60:
                logger.info(f"Almost time... {time_diff:.0f} seconds remaining.")
                await asyncio.sleep(1)
            else:
                logger.info(f"Waiting for release. {time_diff:.0f} seconds remaining.")
                await asyncio.sleep(30)

    def refresh_site(self):
        """Refreshes the current page."""
        try:
            logger.info("Refreshing the site...")
            self.driver.refresh()
            time.sleep(random.uniform(2.0, 3.5))
            return True
        except Exception as e:
            logger.error(f"Failed to refresh site: {e}")
            return False

    async def run_complete_flow(self):
        """
        Executes the booking flow by warming up the session, then
        racing through the selections after the 7 AM refresh.
        """
        try:
            self.calculate_target_date()
            if not self.setup_driver():
                logger.error("Driver setup failed. Aborting flow.")
                return False

            # --- PRE-7 AM: SESSION WARM-UP (Build Trust) ---
            logger.info("--- Starting Session WARM-UP Phase ---")
            
            logger.info(f"Navigating to: {self.config['ticket_url']} to build a clean session.")
            self.driver.get(self.config['ticket_url'])
            
            logger.info("Session started. Simulating human presence before release time...")
            time.sleep(random.uniform(5, 12))
            
            for _ in range(random.randint(1, 3)):
                self.driver.execute_script(f"window.scrollBy(0, {random.randint(50, 200)});")
                time.sleep(random.uniform(0.6, 1.5))

            logger.info("--- WARM-UP Complete. Waiting for release time. ---")
            
            # --- AT 7 AM: THE RACE (Maximum Speed) ---
            await self.wait_for_release_time()
            
            logger.info("--- GO-TIME! Refreshing and beginning high-speed selection! ---")
            if not self.refresh_site(): return False
            self.wait_for_user_input("Page refreshed, now racing at max speed")
            
            if not self.select_park_and_book(): return False
            if not self.select_visit_date(): return False
            if not self.select_pass_type(): return False
            if not self.select_visit_time(): return False
            if not self.click_next_button(): return False
            if not self.fill_form_details(): return False
            if not self.accept_terms_and_conditions(): return False
            if not self.submit_form(): return False
            
            logger.info("✅ Complete booking flow executed successfully!")
            keep_open_time = self.config.get('settings', {}).get('keep_browser_open_seconds', 15)
            logger.info(f"Process finished. Browser will remain open for {keep_open_time} seconds.")
            time.sleep(keep_open_time)
            return True
            
        except Exception as e:
            logger.error(f"Complete flow failed with an unexpected error: {e}", exc_info=True)
            self.take_screenshot("flow_failure")
            return False
        
        finally:
            if self.driver:
                if self.test_mode or 'pydevd' in sys.modules:
                    logger.info("Debug/Test mode active. Keeping browser open for 60 seconds.")
                    time.sleep(60)
                self.driver.quit()
                logger.info("Browser has been closed.")

# --- CONFIGURATION LOADER ---
def load_config():
    """Load configuration from config.py or config.json"""
    try:
        from config import config
        logger.info("Loaded configuration from config.py")
        return config
    except ImportError:
        try:
            with open('config.json', 'r') as f:
                config = json.load(f)
                logger.info("Loaded configuration from config.json")
                return config
        except FileNotFoundError:
            logger.error("FATAL: No config file found. Please create 'config.py' or 'config.json'.")
            return None
    except Exception as e:
        logger.error(f"Failed to load configuration: {e}")
        return None

# --- MAIN EXECUTION ---
async def main():
    """Main function to initialize and run the bot."""
    config = load_config()
    if not config:
        logger.error("Failed to load configuration. Exiting.")
        return
        
    bot = AdvancedTicketBot(config)
    
    logger.info("🎫 BC Parks Ticket Bot Starting...")
    park_info = bot.parks.get(bot.selected_park, {})
    logger.info(f"Selected Park: {park_info.get('name', bot.selected_park)}")
    logger.info(f"Test Mode: {'ON' if bot.test_mode else 'OFF'}")
    
    await bot.run_complete_flow()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("\nBot stopped by user.")
