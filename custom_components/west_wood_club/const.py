"""Constants for the West Wood Club integration."""

from datetime import timedelta

DOMAIN = 'west_wood_club'

# PerfectGym Go backend (West Wood is a white-label tenant).
BASE_URL = 'https://goapi2.perfectgym.com'

# Config entry keys.
CONF_TOKEN = 'token'
CONF_CLUBS = 'clubs'

# How often to poll live occupancy.
UPDATE_INTERVAL = timedelta(minutes=5)
