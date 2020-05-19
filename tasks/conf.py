from django.conf import settings

REGION = settings.TASKS_REGION
PROJECT_ID = settings.TASKS_PROJECT_ID
SERVICE = settings.TASKS_SERVICE
QUEUE = getattr(settings, 'TASKS_QUEUE', None)
# default to True if QUEUE is provided
USE_CLOUD_TASKS = getattr(settings, 'TASKS_USE_CLOUD_TASKS', bool(QUEUE))
ROOT_URL = getattr(settings, 'TASKS_ROOT_URL', None)
SERVICE_ACCOUNT = getattr(settings, 'TASKS_SERVICE_ACCOUNT', None)
TIME_ZONE = getattr(settings, 'TIME_ZONE', 'UTC')

if ROOT_URL is None:
    if SERVICE == 'default':
        ROOT_URL = f'https://{PROJECT_ID}.appspot.com'
    else:
        ROOT_URL = f'https://{SERVICE}-dot-{PROJECT_ID}.appspot.com'

if SERVICE_ACCOUNT is None:
    """
    To enable acting as this service account:
    gcloud iam service-accounts add-iam-policy-binding [SERVICE_ACCOUNT]
        --member [MEMBER_EMAIL] --role roles/iam.serviceAccountUser
    """
    SERVICE_ACCOUNT = f'{PROJECT_ID}@appspot.gserviceaccount.com'
