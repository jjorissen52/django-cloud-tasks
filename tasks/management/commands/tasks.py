import os
import datetime
import argparse

from django.core.management import BaseCommand

from google.cloud import tasks_v2
from google.protobuf import timestamp_pb2

class Command(BaseCommand):
    project = None
    region = None
    service_account = None
    client = None

    available_subcommands = ['create', 'list']

    project_argname = 'project'
    region_argname = 'region'
    subcommand_argname = 'subcommand'
    queue_argname = 'queue'
    url_argname = 'url'
    service_account_argname = 'email'
    payload_argname = 'payload'
    delay_argname = 'delay'

    @staticmethod
    def _check_subcommand(value):
        if value not in Command.available_subcommands:
            raise argparse.ArgumentError(f"{Command.subcommand_argname} must be one of {Command.available_subcommands}"
                                         f"; got {value}")
        return value

    def add_arguments(self, parser):
        parser.add_argument(Command.subcommand_argname, help=f"One of {Command.available_subcommands}",
                            type=Command._check_subcommand)

        parser.add_argument(f'--{Command.queue_argname}', help="Name of Queue to which task(s) belong.")
        parser.add_argument(f'--{Command.project_argname}', help="(Optional) project_id containing task queue")
        parser.add_argument(f'--{Command.region_argname}', help="(Optional) region where task queue should exist")
        parser.add_argument(f'--{Command.url_argname}', help="Name of target URL of task.")
        parser.add_argument(f'--{Command.service_account_argname}', help="(Optional) email of service account to "
                                                                         "execute task.")
        parser.add_argument(f'--{Command.payload_argname}', help="(Optional) payload of task.")
        parser.add_argument(f'--{Command.delay_argname}', default=10, type=lambda x: int(x),
                            help="(Optional) how long from now before a task executes (in seconds).", )

    def _create(self, full_queue_name, url, payload, service_account, delay):
        task = {
            'http_request': {  # Specify the type of request.
                'http_method': 'POST',
                'url': url,  # The full url path that the task will be sent to.
                'oidc_token': {
                    'service_account_email': service_account if service_account else os.environ['TASK_SERVICE_ACCOUNT']
                }

            }
        }
        if isinstance(payload, str):
            task['http_request']['body'] = payload.encode()
        scheduled_time = datetime.datetime.utcnow() + datetime.timedelta(seconds=delay)
        timestamp = timestamp_pb2.Timestamp()
        timestamp.FromDatetime(scheduled_time)

        task['schedule_time'] = timestamp

        return self.client.create_task(full_queue_name, task)

    def _list(self, full_queue_name):
        tasks = tuple(self.client.list_tasks(full_queue_name))
        if len(tasks) == 0:
            print(f"0 tasks in {full_queue_name}")
        for task in tasks:
            print(task)

    def handle(self, *args, **options):
        subcommand = options.get(Command.subcommand_argname)
        project = options.get(Command.project_argname)
        region = options.get(Command.region_argname)
        if not project:
            project = os.environ['PROJECT_ID']
        if not region:
            region = os.environ['REGION']
        service_account = options.get(Command.service_account_argname)
        url = options.get(Command.url_argname)
        queue = options.get(Command.queue_argname)
        payload = options.get(Command.payload_argname, None)
        delay = options.get(Command.delay_argname, 10)

        self.project = project
        self.region = region
        self.client = tasks_v2.CloudTasksClient()

        full_queue_name = self.client.queue_path(self.project, self.region, queue)

        if subcommand == 'create':
            self._create(full_queue_name, url, payload, service_account, delay)
        elif subcommand == 'list':
            self._list(full_queue_name)
