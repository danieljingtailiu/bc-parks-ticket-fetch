TEST_MODE = False        # <--- CHANGE THIS to False for prod
SKIP_TIME_WAIT = False     # <--- CHANGE THIS to False to test the launch sequence


PARKS = {
    'golden_ears': {
        'name': 'Golden Ears Provincial Park',
        'search_text': 'Golden Ears'
    },
    'joffre_lakes': {
        'name': 'Joffre Lakes Provincial Park', 
        'search_text': 'Joffre Lakes'
    },
    'garibaldi': {
        'name': 'Garibaldi Provincial Park',
        'search_text': 'garibaldi'
    }
}

SELECTED_PARK = 'golden_ears' # choose the parks using the search text i.e. joffre_lakes
TICKET_URL = 'https://reserve.bcparks.ca/dayuse/'

# Personal Information
FORM_DATA = {
    'first_name': 'John',
    'last_name': 'Doe',
    'email': 'johnedoe828@gmail.com'
}

# Bot Settings
SETTINGS = {
    'wait_timeout': 3,  # Use the production timeout
    'cf-clearance_path':r"xxxxx/xxxxx/xxxxx/xxx", # <-- your cf-clearance folder path, the folder should be empty and in the python folder
    # Use 24-hour format. E.g., if it's 2:10 PM, set this to '14:13'.
    'vancouver_release_time': '07:00', # <--- SET THIS TO A FUTURE TIME
    'days_ahead': 0,
    'keep_browser_open_seconds': 30, # Keep open longer to see the result
    'test_mode': TEST_MODE,
    'skip_time_wait': SKIP_TIME_WAIT,
    # python indexing, 0 euqates to the first pass type option
    'pass_type_index': 1,
    'visit_time': 'AM', # <-- 3 options, AM, PM, ALL DAY
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