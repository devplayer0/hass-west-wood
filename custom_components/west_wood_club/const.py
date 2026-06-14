"""Constants for the West Wood Club integration."""

from datetime import timedelta

DOMAIN = 'west_wood_club'

# Shown as the device name; also the prefix the API puts on every club name
# (e.g. 'West Wood Club Dun Laoghaire'), stripped from per-club entity names.
DEVICE_NAME = 'West Wood Club'

# PerfectGym Go backend (West Wood is a white-label tenant).
BASE_URL = 'https://goapi2.perfectgym.com'

# Hardcoded West Wood white-label tenant ID (baked into the app binary). Sent as
# the X-Go-White-Label-ID header. The server doesn't require it, but it matches
# what the app sends. See api.md.
WHITE_LABEL_ID = '7d073db5-0ef8-4d78-89ec-4a8bebaf4cbc'

# Config entry keys.
CONF_TOKEN = 'token'
CONF_CLUBS = 'clubs'

# How often to poll live occupancy.
UPDATE_INTERVAL = timedelta(minutes=5)
