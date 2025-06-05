import asyncio
import aiohttp
import json
import time
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

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class AdvancedTicketBot:
    def __init__(self, config):
        self.config = config
        self.driver = None
        self.target_date = None
        
    def calculate_target_date(self):
        """Calculate the date that is 2 days after today"""
        today = datetime.now()
        self.target_date = today + timedelta(days=2)
        logger.info(f"Target visit date: {self.target_date.strftime('%Y-%m-%d')}")
        
    def setup_driver(self):
        """Setup Chrome driver with optimized options for speed and stealth"""
        chrome_options = Options()
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
        self.driver.implicitly_wait(2)
        
    async def wait_for_release_time(self):
        """Wait until exactly 7 AM Vancouver time, then refresh"""
        vancouver_tz = pytz.timezone('America/Vancouver')
        
        while True:
            now = datetime.now(vancouver_tz)
            target_time = now.replace(hour=7, minute=0, second=0, microsecond=0)
            
            # If it's past 7 AM today, target tomorrow
            if now.time() > target_time.time():
                target_time = target_time.replace(day=target_time.day + 1)
            
            time_diff = (target_time - now).total_seconds()
            
            if time_diff <= 0:
                logger.info("7 AM Vancouver time reached! Refreshing site...")
                return True
                
            if time_diff <= 10:  # Get ready in the last 10 seconds
                logger.info(f"Getting ready... {time_diff:.1f} seconds remaining")
                await asyncio.sleep(0.1)
            elif time_diff <= 60:  # Check every second in the last minute
                logger.info(f"Almost time... {time_diff:.0f} seconds remaining")
                await asyncio.sleep(1)
            else:  # Check every 30 seconds otherwise
                logger.info(f"Waiting {time_diff:.0f} seconds until 7 AM Vancouver time...")
                await asyncio.sleep(30)
    
    def refresh_site(self):
        """Refresh the site at exactly 7 AM"""
        try:
            logger.info("Refreshing the site...")
            self.driver.refresh()
            time.sleep(2)  # Allow page to load
            return True
        except Exception as e:
            logger.error(f"Failed to refresh site: {e}")
            return False
    
    def select_visit_date(self):
        """Select the visit date (2 days after today)"""
        try:
            logger.info(f"Selecting visit date: {self.target_date.strftime('%Y-%m-%d')}")
            
            # Common date selector patterns
            date_selectors = [
                "input[type='date']",
                "select[name*='date']",
                "select[id*='date']",
                ".date-picker",
                ".datepicker",
                "[data-date-picker]"
            ]
            
            wait = WebDriverWait(self.driver, 10)
            date_element = None
            
            for selector in date_selectors:
                try:
                    date_element = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, selector)))
                    break
                except:
                    continue
            
            if date_element:
                if date_element.tag_name == 'input':
                    # For date input fields
                    date_string = self.target_date.strftime('%Y-%m-%d')
                    date_element.clear()
                    date_element.send_keys(date_string)
                elif date_element.tag_name == 'select':
                    # For dropdown selectors
                    select = Select(date_element)
                    # Try different date formats
                    date_formats = [
                        self.target_date.strftime('%Y-%m-%d'),
                        self.target_date.strftime('%m/%d/%Y'),
                        self.target_date.strftime('%d/%m/%Y')
                    ]
                    for date_format in date_formats:
                        try:
                            select.select_by_value(date_format)
                            break
                        except:
                            continue
                else:
                    # For clickable date elements
                    date_element.click()
                
                logger.info("Visit date selected successfully")
                return True
            else:
                logger.error("Could not find date selector")
                return False
                
        except Exception as e:
            logger.error(f"Failed to select visit date: {e}")
            return False
    
    def select_first_pass_type(self):
        """Select the first option in the pass type"""
        try:
            logger.info("Selecting first pass type option...")
            
            # Common pass type selector patterns
            pass_selectors = [
                "select[name*='pass']",
                "select[name*='type']",
                "select[id*='pass']",
                "select[id*='type']",
                ".pass-type select",
                ".ticket-type select",
                "[data-pass-type] select"
            ]
            
            wait = WebDriverWait(self.driver, 10)
            
            for selector in pass_selectors:
                try:
                    pass_element = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, selector)))
                    select = Select(pass_element)
                    
                    # Select the first non-empty option
                    options = select.options
                    for option in options[1:]:  # Skip first if it's a placeholder
                        if option.get_attribute('value') and option.get_attribute('value') != '':
                            select.select_by_value(option.get_attribute('value'))
                            logger.info(f"Selected pass type: {option.text}")
                            return True
                    
                except:
                    continue
            
            logger.error("Could not find or select pass type")
            return False
            
        except Exception as e:
            logger.error(f"Failed to select pass type: {e}")
            return False
    
    def click_booking_time_button(self):
        """Click on the booking time button"""
        try:
            logger.info("Clicking booking time button...")
            
            booking_selectors = [
                "button:contains('booking')",
                "button:contains('time')",
                "button[id*='booking']",
                "button[class*='booking']",
                ".booking-time button",
                ".time-slot button",
                "[data-booking] button"
            ]
            
            wait = WebDriverWait(self.driver, 10)
            
            for selector in booking_selectors:
                try:
                    if ':contains(' in selector:
                        # Handle text-based selectors
                        search_text = selector.split('contains(')[1].split(')')[0].strip("'")
                        xpath_selector = f"//button[contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), '{search_text}')]"
                        booking_button = wait.until(EC.element_to_be_clickable((By.XPATH, xpath_selector)))
                    else:
                        booking_button = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, selector)))
                    
                    booking_button.click()
                    logger.info("Booking time button clicked successfully")
                    return True
                except:
                    continue
            
            logger.error("Could not find booking time button")
            return False
            
        except Exception as e:
            logger.error(f"Failed to click booking time button: {e}")
            return False
    
    def click_next_button(self):
        """Click the Next button"""
        try:
            logger.info("Clicking Next button...")
            
            next_selectors = [
                "button:contains('next')",
                "input[value*='Next']",
                "button[id*='next']",
                "button[class*='next']",
                ".next-btn",
                ".btn-next"
            ]
            
            wait = WebDriverWait(self.driver, 10)
            
            for selector in next_selectors:
                try:
                    if ':contains(' in selector:
                        xpath_selector = "//button[contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'next')] | //input[contains(translate(@value, 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'next')]"
                        next_button = wait.until(EC.element_to_be_clickable((By.XPATH, xpath_selector)))
                    else:
                        next_button = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, selector)))
                    
                    next_button.click()
                    logger.info("Next button clicked successfully")
                    return True
                except:
                    continue
            
            logger.error("Could not find Next button")
            return False
            
        except Exception as e:
            logger.error(f"Failed to click Next button: {e}")
            return False
    
    def handle_cloudflare_popup(self):
        """Handle Cloudflare verification popup"""
        try:
            logger.info("Waiting for Cloudflare verification...")
            
            # Wait for Cloudflare challenge to appear and complete
            wait = WebDriverWait(self.driver, 60)  # Extended timeout for Cloudflare
            
            # Look for common Cloudflare indicators
            cloudflare_indicators = [
                "Checking your browser",
                "DDoS protection by Cloudflare",
                "Please wait while we verify",
                "cf-browser-verification"
            ]
            
            # Wait until Cloudflare verification is complete
            def cloudflare_complete(driver):
                page_source = driver.page_source.lower()
                return not any(indicator.lower() in page_source for indicator in cloudflare_indicators)
            
            wait.until(cloudflare_complete)
            logger.info("Cloudflare verification completed")
            time.sleep(2)  # Additional wait to ensure page is fully loaded
            return True
            
        except TimeoutException:
            logger.error("Cloudflare verification timed out")
            return False
        except Exception as e:
            logger.error(f"Cloudflare verification failed: {e}")
            return False
    
    def fill_form_details(self):
        """Fill out the form with personal details"""
        try:
            logger.info("Filling out form details...")
            
            form_data = self.config['form_data']
            wait = WebDriverWait(self.driver, 15)
            
            # Fill first name
            first_name_selectors = [
                "input[name*='first']",
                "input[id*='first']",
                "input[placeholder*='First']"
            ]
            
            for selector in first_name_selectors:
                try:
                    first_name_field = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, selector)))
                    first_name_field.clear()
                    first_name_field.send_keys(form_data['first_name'])
                    logger.info("First name filled")
                    break
                except:
                    continue
            
            # Fill last name
            last_name_selectors = [
                "input[name*='last']",
                "input[id*='last']",
                "input[placeholder*='Last']"
            ]
            
            for selector in last_name_selectors:
                try:
                    last_name_field = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, selector)))
                    last_name_field.clear()
                    last_name_field.send_keys(form_data['last_name'])
                    logger.info("Last name filled")
                    break
                except:
                    continue
            
            # Fill email
            email_selectors = [
                "input[type='email']",
                "input[name*='email']",
                "input[id*='email']"
            ]
            
            email_fields = []
            for selector in email_selectors:
                try:
                    fields = self.driver.find_elements(By.CSS_SELECTOR, selector)
                    email_fields.extend(fields)
                except:
                    continue
            
            # Fill first email field
            if len(email_fields) >= 1:
                email_fields[0].clear()
                email_fields[0].send_keys(form_data['email'])
                logger.info("Email filled")
            
            # Fill retype email field (if exists)
            if len(email_fields) >= 2:
                email_fields[1].clear()
                email_fields[1].send_keys(form_data['email'])
                logger.info("Retype email filled")
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to fill form details: {e}")
            return False
    
    def accept_terms_and_conditions(self):
        """Click the 'I have read and agree' checkbox"""
        try:
            logger.info("Accepting terms and conditions...")
            
            terms_selectors = [
                "input[type='checkbox'][name*='agree']",
                "input[type='checkbox'][id*='agree']",
                "input[type='checkbox'][name*='terms']",
                "input[type='checkbox'][id*='terms']",
                "input[type='checkbox'][name*='notice']",
                "input[type='checkbox'][id*='notice']"
            ]
            
            wait = WebDriverWait(self.driver, 10)
            
            for selector in terms_selectors:
                try:
                    checkbox = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, selector)))
                    if not checkbox.is_selected():
                        checkbox.click()
                        logger.info("Terms and conditions accepted")
                        return True
                except:
                    continue
            
            logger.error("Could not find terms and conditions checkbox")
            return False
            
        except Exception as e:
            logger.error(f"Failed to accept terms: {e}")
            return False
    
    def submit_form(self):
        """Submit the final form"""
        try:
            logger.info("Submitting form...")
            
            submit_selectors = [
                "button[type='submit']",
                "input[type='submit']",
                "button:contains('submit')",
                "button:contains('book')",
                "button:contains('confirm')",
                ".submit-btn",
                "#submit"
            ]
            
            wait = WebDriverWait(self.driver, 10)
            
            for selector in submit_selectors:
                try:
                    if ':contains(' in selector:
                        text = selector.split('contains(')[1].split(')')[0].strip("'")
                        xpath_selector = f"//button[contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), '{text}')]"
                        submit_button = wait.until(EC.element_to_be_clickable((By.XPATH, xpath_selector)))
                    else:
                        submit_button = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, selector)))
                    
                    submit_button.click()
                    logger.info("Form submitted successfully!")
                    return True
                except:
                    continue
            
            logger.error("Could not find submit button")
            return False
            
        except Exception as e:
            logger.error(f"Failed to submit form: {e}")
            return False
    
    async def run_complete_flow(self):
        """Execute the complete ticket booking flow"""
        try:
            # Calculate target date
            self.calculate_target_date()
            
            # Setup browser and navigate to site
            self.setup_driver()
            logger.info(f"Navigating to: {self.config['ticket_url']}")
            self.driver.get(self.config['ticket_url'])
            
            # Wait for 7 AM Vancouver time and refresh
            await self.wait_for_release_time()
            if not self.refresh_site():
                return False
            
            # Step 1: Select visit date (2 days after today)
            if not self.select_visit_date():
                return False
            
            # Step 2: Choose first pass type option
            if not self.select_first_pass_type():
                return False
            
            # Step 3: Click booking time button
            if not self.click_booking_time_button():
                return False
            
            # Step 4: Click Next
            if not self.click_next_button():
                return False
            
            # Step 5: Handle Cloudflare popup
            if not self.handle_cloudflare_popup():
                return False
            
            # Step 6: Fill form details
            if not self.fill_form_details():
                return False
            
            # Step 7: Accept terms and conditions
            if not self.accept_terms_and_conditions():
                return False
            
            # Step 8: Submit form
            if not self.submit_form():
                return False
            
            # Wait for confirmation
            time.sleep(5)
            logger.info("✅ Complete booking flow executed successfully!")
            return True
            
        except Exception as e:
            logger.error(f"Complete flow failed: {e}")
            return False
        
        finally:
            if self.driver:
                # Keep browser open for a few seconds to see result
                time.sleep(10)
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
            'ticket_url': 'https://your-ticket-website.com',
            'form_data': {
                'first_name': 'John',
                'last_name': 'Doe',
                'email': 'john.doe@example.com'
            }
        }
        
    except Exception as e:
        logger.error(f"Error loading configuration: {e}")
        raise

# Run the advanced bot
async def main():
    config = load_config()
    bot = AdvancedTicketBot(config)
    success = await bot.run_complete_flow()
    
    if success:
        print("🎉 Advanced ticket bot completed successfully!")
    else:
        print("❌ Advanced ticket bot encountered an error")

if __name__ == "__main__":
    asyncio.run(main())