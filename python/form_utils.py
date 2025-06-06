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