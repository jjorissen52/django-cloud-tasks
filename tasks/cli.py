import functools
import os
import sys
import json
import django

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

django.setup()

import tasks.models as models
from django.contrib.auth import get_user_model
from tasks.openid import create_token, decode_token

User = get_user_model()


def output(func):
    @functools.wraps(func)
    def inner(*args, **kwargs):
        result = func(*args, **kwargs)
        if isinstance(result, dict):
            sys.stdout.write(f'{json.dumps(result, indent=2)}\n')
            sys.stdout.flush()
        elif isinstance(result, str):
            sys.stdout.write(f'{result}\n')
            sys.stdout.flush()
        else:
            return result
    return inner


@output
def list_steps(offset=0, limit=100):
    return list(models.Step.objects
                .values("name", "action", "id", "payload", "success_pattern", "task_id", "task__name")[offset:limit])


@output
def execute_step(name: str):
    return models.Step.objects.get(name=name).execute()


@output
def list_tasks(offset=0, limit=100):
    return list(models.Task.objects.values('name')[offset:limit])


@output
def execute_task(name: str):
    return models.Task.objects.get(name=name).execute()


@output
def list_clocks(offset=0, limit=100):
    return list(models.Clock.objects.values(
        'name',
        'cron',
        'management',
        'status'
    )[offset:limit])


@output
def tick_clock(name: str):
    return models.Clock.objects.get(name=name).tick()


@output
def start_clock(name: str):
    _, message = models.Clock.objects.get(name=name).start_clock()
    return message


@output
def pause_clock(name: str):
    _, message = models.Clock.objects.get(name=name).pause_clock()
    return message


@output
def delete_clock(name: str):
    _, message = models.Clock.objects.get(name=name).delete_clock()
    return message


@output
def sync_clock(name: str):
    _, message = models.Clock.objects.get(name=name).sync_clock()
    return message


@output
def list_schedules(offset=0, limit=100):
    return list(models.TaskSchedule.objects.values(
        "id",
        "name",
        "enabled",
        "clock__name",
        "clock_id",
        "clock__cron",
        "task__name",
        "task_id"
    )[offset:limit])


@output
def list_executions(offset=0, limit=100):
    return list(models.TaskExecution.objects.values(
        "id",
        "results",
        "status",
        "task__name",
        "task_id",
    )[offset:limit])


@output
def register_service_account(email: str):
    try:
        User.objects.get(email__iexact=email)
        return f'User for service account {email} already exists.'
    except User.DoesNotExist:
        User.objects.create(email=email, username=email)
        return f'Created User for service account {email}.'


@output
def delete_service_account(email: str):
    try:
        User.objects.filter(email__iexact=email).delete()
        return f'Deleted User for service account {email}'
    except User.DoesNotExist:
       return f'User for service account {email} does not exist.'


if __name__ == '__main__':
    import fire

    fire.Fire({
        'tasks': {
            'list': list_tasks,
            'exec': execute_task,
            'steps': {
                'list': list_steps,
                'exec': execute_step,
            },
            'executions': {
                'list': list_executions,
            },
        },
        'clocks': {
            'list': list_clocks,
            'tick': tick_clock,
            'start': start_clock,
            'pause': pause_clock,
            'delete': delete_clock,
            'sync': sync_clock,
            'schedules': {
                'list': list_schedules,
            }
        },
        'auth': {
            'open_id': {
                'token': {
                    'create': output(create_token),
                    'decode': output(decode_token),
                }
            },
            'service_account': {
                'register': register_service_account,
                'delete': delete_service_account,
            },
        }
    })
