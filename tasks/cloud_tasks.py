"""
Some wrapper methods around Google Cloud Tasks
ref: https://googleapis.dev/python/cloudtasks/latest/gapic/v2/api.html
"""
import json
import datetime
from typing import Optional, Union, List

from google.cloud import tasks_v2
from google.cloud.tasks_v2.proto.task_pb2 import Task
from google.protobuf import timestamp_pb2

from tasks.conf import PROJECT_ID, REGION, SERVICE_ACCOUNT


def list_tasks(queue: str) -> List[Task]:
    client = tasks_v2.CloudTasksClient()
    full_queue_name = client.queue_path(PROJECT_ID, REGION, queue)
    attributes = ['url', 'http_method', 'headers', 'oidc_token']

    return [{'name': task.name, **{attr: getattr(task.http_request, attr) for attr in attributes}}
            for task in client.list_tasks(full_queue_name)]


def create_task(
        queue: str,
        url: str,
        name: Optional[str] = None,
        payload: Optional[Union[str, dict, list, tuple]] = None,
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
        task['name'] = client.task_path(PROJECT_ID, REGION, queue, f'{name}-{int(scheduled_time.timestamp())}')
        print(task['name'])
    return client.create_task(full_queue_name, task)


def delete_task(queue: str, name: str):
    client = tasks_v2.CloudTasksClient()
    full_queue_name = client.queue_path(PROJECT_ID, REGION, queue)
    if name.startswith(f'{full_queue_name}/tasks/'):
        name = name.split(f'{full_queue_name}/tasks/')[-1]
    full_task_name = client.task_path(PROJECT_ID, REGION, queue, name)
    return client.delete_task(full_task_name)
