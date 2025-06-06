# Configuration for BC Parks Ticket Bot
# TEST MODE SETTINGS
TEST_MODE = True  # Set to False for production
SKIP_TIME_WAIT = True  # Skip waiting for 7 AM when testing
HEADLESS_MODE = False  # Set to True to hide browser during testing

# Website Configuration - Available Parks
PARKS = {
    'golden_ears': {
        'name': 'Golden Ears Provincial Park',
        'search_text': 'Golden Ears'
    },
    'joffre_lakes': {
        'name': 'Joffre Lakes Provincial Park', 
        'search_text': 'Joffre Lakes'
    }
}

# Choose which park you want to book
SELECTED_PARK = 'golden_ears'  # Change this to 'golden_ears' or 'joffre_lakes'

# Always start at the main BC Parks day use reservation page
TICKET_URL = 'https://reserve.bcparks.ca/dayuse/'

# Personal Information
FORM_DATA = {
    'first_name': 'John',
    'last_name': 'Doe',
    'email': 'JohnDoe828@gmail.com'
}

# Bot Settings
SETTINGS = {
    'wait_timeout': 5 if TEST_MODE else 3,  # Shorter timeout for testing
    'vancouver_release_time': '07:00',
    'days_ahead': 2,
    'browser_headless': HEADLESS_MODE,
    'keep_browser_open_seconds': 30 if TEST_MODE else 10,  # Keep browser open longer for testing
    'test_mode': TEST_MODE,
    'skip_time_wait': SKIP_TIME_WAIT,
    
    # PASS TYPE SELECTION - Choose one of these options:
    
    # Option 1: Select by index (0 = first option, 1 = second option, 2 = third option, etc.)
    'pass_type_index': 1,  # Change this to select different option by position
    
    # VISIT TIME SELECTION (AM/PM) - This was added for the new step
    'visit_time': 'AM',  # Set to 'AM' or 'PM' based on your preference
}

# Test-specific settings
TEST_SETTINGS = {
    'simulate_steps': False,  # Set to True to simulate without actually clicking
    'verbose_logging': True,  # More detailed logging for testing
    'step_by_step': False,     # Pause between steps for manual verification
    'screenshot_steps': True # Take screenshots at each step
}

# Complete config dictionary
config = {
    'ticket_url': TICKET_URL,
    'form_data': FORM_DATA,
    'settings': SETTINGS,
    'test_settings': TEST_SETTINGS if TEST_MODE else {},
    'selected_park': SELECTED_PARK,
    'parks': PARKS
}