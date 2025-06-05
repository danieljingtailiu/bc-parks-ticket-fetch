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

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class AdvancedTicketBot:
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
    
    def select_park_and_book(self):
        def _select_and_book():
            try:
                park_info = self.parks.get(self.selected_park, {})
                park_name = park_info.get('name', self.selected_park)
                search_text = park_info.get('search_text', park_name)
                
                logger.info(f"Looking for {park_name} on BC Parks website...")
                
                # Perform single scroll to reach park listings
                logger.info("Scrolling to park listings...")
                self.driver.execute_script("window.scrollTo(0, 1000);")
                time.sleep(0.5)  # Minimal wait after scroll for speed
                
                # Target the "Book a Pass" button within the Joffre Lakes card
                wait_timeout = self.config.get('settings', {}).get('wait_timeout', 10)
                wait = WebDriverWait(self.driver, wait_timeout)
                
                # Specific selector for the button after the park name
                selector = f"//*[contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), '{search_text.lower()}')]//following::button[contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'book a pass')][1]"
                
                try:
                    book_button = wait.until(EC.element_to_be_clickable((By.XPATH, selector)))
                    logger.info(f"Found booking button: {book_button.text}")
                except TimeoutException:
                    logger.error(f"Could not find 'Book a Pass' button for {park_name}")
                    self.take_screenshot("park_not_found_debug")
                    page_text = self.driver.find_element(By.TAG_NAME, "body").text
                    logger.debug(f"Available page text: {page_text[:500]}...")
                    return False
                
                # Scroll and click the button
                self.driver.execute_script("arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});", book_button)
                time.sleep(0.5)  # Minimal wait for scroll
                book_button.click()
                logger.info(f"Successfully clicked booking button for {park_name}")
                time.sleep(1)  # Minimal wait for page transition
                return True
                
            except Exception as e:
                logger.error(f"Failed to select park and book: {e}")
                return False
        
        return self.simulate_step("Select Park and Book", _select_and_book)
    
    def select_visit_date(self):
        def _select_date():
            try:
                logger.info(f"Selecting visit date: {self.target_date.strftime('%Y-%m-%d')}")
                
                wait_timeout = self.config.get('settings', {}).get('wait_timeout', 10)
                wait = WebDriverWait(self.driver, wait_timeout)
                
                # Locate the "Visit Date" label
                label_selector = "//*[contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'visit date') and (self::label or self::span or self::div or self::p)]"
                try:
                    label_element = wait.until(EC.presence_of_element_located((By.XPATH, label_selector)))
                    logger.info("Found Visit Date label element")
                except TimeoutException as e:
                    logger.error(f"Could not find Visit Date label: {e}")
                    self.take_screenshot("visit_date_label_not_found")
                    return False
                
                # Locate the calendar button following the label
                date_button_selector = "//*[contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'visit date')]//following::button[contains(@class, 'date-input__calendar-btn') and contains(@class, 'form-control') and @title='Select a Date'][1]"
                try:
                    date_button = wait.until(EC.element_to_be_clickable((By.XPATH, date_button_selector)))
                    logger.info("Found Visit Date button element")
                except TimeoutException as e:
                    logger.error(f"Could not find Visit Date button: {e}")
                    self.take_screenshot("visit_date_button_not_found")
                    return False
                
                # Debug: Log the outer HTML of the button
                button_html = self.driver.execute_script("return arguments[0].outerHTML;", date_button)
                logger.info(f"Visit Date button HTML: {button_html}")
                
                # Scroll to the element to ensure visibility
                self.driver.execute_script("arguments[0].scrollIntoView(true);", date_button)
                time.sleep(0.1)  # Brief wait for scroll
                
                # Click the button to open the date table
                logger.info("Attempting to open date table by clicking the Visit Date button...")
                try:
                    date_button.click()  # Try native click first
                    time.sleep(0.3)  # Wait for the date table to appear
                except Exception as e:
                    logger.warning(f"Native click failed, falling back to JavaScript: {e}")
                    self.driver.execute_script("arguments[0].click();", date_button)
                    time.sleep(0.3)  # Wait for the date table to appear
                
                # Wait for the date table to be visible
                date_table_selector = ".datepicker-days, .table-condensed, [class*='calendar-days'], [role='application'][class*='datepicker']"
                try:
                    wait.until(EC.visibility_of_element_located((By.CSS_SELECTOR, date_table_selector)))
                    logger.info("Date table opened successfully")
                except TimeoutException:
                    logger.error("Date table did not appear after clicking")
                    self.take_screenshot("date_table_not_found")
                    return False
                
                # Wait a bit for the date table to be fully interactable
                time.sleep(0.2)
                
                # Target date components
                target_year = self.target_date.strftime('%Y')  # "2025"
                target_month = self.target_date.strftime('%m')  # "06"
                target_day = self.target_date.strftime('%d').lstrip('0')  # "7"
                
                # Verify the current month and year (should already be June 2025)
                try:
                    month_year = wait.until(EC.visibility_of_element_located((By.CSS_SELECTOR, ".datepicker-switch, [class*='month-year']")))
                    current_month_year = month_year.text  # e.g., "June 2025"
                    logger.info(f"Current month and year in date table: {current_month_year}")
                    current_month, current_year = current_month_year.split()
                    current_month_num = datetime.strptime(current_month, '%B').strftime('%m')
                    
                    if current_year != target_year or current_month_num != target_month:
                        logger.error(f"Date table is not on the correct month. Expected {target_month} {target_year}, but got {current_month_num} {current_year}")
                        self.take_screenshot("wrong_month")
                        return False
                    logger.info(f"Confirmed date table is on {current_month} {current_year}")
                except Exception as e:
                    logger.error(f"Failed to verify current month in date table: {e}")
                    self.take_screenshot("month_verification_failed")
                    return False
                
                # Select the target day
                day_selector = f"//td[contains(@class, 'day') and not(contains(@class, 'old') or contains(@class, 'new')) and normalize-space(text())='{target_day}']"
                try:
                    day_element = wait.until(EC.element_to_be_clickable((By.XPATH, day_selector)))
                    logger.info(f"Found day element for {target_day}")
                    
                    # Debug: Log the outer HTML of the day element
                    day_html = self.driver.execute_script("return arguments[0].outerHTML;", day_element)
                    logger.info(f"Day element HTML: {day_html}")
                    
                    # Scroll to the day element and click
                    self.driver.execute_script("arguments[0].scrollIntoView(true);", day_element)
                    time.sleep(0.1)
                    day_element.click()  # Try native click
                    logger.info(f"Clicked target day: {target_day}")
                    time.sleep(0.2)  # Wait for the date table to close
                except Exception as e:
                    logger.error(f"Failed to select target day: {e}")
                    self.take_screenshot("day_selection_failed")
                    return False
                
                # Verify the input field updated
                date_input = wait.until(EC.presence_of_element_located((By.XPATH, "//input[@id='visitDate']")))
                selected_date = date_input.get_attribute('value')
                logger.info(f"Selected date in input field: {selected_date}")
                if selected_date != self.target_date.strftime('%Y-%m-%d'):
                    logger.error(f"Date input did not update correctly. Expected {self.target_date.strftime('%Y-%m-%d')}, but got {selected_date}")
                    self.take_screenshot("date_input_verification_failed")
                    return False
                
                logger.info("Visit date selected successfully")
                return True
                
            except Exception as e:
                logger.error(f"Failed to select visit date: {e}")
                self.take_screenshot("date_selection_failed")
                return False
        
        return self.simulate_step("Select Visit Date", _select_date)
    
    def select_first_pass_type(self):
        def _select_pass():
            try:
                logger.info("Selecting first pass type option...")
                
                wait_timeout = self.config.get('settings', {}).get('wait_timeout', 10)
                wait = WebDriverWait(self.driver, wait_timeout)
                
                # Target the pass type dropdown
                pass_selector = "select[name*='pass'], select[name*='type'], select[id*='pass'], select[id*='type'], .pass-type select"
                pass_element = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, pass_selector)))
                
                if pass_element.tag_name == 'select':
                    select = Select(pass_element)
                    # Select the first non-empty option
                    options = select.options
                    for option in options[1:]:  # Skip the "--Select a pass type--" placeholder
                        if option.get_attribute('value') and option.get_attribute('value') != '':
                            select.select_by_value(option.get_attribute('value'))
                            logger.info(f"Selected pass type: {option.text}")
                            time.sleep(0.5)  # Minimal wait for page update
                            return True
                    logger.error("No valid pass type options found")
                    return False
                else:
                    logger.error("Could not find pass type dropdown or unsupported element type")
                    return False
                    
            except Exception as e:
                logger.error(f"Failed to select pass type: {e}")
                return False
        
        return self.simulate_step("Select Pass Type", _select_pass)
    
    def click_next_button(self):
        """Click the Next button"""
        def _click_next():
            try:
                logger.info("Clicking Next button...")
                
                next_selectors = [
                    "//button[contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'next')]",
                    "//input[@type='submit' and contains(translate(@value, 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'next')]",
                    "//a[contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'next')]",
                    "button[id*='next']",
                    "button[class*='next']",
                    ".next-btn",
                    ".btn-next",
                    "input[type='submit']"
                ]
                
                wait_timeout = self.config.get('settings', {}).get('wait_timeout', 10)
                wait = WebDriverWait(self.driver, wait_timeout)
                
                for selector in next_selectors:
                    try:
                        if selector.startswith('//'):
                            next_button = wait.until(EC.element_to_be_clickable((By.XPATH, selector)))
                        else:
                            next_button = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, selector)))
                        
                        next_button.click()
                        logger.info("Next button clicked successfully")
                        time.sleep(3)  # Wait for page to load
                        return True
                    except:
                        continue
                
                logger.error("Could not find Next button")
                return False
                
            except Exception as e:
                logger.error(f"Failed to click Next button: {e}")
                return False
        
        return self.simulate_step("Click Next Button", _click_next)
    
    def fill_form_details(self):
        """Fill out the form with personal details"""
        def _fill_form():
            try:
                logger.info("Filling out form details...")
                
                form_data = self.config['form_data']
                wait_timeout = self.config.get('settings', {}).get('wait_timeout', 10)
                wait = WebDriverWait(self.driver, wait_timeout)
                
                # Fill first name
                first_name_selectors = [
                    "input[name*='first']",
                    "input[id*='first']",
                    "input[placeholder*='First']",
                    "input[name*='fname']",
                    "input[id*='fname']"
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
                    "input[placeholder*='Last']",
                    "input[name*='lname']",
                    "input[id*='lname']"
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
        
        return self.simulate_step("Fill Form Details", _fill_form)
    
    def accept_terms_and_conditions(self):
        """Click the 'I have read and agree' checkbox"""
        def _accept_terms():
            try:
                logger.info("Accepting terms and conditions...")
                
                terms_selectors = [
                    "input[type='checkbox'][name*='agree']",
                    "input[type='checkbox'][id*='agree']",
                    "input[type='checkbox'][name*='terms']",
                    "input[type='checkbox'][id*='terms']",
                    "input[type='checkbox'][name*='notice']",
                    "input[type='checkbox'][id*='notice']",
                    "input[type='checkbox'][name*='accept']",
                    "input[type='checkbox'][id*='accept']"
                ]
                
                wait_timeout = self.config.get('settings', {}).get('wait_timeout', 10)
                wait = WebDriverWait(self.driver, wait_timeout)
                
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
        
        return self.simulate_step("Accept Terms", _accept_terms)
    
    def submit_form(self):
        """Submit the final form"""
        def _submit():
            try:
                logger.info("Submitting form...")
                
                submit_selectors = [
                    "button[type='submit']",
                    "input[type='submit']",
                    "//button[contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'submit')]",
                    "//button[contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'book')]",
                    "//button[contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'confirm')]",
                    "//input[@type='submit']",
                    ".submit-btn",
                    "#submit"
                ]
                
                wait_timeout = self.config.get('settings', {}).get('wait_timeout', 10)
                wait = WebDriverWait(self.driver, wait_timeout)
                
                for selector in submit_selectors:
                    try:
                        if selector.startswith('//'):
                            submit_button = wait.until(EC.element_to_be_clickable((By.XPATH, selector)))
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
        
        return self.simulate_step("Submit Form", _submit)

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
            
            # Step 3: Choose first pass type option
            if not self.select_first_pass_type():
                return False
            
            self.take_screenshot("pass_type_selected")
            self.wait_for_user_input("Pass type selected")
            
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