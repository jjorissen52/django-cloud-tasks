# model invariants
MAX_NAME_LENGTH = 100
# status constants
RUNNING, PAUSED, UNKNOWN, BROKEN, PENDING, STARTED, SUCCESS, FAILURE = \
    'running', 'paused', 'unknown', 'broken', 'pending', 'started', 'success', 'failure'
# action constants
START, PAUSE, FIX, SYNC = 'start', 'pause', 'fix', 'sync'
# management constants
GCP, MANUAL = 'gcp', 'manual'
