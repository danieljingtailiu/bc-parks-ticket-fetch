TEST_MODE = True        # <--- CHANGE THIS to False for prod
SKIP_TIME_WAIT = False     # <--- CHANGE THIS to False to test the launch sequence


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
SELECTED_PARK = 'golden_ears'
TICKET_URL = 'https://reserve.bcparks.ca/dayuse/'

# Personal Information
FORM_DATA = {
    'first_name': 'John',
    'last_name': 'Doe',
    'email': 'JohnDoe828@gmail.com'
}

# Bot Settings
SETTINGS = {
    'wait_timeout': 3,  # Use the production timeout

    # Use 24-hour format. E.g., if it's 2:10 PM, set this to '14:13'.
    'vancouver_release_time': '16:33', # <--- SET THIS TO A FUTURE TIME
    'days_ahead': 2,
    'keep_browser_open_seconds': 30, # Keep open longer to see the result
    'test_mode': TEST_MODE,
    'skip_time_wait': SKIP_TIME_WAIT,
    'pass_type_index': 0,
    'visit_time': 'ALL DAY',
}

# Test-specific settings will be IGNORED because TEST_MODE is False
TEST_SETTINGS = {
    'simulate_steps': False,
    'verbose_logging': True,
    'step_by_step': False,
    'screenshot_steps': True
}

# Complete config dictionary
config = {
    'ticket_url': TICKET_URL,
    'form_data': FORM_DATA,
    'settings': SETTINGS,
    'test_settings': TEST_SETTINGS if TEST_MODE else {}, # This will correctly be an empty dict
    'selected_park': SELECTED_PARK,
    'parks': PARKS
}