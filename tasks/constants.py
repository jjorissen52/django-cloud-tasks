# model invariants
MAX_NAME_LENGTH = 100
# status constants
RUNNING, PAUSED, UNKNOWN, BROKEN, STARTED, SUCCESS, FAILURE = \
    'running', 'paused', 'unknown', 'broken', 'started', 'success', 'failure'
# action constants
START, PAUSE, FIX = 'start', 'pause', 'fix'
# management constants
GCP, MANUAL = 'gcp', 'manual'