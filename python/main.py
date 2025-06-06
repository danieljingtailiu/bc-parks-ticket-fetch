import asyncio
import aiohttp
import json
import time
import os
from datetime import datetime, timezone, timedelta
import pytz
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import Select
from selenium.common.exceptions import TimeoutException, NoSuchElementException
import logging
from date_utils import DateUtilMixin
from form_utils import FormUtilMixin

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class AdvancedTicketBot(DateUtilMixin,FormUtilMixin):
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
        
    def calculate_target_date(self):
        """Calculate the date that is 2 days after today"""
        today = datetime.now()
        days_ahead = self.config.get('settings', {}).get('days_ahead', 2)
        self.target_date = today + timedelta(days=days_ahead)
        logger.info(f"Target visit date: {self.target_date.strftime('%Y-%m-%d')}")
        
    def setup_driver(self):
        """Setup Chrome driver with optimized options for speed and stealth"""
        chrome_options = Options()
        
        # Test mode specific options
        if self.test_mode:
            headless = self.config.get('settings', {}).get('browser_headless', False)
            if headless:
                chrome_options.add_argument('--headless')
                logger.info("Running in headless mode for testing")
            else:
                logger.info("Running in visible mode for testing")
        else:
            # Production mode options
            chrome_options.add_argument('--no-sandbox')
            chrome_options.add_argument('--disable-dev-shm-usage')
            chrome_options.add_argument('--disable-blink-features=AutomationControlled')
            chrome_options.add_argument('--disable-extensions')
            chrome_options.add_argument('--disable-plugins')
            chrome_options.add_argument('--disable-images')  # Faster loading
        
        chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        chrome_options.add_experimental_option('useAutomationExtension', False)
        chrome_options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
        
        self.driver = webdriver.Chrome(options=chrome_options)
        self.driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
        
        # Set implicit wait based on test mode
        wait_timeout = self.config.get('settings', {}).get('wait_timeout', 10)
        self.driver.implicitly_wait(wait_timeout)
        
    def take_screenshot(self, step_name):
        """Take screenshot if enabled in test settings"""
        if self.test_settings.get('screenshot_steps', False):
            try:
                self.screenshot_counter += 1
                screenshots_dir = os.path.join(os.getcwd(), "screenshots")
                os.makedirs(screenshots_dir, exist_ok=True)
                filename = os.path.join(screenshots_dir, f"screenshot_{self.screenshot_counter:02d}_{step_name}.png")
                self.driver.save_screenshot(filename)
                logger.info(f"Screenshot saved: {filename}")
            except Exception as e:
                logger.warning(f"Failed to take screenshot: {e}")
    
    def wait_for_user_input(self, step_name):
        """Wait for user input if step-by-step mode is enabled"""
        if self.test_settings.get('step_by_step', False):
            input(f"Press Enter to continue after '{step_name}' step...")
    
    def simulate_step(self, step_name, actual_function):
        """Simulate a step if simulate_steps is enabled, otherwise execute normally"""
        if self.test_settings.get('simulate_steps', False):
            logger.info(f"SIMULATING: {step_name}")
            time.sleep(1)  # Simulate processing time
            return True
        else:
            return actual_function()
        
    async def wait_for_release_time(self):
        """Wait until exactly 7 AM Vancouver time, then refresh"""
        if self.skip_time_wait:
            logger.info("SKIPPING time wait due to test mode")
            return True
            
        vancouver_tz = pytz.timezone('America/Vancouver')
        release_time = self.config.get('settings', {}).get('vancouver_release_time', '07:00')
        hour, minute = map(int, release_time.split(':'))
        
        while True:
            now = datetime.now(vancouver_tz)
            target_time = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
            
            # If it's past release time today, target tomorrow
            if now.time() > target_time.time():
                target_time = target_time.replace(day=target_time.day + 1)
            
            time_diff = (target_time - now).total_seconds()
            
            if time_diff <= 0:
                logger.info(f"{release_time} Vancouver time reached! Refreshing site...")
                return True
                
            if time_diff <= 10:  # Get ready in the last 10 seconds
                logger.info(f"Getting ready... {time_diff:.1f} seconds remaining")
                await asyncio.sleep(0.1)
            elif time_diff <= 60:  # Check every second in the last minute
                logger.info(f"Almost time... {time_diff:.0f} seconds remaining")
                await asyncio.sleep(1)
            else:  # Check every 30 seconds otherwise
                logger.info(f"Waiting {time_diff:.0f} seconds until {release_time} Vancouver time...")
                await asyncio.sleep(30)

    def refresh_site(self):
        """Refresh the site at exactly release time"""
        def _refresh():
            try:
                logger.info("Refreshing the site...")
                self.driver.refresh()
                time.sleep(2)  # Allow page to load
                return True
            except Exception as e:
                logger.error(f"Failed to refresh site: {e}")
                return False
        
        return self.simulate_step("Refresh Site", _refresh)
    
    async def run_complete_flow(self):
        """Execute the complete ticket booking flow"""
        try:
            if self.test_mode:
                logger.info("🧪 RUNNING IN TEST MODE")
                if self.test_settings.get('verbose_logging', False):
                    logger.setLevel(logging.DEBUG)
            
            # Calculate target date
            self.calculate_target_date()
            
            # Setup browser and navigate to site
            self.setup_driver()
            logger.info(f"Navigating to: {self.config['ticket_url']}")
            self.driver.get(self.config['ticket_url'])
            
            self.take_screenshot("initial_page")
            self.wait_for_user_input("Initial page loaded")
            
            # Wait for release time and refresh (unless skipped)
            await self.wait_for_release_time()
            if not self.refresh_site():
                return False
            
            self.take_screenshot("after_refresh")
            self.wait_for_user_input("Page refreshed")
            
            # Step 1: Select specific park and click Book a Pass
            if not self.select_park_and_book():
                return False
            
            self.take_screenshot("park_selected")
            self.wait_for_user_input("Park selected and booking page loaded")
            
            # Step 2: Select visit date
            if not self.select_visit_date():
                return False
            
            self.take_screenshot("date_selected")
            self.wait_for_user_input("Date selected")
            
            if not self.select_pass_type():
                return False
            
            self.take_screenshot("pass_type_selected")
            self.wait_for_user_input("Pass type selected")
            
            # Step 3: Select Visit Time
            if not self.select_visit_time():
                return False

            self.take_screenshot("visit_time_selected")
            self.wait_for_user_input("Visit time selected")

            # Step 4: Click Next
            if not self.click_next_button():
                return False
            
            self.take_screenshot("next_clicked")
            self.wait_for_user_input("Next button clicked")
            
            # Step 5: Fill form details
            if not self.fill_form_details():
                return False
            
            self.take_screenshot("form_filled")
            self.wait_for_user_input("Form filled")
            
            # Step 6: Accept terms and conditions
            if not self.accept_terms_and_conditions():
                return False
            
            self.take_screenshot("terms_accepted")
            self.wait_for_user_input("Terms accepted")
            
            # Step 7: Submit form
            if not self.submit_form():
                return False
            
            self.take_screenshot("form_submitted")
            
            # Wait for confirmation
            keep_open_time = self.config.get('settings', {}).get('keep_browser_open_seconds', 10)
            time.sleep(keep_open_time)
            logger.info("✅ Complete booking flow executed successfully!")
            return True
            
        except Exception as e:
            logger.error(f"Complete flow failed: {e}")
            return False
        
        finally:
            if self.driver:
                self.driver.quit()

def load_config():
    """Load configuration from config file"""
    try:
        # Try to load from config.py first
        try:
            from config import config
            logger.info("Loaded configuration from config.py")
            return config
        except ImportError:
            pass
        
        # Try to load from config.json
        try:
            with open('config.json', 'r') as f:
                config = json.load(f)
                logger.info("Loaded configuration from config.json")
                return config
        except FileNotFoundError:
            pass
        
        # Fallback to default configuration
        logger.warning("No config file found, using default configuration")
        return {
            'ticket_url': 'https://reserve.bcparks.ca/dayuse/',
            'form_data': {
                'first_name': 'John',
                'last_name': 'Doe',
                'email': 'example@email.com'
            },
            'settings': {
                'wait_timeout': 10,
                'vancouver_release_time': '07:00',
                'days_ahead': 2,
                'browser_headless': False,
                'keep_browser_open_seconds': 10,
                'test_mode': False,
                'skip_time_wait': False
            },
            'test_settings': {},
            'selected_park': 'joffre_lakes',
            'parks': {
                'golden_ears': {
                    'name': 'Golden Ears Provincial Park',
                    'search_text': 'Golden Ears'
                },
                'joffre_lakes': {
                    'name': 'Joffre Lakes Provincial Park', 
                    'search_text': 'Joffre'
                }
            }
        }
        
    except Exception as e:
        logger.error(f"Failed to load configuration: {e}")
        return None

async def main():
    """Main function to run the bot"""
    try:
        # Load configuration
        config = load_config()
        if not config:
            logger.error("Failed to load configuration. Exiting.")
            return
        
        # Validate configuration
        if not config.get('form_data', {}).get('email'):
            logger.error("Email is required in form_data. Please check your config.")
            return
        
        if not config.get('form_data', {}).get('first_name'):
            logger.error("First name is required in form_data. Please check your config.")
            return
        
        if not config.get('form_data', {}).get('last_name'):
            logger.error("Last name is required in form_data. Please check your config.")
            return
        
        # Create and run the bot
        bot = AdvancedTicketBot(config)
        
        logger.info("🎫 BC Parks Ticket Bot Starting...")
        logger.info(f"Selected Park: {bot.parks.get(bot.selected_park, {}).get('name', bot.selected_park)}")
        logger.info(f"Test Mode: {'ON' if bot.test_mode else 'OFF'}")
        
        if bot.test_mode:
            logger.info("Test Settings:")
            for key, value in bot.test_settings.items():
                logger.info(f"  {key}: {value}")
        
        success = await bot.run_complete_flow()
        
        if success:
            logger.info("🎉 Bot completed successfully!")
        else:
            logger.error("❌ Bot failed to complete the booking process")
            
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
    except Exception as e:
        logger.error(f"Unexpected error: {e}")

if __name__ == "__main__":
    # Run the bot
    asyncio.run(main())