"""Define various constants."""

BLACKOUT_START = '22:00:00'
BLACKOUT_END = '08:00:00'

HANDLER_DISHWASHER_CLEAN = 'dishwasher_clean'
HANDLER_SWITCH_SLEEP_TIMER = 'switch_sleep_timer_{0}'
HANDLER_SWITCH_VACATION_MODE = 'switch_vacation_mode_{0}'
HANDLER_PLANT_NEEDS_WATER = 'plant_needs_water_{0}'
HANDLER_VACUUM_FULL = 'vacuum_full'
HANDLER_VACUUM_SCHEDULE = 'vacuum_schedule'
HANDLER_VACUUM_STUCK = 'vacuum_stuck'

PEOPLE = {
    'Aaron': {
        'car': 'device_tracker.2010_subaru_legacy',
        'device_tracker': 'device_tracker.aaron_iphone',
        'geocode_sensor': 'sensor.aaron_travel_time',
        'notifiers': ['ios_aaron_bachs_iphone'],
        'presence_manager_input_select': 'input_select.aaron_presence_status',
        'push_device_id': 'xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx'
    },
    'Britt': {
        'device_tracker': 'device_tracker.britt_iphone',
        'geocode_sensor': 'sensor.britt_travel_time',
        'notifiers': ['ios_brittany_bachs_iphone'],
        'presence_manager_input_select': 'input_select.britt_presence_status',
        'push_device_id': 'xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx'
    }
}
