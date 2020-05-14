from django.conf import settings

REGION = settings.TASKS_REGION
PROJECT_ID = settings.TASKS_PROJECT_ID
SERVICE = settings.TASKS_SERVICE
ROOT_URL = getattr(settings, 'TASKS_ROOT_URL', None)

if ROOT_URL is None:
    if SERVICE == 'default':
        ROOT_URL = f'https://{PROJECT_ID}.appspot.com'
    else:
        ROOT_URL = f'https://{SERVICE}-dot-{PROJECT_ID}.appspot.com'
