# Configuration for BC Parks Ticket Bot

# Website Configuration
TICKET_URL = "https://your-ticket-website.com"

# Personal Information
FORM_DATA = {
    'first_name': 'John',
    'last_name': 'Doe',
    'email': 'john.doe@example.com'
}

# Bot Settings
SETTINGS = {
    'wait_timeout': 10,
    'vancouver_release_time': '07:00',
    'days_ahead': 2,
    'browser_headless': False,
    'keep_browser_open_seconds': 10
}

# Browser Options
CHROME_OPTIONS = [
    '--no-sandbox',
    '--disable-dev-shm-usage',
    '--disable-blink-features=AutomationControlled',
    '--disable-extensions',
    '--disable-plugins',
    '--disable-images'
]

# Complete config dictionary (for backward compatibility)
config = {
    'ticket_url': TICKET_URL,
    'form_data': FORM_DATA,
    'settings': SETTINGS
}