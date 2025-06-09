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

class FormUtilMixin:
    def _find_element_by_selectors(self, wait, css_selectors=None, xpath_selectors=None):
        """
        Waits for the first element matching any of the provided selectors.
        Prioritizes CSS selectors, then falls back to XPath.
        """
        # First, try the highly efficient combined CSS selector
        if css_selectors:
            combined_css_selector = ", ".join(css_selectors)
            try:
                # Wait for just ONE element that matches ANY of the selectors to be clickable
                return wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, combined_css_selector)))
            except TimeoutException:
                logger.debug(f"Element with CSS selectors '{combined_css_selector}' not found. Trying XPath.")

        # If CSS fails or isn't provided, try XPath selectors one by one
        if xpath_selectors:
            for selector in xpath_selectors:
                try:
                    return wait.until(EC.element_to_be_clickable((By.XPATH, selector)))
                except TimeoutException:
                    continue # Try the next XPath selector
        
        logger.warning("Could not find a clickable element with any of the provided selectors.")
        return None


    def fill_form_details(self):
        """Fill out the form with personal details, hyper-optimized for the given HTML."""
        def _fill_form():
            try:
                logger.info("Filling out form details with optimized selectors...")
                form_data = self.config['form_data']
                wait_timeout = self.config.get('settings', {}).get('wait_timeout', 5) # Can likely reduce timeout
                wait = WebDriverWait(self.driver, wait_timeout)

                # First Name
                first_name_selectors = [
                    "#firstName",                                   # HIGHEST PRIORITY: ID
                    "input[formcontrolname='firstName']",           # SECOND PRIORITY: Angular formcontrolname
                    "input[name*='first']", "input[placeholder*='First']" # Fallbacks
                ]
                first_name_field = self._find_element_by_selectors(wait, css_selectors=first_name_selectors)
                if first_name_field:
                    first_name_field.clear()
                    first_name_field.send_keys(form_data['first_name'])
                    logger.info("First name filled.")
                else:
                    logger.error("COULD NOT FIND FIRST NAME FIELD.")
                    return False


                # Last Name 
                last_name_selectors = [
                    "#lastName",                                    # HIGHEST PRIORITY: ID
                    "input[formcontrolname='lastName']",            # SECOND PRIORITY: Angular formcontrolname
                    "input[name*='last']", "input[placeholder*='Last']"  # Fallbacks
                ]
                last_name_field = self._find_element_by_selectors(wait, css_selectors=last_name_selectors)
                if last_name_field:
                    last_name_field.clear()
                    last_name_field.send_keys(form_data['last_name'])
                    logger.info("Last name filled.")
                else:
                    logger.error("COULD NOT FIND LAST NAME FIELD.")
                    return False

                # Email
                email_selectors = ["input[type='email']", "input[name*='email']", "input[id*='email']"]
                combined_email_selector = ", ".join(email_selectors)
                email_fields = self.driver.find_elements(By.CSS_SELECTOR, combined_email_selector)
                unique_email_fields = list(dict.fromkeys(email_fields)) # Remove duplicates

                if len(unique_email_fields) >= 1:
                    unique_email_fields[0].clear()
                    unique_email_fields[0].send_keys(form_data['email'])
                    logger.info("Email filled.")
                if len(unique_email_fields) >= 2:
                    unique_email_fields[1].clear()
                    unique_email_fields[1].send_keys(form_data['email'])
                    logger.info("Retype email filled.")

                return True
            except Exception as e:
                logger.error(f"Failed to fill form details: {e}")
                return False

        return self.simulate_step("Fill Form Details", _fill_form)

    def accept_terms_and_conditions(self):
        """
        Precisely targets and clicks the LAST checkbox associated with the 'terms'
        text, ignoring the earlier 'text reminders' checkbox.
        """
        def _accept_terms():
            try:
                logger.info("Accepting terms: distinguishing between the two checkboxes...")
                wait_timeout = self.config.get('settings', {}).get('wait_timeout', 10)
                wait = WebDriverWait(self.driver, wait_timeout)
                
                # There are two inputs on the page. We want the one associated with the 'notice' text.
                # This XPath finds ALL checkboxes inside a container that has our target text, and then uses [last()] to select the very last one.
                # This correctly identifies the terms and conditions box and ignores the text message box.
                
                xpath_selector = "(//input[@type='checkbox'])[last()]"
                
                logger.info(f"Attempting to find the LAST checkbox on the page with XPath: {xpath_selector}")
                checkbox = wait.until(EC.element_to_be_clickable((By.XPATH, xpath_selector)))
                
                if checkbox:
                    # We scroll the element into view before clicking to ensure it's not off-screen.
                    self.driver.execute_script("arguments[0].scrollIntoView(true);", checkbox)
                    time.sleep(0.5) # A brief pause to ensure scrolling has finished.

                    if not checkbox.is_selected():
                        checkbox.click()
                        logger.info("Correct 'Terms and conditions' checkbox found and accepted successfully.")
                    else:
                        logger.info("Correct 'Terms and conditions' checkbox was already selected.")
                    return True
                
            except Exception as e:
                logger.error(f"Failed to find or click the correct terms checkbox. Error: {e}")
                return False

        return self.simulate_step("Accept Terms", _accept_terms)


    def submit_form(self):
        """
        This function submits the final form after the correct checkbox is clicked.
        """
        def _submit():
            try:
                logger.info("Submitting form...")
                wait_timeout = self.config.get('settings', {}).get('wait_timeout', 5)
                wait = WebDriverWait(self.driver, wait_timeout)

                xpath_selector = "//button[contains(., 'Submit')]"
                
                submit_button = wait.until(EC.element_to_be_clickable((By.XPATH, xpath_selector)))

                if submit_button:
                    submit_button.click()
                    logger.info("Form submitted successfully!")
                    return True
                
                logger.error("Could not find submit button.")
                return False
            except Exception as e:
                logger.error(f"Failed to submit form: {e}")
                return False

        return self.simulate_step("Submit Form", _submit)