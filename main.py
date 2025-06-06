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
                
                # Scroll to the element to ensure visibility
                self.driver.execute_script("arguments[0].scrollIntoView(true);", date_button)
                time.sleep(0.2)
                
                # Click the button to open the date table
                logger.info("Attempting to open date table by clicking the Visit Date button...")
                try:
                    date_button.click()
                    time.sleep(1)  # Increased wait time for the date table to appear
                except Exception as e:
                    logger.warning(f"Native click failed, falling back to JavaScript: {e}")
                    self.driver.execute_script("arguments[0].click();", date_button)
                    time.sleep(1)
                
                # Wait for the date table to be visible with Angular Bootstrap selectors
                date_table_selectors = [
                    "div[ngbdatepickerdayview]",  # Angular Bootstrap specific
                    "ngb-datepicker",
                    "[class*='ngb-dp']",
                    ".datepicker-days",
                    ".table-condensed", 
                    "[class*='calendar-days']",
                    "[role='application'][class*='datepicker']",
                    ".datepicker",
                    ".calendar-table",
                    "table[class*='calendar']",
                    ".date-picker-table"
                ]
                
                date_table_found = False
                for selector in date_table_selectors:
                    try:
                        wait.until(EC.visibility_of_element_located((By.CSS_SELECTOR, selector)))
                        logger.info(f"Date table opened successfully with selector: {selector}")
                        date_table_found = True
                        break
                    except TimeoutException:
                        continue
                
                if not date_table_found:
                    logger.error("Date table did not appear after clicking")
                    self.take_screenshot("date_table_not_found")
                    return False
                
                time.sleep(0.5)  # Allow table to fully render
                
                # Calculate target date components
                today = datetime.now()
                target_year = self.target_date.year
                target_month = self.target_date.month
                target_day = self.target_date.day
                
                logger.info(f"Target date: {target_year}-{target_month:02d}-{target_day:02d}")
                logger.info(f"Today: {today.year}-{today.month:02d}-{today.day:02d}")
                
                # Navigate to the correct month if needed
                current_month = today.month
                current_year = today.year
                
                # Check if we need to navigate to next month
                if target_month > current_month or target_year > current_year:
                    logger.info(f"Need to navigate from {current_month}/{current_year} to {target_month}/{target_year}")
                    
                    # Multiple selectors for the "next" button
                    next_button_selectors = [
                        ".datepicker-days .next",
                        ".next",
                        "th.next",
                        "[class*='next']",
                        "//th[@class='next'][1]",
                        "//button[contains(@class, 'next')]",
                        "//a[contains(@class, 'next')]",
                        ".datepicker-switch + .next",
                        "th[title*='next']",
                        "th[title*='Next']"
                    ]
                    
                    months_to_advance = (target_year - current_year) * 12 + (target_month - current_month)
                    
                    for month_step in range(months_to_advance):
                        next_clicked = False
                        for selector in next_button_selectors:
                            try:
                                if selector.startswith('//'):
                                    next_btn = wait.until(EC.element_to_be_clickable((By.XPATH, selector)))
                                else:
                                    next_btn = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, selector)))
                                
                                # Try clicking
                                try:
                                    next_btn.click()
                                except:
                                    self.driver.execute_script("arguments[0].click();", next_btn)
                                
                                time.sleep(0.5)  # Wait for month to change
                                logger.info(f"Advanced to next month (step {month_step + 1}/{months_to_advance})")
                                next_clicked = True
                                break
                            except:
                                continue
                        
                        if not next_clicked:
                            logger.error(f"Could not find next button to navigate months at step {month_step + 1}")
                            self.take_screenshot("next_button_not_found")
                            return False
                
                # Now select the target day with Angular Bootstrap ngb-datepicker selectors
                day_selectors = [
                    # Angular Bootstrap ngb-datepicker specific selectors
                    f"//div[@ngbdatepickerdayview and normalize-space(text())='{target_day}']",
                    f"//div[contains(@ngbdatepickerdayview, '') and normalize-space(text())='{target_day}']",
                    f"//div[@ngbdatepickerdayview='' and text()='{target_day}']",
                    # More generic Angular Bootstrap selectors
                    f"//div[contains(@class, 'btn-light') and normalize-space(text())='{target_day}']",
                    f"//div[contains(@class, 'btn') and normalize-space(text())='{target_day}']",
                    # Fallback to traditional selectors
                    f"//td[contains(@class, 'day') and not(contains(@class, 'old')) and not(contains(@class, 'new')) and not(contains(@class, 'disabled')) and normalize-space(text())='{target_day}']",
                    f"//button[normalize-space(text())='{target_day}' and contains(@class, 'day')]"
                ]
                
                day_element = None
                selector_used = None
                
                for selector in day_selectors:
                    try:
                        day_element = wait.until(EC.element_to_be_clickable((By.XPATH, selector)))
                        selector_used = selector
                        logger.info(f"Found day element for {target_day} using selector: {selector}")
                        break
                    except:
                        continue
                
                # If XPath selectors failed, try CSS selector with Angular Bootstrap filtering
                if not day_element:
                    try:
                        # Get all Angular Bootstrap day elements
                        day_elements = self.driver.find_elements(By.CSS_SELECTOR, "div[ngbdatepickerdayview], div.btn-light, div[class*='btn']")
                        logger.info(f"Found {len(day_elements)} potential Angular Bootstrap day elements")
                        
                        for element in day_elements:
                            element_text = element.text.strip()
                            element_classes = element.get_attribute('class') or ''
                            ngb_attr = element.get_attribute('ngbdatepickerdayview')
                            
                            logger.debug(f"Checking element: text='{element_text}', classes='{element_classes}', ngb='{ngb_attr}'")
                            
                            # Check if this is our target day
                            if element_text == str(target_day):
                                # Make sure it's not disabled (Angular Bootstrap might use different disabled indicators)
                                if ('disabled' not in element_classes.lower() and 
                                    'muted' not in element_classes.lower() and
                                    'text-muted' not in element_classes.lower() and
                                    element.is_enabled() and
                                    element.is_displayed()):
                                    day_element = element
                                    selector_used = "Angular Bootstrap CSS filtering"
                                    logger.info(f"Found day element for {target_day} using Angular Bootstrap CSS selector with filtering")
                                    break
                                else:
                                    logger.debug(f"Skipping day {target_day} - appears disabled or not available. Classes: {element_classes}")
                                    
                    except Exception as e:
                        logger.warning(f"Angular Bootstrap CSS filtering approach failed: {e}")
                
                if not day_element:
                    logger.error(f"Could not find clickable day element for {target_day}")
                    self.take_screenshot("day_element_not_found")
                    
                    # Debug: Log all available day elements
                    try:
                        all_days = self.driver.find_elements(By.CSS_SELECTOR, "td, button")
                        logger.debug(f"All potential clickable elements:")
                        for day in all_days[:20]:  # Limit to first 20 for readability
                            classes = day.get_attribute('class') or ''
                            text = day.text.strip()
                            tag = day.tag_name
                            if text and ('day' in classes.lower() or text.isdigit()):
                                logger.debug(f"  Element: '{text}', Tag: {tag}, Classes: '{classes}'")
                    except Exception as e:
                        logger.debug(f"Could not retrieve elements for debugging: {e}")
                    
                    return False
                
                # Click the day element with multiple attempts
                click_attempts = [
                    lambda: day_element.click(),
                    lambda: self.driver.execute_script("arguments[0].click();", day_element),
                    lambda: self.driver.execute_script("arguments[0].dispatchEvent(new MouseEvent('click', {bubbles: true}));", day_element)
                ]
                
                clicked_successfully = False
                for i, click_method in enumerate(click_attempts):
                    try:
                        # Scroll to the day element first
                        self.driver.execute_script("arguments[0].scrollIntoView({behavior: 'instant', block: 'center'});", day_element)
                        time.sleep(0.1)
                        
                        # Attempt click
                        click_method()
                        logger.info(f"Successfully clicked target day: {target_day} (method {i+1})")
                        time.sleep(0.5)  # Wait for the date table to close
                        clicked_successfully = True
                        break
                        
                    except Exception as e:
                        logger.warning(f"Click method {i+1} failed: {e}")
                        if i < len(click_attempts) - 1:
                            time.sleep(0.2)  # Brief pause before next attempt
                
                if not clicked_successfully:
                    logger.error("All click methods failed")
                    self.take_screenshot("day_click_failed")
                    return False
                
                # Verify the input field updated correctly with multiple possible input selectors
                input_selectors = [
                    "//input[@id='visitDate']",
                    "//input[contains(@name, 'visit')]",
                    "//input[contains(@name, 'date')]",
                    "//input[@type='date']",
                    "//input[contains(@class, 'date')]"
                ]
                
                verification_successful = False
                for input_selector in input_selectors:
                    try:
                        date_input = wait.until(EC.presence_of_element_located((By.XPATH, input_selector)))
                        selected_date = date_input.get_attribute('value')
                        expected_date = self.target_date.strftime('%Y-%m-%d')
                        
                        logger.info(f"Selected date in input field: '{selected_date}'")
                        logger.info(f"Expected date: '{expected_date}'")
                        
                        if selected_date == expected_date:
                            logger.info("✅ Visit date selected successfully!")
                            verification_successful = True
                            break
                        elif selected_date:
                            # Try different date formats
                            try:
                                # Parse the selected date and compare
                                parsed_selected = datetime.strptime(selected_date, '%Y-%m-%d').date()
                                expected_date_obj = self.target_date.date()
                                
                                if parsed_selected == expected_date_obj:
                                    logger.info("✅ Visit date selected successfully (date objects match)!")
                                    verification_successful = True
                                    break
                            except:
                                pass
                        
                    except Exception as e:
                        logger.debug(f"Input selector {input_selector} failed: {e}")
                        continue
                
                if not verification_successful:
                    logger.warning("Could not verify date selection through input field, but click appeared successful")
                    logger.warning("Continuing with the assumption that date selection worked...")
                    self.take_screenshot("date_verification_warning")
                    return True  # Continue anyway as click seemed to work
                
                return True
                
            except Exception as e:
                logger.error(f"Failed to select visit date: {e}")
                self.take_screenshot("date_selection_failed")
                return False
        
        return self.simulate_step("Select Visit Date", _select_date)
    
    def select_pass_type(self):
        """Select pass type based on configuration (index or text)"""
        def _select_pass():
            try:
                # Get configuration settings
                pass_type_index = self.config.get('settings', {}).get('pass_type_index', 0)
                pass_type_text = self.config.get('settings', {}).get('pass_type_text', '')
                
                if pass_type_text:
                    logger.info(f"Looking for pass type containing: '{pass_type_text}'")
                else:
                    logger.info(f"Selecting pass type at index: {pass_type_index}")
                
                wait_timeout = self.config.get('settings', {}).get('wait_timeout', 10)
                wait = WebDriverWait(self.driver, wait_timeout)
                
                # Target the pass type dropdown
                pass_selector = "select[name*='pass'], select[name*='type'], select[id*='pass'], select[id*='type'], .pass-type select"
                pass_element = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, pass_selector)))
                
                if pass_element.tag_name == 'select':
                    select = Select(pass_element)
                    options = select.options
                    valid_options = [opt for opt in options[1:] if opt.get_attribute('value') and opt.get_attribute('value') != '']
                    
                    # Log available options for debugging
                    logger.info(f"Found {len(valid_options)} pass type options:")
                    for i, opt in enumerate(valid_options):
                        logger.info(f"  Option {i}: {opt.text}")
                    
                    selected_option = None
                    
                    # Priority 1: Select by text if specified
                    if pass_type_text:
                        for option in valid_options:
                            if pass_type_text.lower() in option.text.lower():
                                selected_option = option
                                logger.info(f"Found matching pass type by text: {option.text}")
                                break
                        
                        if not selected_option:
                            logger.warning(f"Could not find pass type containing '{pass_type_text}'. Falling back to index selection.")
                    
                    # Priority 2: Select by index
                    if not selected_option:
                        if len(valid_options) > pass_type_index:
                            selected_option = valid_options[pass_type_index]
                            logger.info(f"Selected pass type by index {pass_type_index}: {selected_option.text}")
                        else:
                            logger.error(f"Pass type index {pass_type_index} not available. Found {len(valid_options)} options.")
                            return False
                    
                    # Make the selection
                    if selected_option:
                        select.select_by_value(selected_option.get_attribute('value'))
                        logger.info(f"✅ Selected pass type: {selected_option.text}")
                        time.sleep(0.5)
                        return True
                    else:
                        logger.error("No valid pass type option could be selected")
                        return False
                        
                else:
                    logger.error("Could not find pass type dropdown or unsupported element type")
                    return False
                    
            except Exception as e:
                logger.error(f"Failed to select pass type: {e}")
                return False
        
        return self.simulate_step("Select Pass Type", _select_pass)
    
    def select_visit_time(self):
        """Select the visit time slot (e.g., ALL DAY, AM, PM) from radio buttons."""
        def _select_time():
            try:
                # Define allowed visit time options
                valid_time_slots = ['ALL DAY', 'AM', 'PM']
                
                # Get the desired time slot from the config
                time_slot_value = self.config.get('settings', {}).get('visit_time', '').upper()
                
                # Validate the time slot
                if not time_slot_value or time_slot_value not in valid_time_slots:
                    logger.error(f"Invalid or missing visit time in config: '{time_slot_value}'. Valid options are: {valid_time_slots}")
                    self.take_screenshot("invalid_visit_time")
                    return False
                    
                logger.info(f"Selecting visit time slot: {time_slot_value}")
                
                wait_timeout = self.config.get('settings', {}).get('wait_timeout', 15)
                wait = WebDriverWait(self.driver, wait_timeout)

                # Map config value to HTML value (ALL DAY -> DAY)
                selector_value = 'DAY' if time_slot_value == 'ALL DAY' else time_slot_value
                
                # Selector for the parent <div> containing the radio button with the correct value
                div_selector = f"div.card-header.card-header-enabled:has(input[type='radio'][name='visitTime'][value='{selector_value}'])"
                radio_selector = f"input[type='radio'][name='visitTime'][value='{selector_value}']"

                try:
                    # First, try clicking the parent <div>
                    header_div = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, div_selector)))
                    
                    # Scroll to the element to ensure it's in view
                    self.driver.execute_script("arguments[0].scrollIntoView(true);", header_div)
                    time.sleep(0.5)  # Brief pause after scroll
                    
                    # Try clicking via JavaScript to bypass Angular issues
                    self.driver.execute_script("arguments[0].click();", header_div)
                    logger.info(f"✅ Successfully clicked header div for time slot: {time_slot_value}")
                    return True

                except TimeoutException:
                    logger.warning(f"Could not find or click the header div for '{time_slot_value}'. Falling back to radio button.")
                    
                    # Fallback: Try clicking the radio button directly
                    try:
                        time_radio = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, radio_selector)))
                        self.driver.execute_script("arguments[0].scrollIntoView(true);", time_radio)
                        time.sleep(0.5)
                        self.driver.execute_script("arguments[0].click();", time_radio)
                        logger.info(f"✅ Successfully clicked radio button for time slot: {time_slot_value}")
                        return True

                    except TimeoutException:
                        logger.error(f"Could not find or click the radio button for the '{time_slot_value}' time slot.")
                        self.take_screenshot("visit_time_not_found")
                        return False

            except Exception as e:
                logger.error(f"Failed to select visit time: {e}")
                self.take_screenshot("visit_time_failed")
                return False
        
        return self.simulate_step("Select Visit Time", _select_time)
    
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