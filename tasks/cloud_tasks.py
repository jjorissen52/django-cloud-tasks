"""
Some wrapper methods around Google Cloud Tasks
ref: https://googleapis.dev/python/cloudtasks/latest/gapic/v2/api.html
"""
import functools
import re
import json
import datetime
from typing import Optional, Union, List

from google.cloud import tasks_v2
from google.cloud.tasks_v2.proto.task_pb2 import Task
from google.protobuf import timestamp_pb2

from tasks import utils
from tasks.conf import PROJECT_ID, REGION, SERVICE_ACCOUNT, QUEUE


def validate_args(func):
    @functools.wraps(func)
    def inner(*args, **kwargs):
        params = utils.named_method_params(func, args, kwargs)
        if params['queue'] is None and QUEUE is None:
            raise ValueError(f'Function `{func.__name__}` '
                             f'requires `queue`. `queue` can either be passed to `{func.__name__}` '
                             f'or it can be set in your project settings with TASKS_QUEUE')
        if 'name' in params:
            params['name'] = str(params['name'])
        return func(**params)
    return inner


@validate_args
def list_tasks(queue: Optional[str] = QUEUE) -> List[Task]:
    client = tasks_v2.CloudTasksClient()
    full_queue_name = client.queue_path(PROJECT_ID, REGION, queue)
    attributes = ['url', 'http_method', 'headers', 'oidc_token']

    return [{'name': task.name, **{attr: getattr(task.http_request, attr) for attr in attributes}}
            for task in client.list_tasks(full_queue_name)]


@validate_args
def create_task(
        url: str,
        name: Optional[str] = None,
        payload: Optional[Union[str, dict, list, tuple]] = None,
        queue: Optional[str] = QUEUE,
        service_account: str = SERVICE_ACCOUNT,
        delay: int = 0
) -> Task:
    client = tasks_v2.CloudTasksClient()
    full_queue_name = client.queue_path(PROJECT_ID, REGION, queue)
    task = {
        'http_request': {  # Specify the type of request.
            'http_method': 'POST',
            'url': url,  # The full url path that the task will be sent to.
            'oidc_token': {
                'service_account_email': service_account,
            }

        }
    }
    if isinstance(payload, str):
        task['http_request']['body'] = payload
    elif isinstance(payload, (dict, list, tuple)):
        task['http_request']['body'] = json.dumps(payload)

    scheduled_time = datetime.datetime.utcnow() + datetime.timedelta(seconds=delay)
    pb2_timestamp = timestamp_pb2.Timestamp()
    pb2_timestamp.FromDatetime(scheduled_time)

    task['schedule_time'] = pb2_timestamp
    if name:
        cleaned_name = re.sub(r'[^\w-]', '-', name)
        task['name'] = client.task_path(PROJECT_ID, REGION, queue, f'{cleaned_name}-{int(scheduled_time.timestamp())}')
    return client.create_task(full_queue_name, task)


@validate_args
def delete_task(name: str, queue: Optional[str] = QUEUE):
    client = tasks_v2.CloudTasksClient()
    full_queue_name = client.queue_path(PROJECT_ID, REGION, queue)
    if name.startswith(f'{full_queue_name}/tasks/'):
        name = name.split(f'{full_queue_name}/tasks/')[-1]
    full_task_name = client.task_path(PROJECT_ID, REGION, queue, name)
    return client.delete_task(full_task_name)
