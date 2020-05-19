#!/usr/bin/env python
import os
import sys
import json
from django import setup

import functools
import subprocess

from django.db.models import Q
from django.urls import reverse

sys.path.insert(0, os.path.abspath(os.getcwd()))

try:
    setup()
except ModuleNotFoundError as e:
    raise ModuleNotFoundError(
        f"Your django project settings could not be imported. The indicated settings module is "
        f"{os.environ['DJANGO_SETTINGS_MODULE']}, and you executed cloud-tasks from the directory "
        f"{os.path.abspath(os.getcwd())}. Please make sure that the relative path from your "
        f"current working directory as indicated by DJANGO_SETTINGS_MODULE is accurate.")

from django.contrib.auth import get_user_model

import tasks.models as models
from tasks import cloud_tasks, conf
from tasks.openid import create_token, decode_token

User = get_user_model()


def hardcode_reverse(view_name, args=None, kwargs=None):
    return f'{conf.ROOT_URL}{reverse(view_name, args=args, kwargs=kwargs)}'


def main():
    import fire

    exec_map = {
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
            'schedules': {
                'list': list_schedules,
                'exec': execute_schedule,
            }
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
                    'create': create_token,
                    'decode': decode_token,
                }
            },
            'service_account': {
                'register': register_service_account,
                'delete': delete_service_account,
            },
        },
        'cloud': {
            'service_account': {
                'grant_required_roles': grant_required_roles,
            },
            'tasks': {
                'list': cloud_tasks.list_tasks,
                'create': cloud_tasks.create_task,
                'delete': cloud_tasks.delete_task,
            }
        },
    }
    __apply_output(exec_map)
    fire.Fire(exec_map)


def list_steps(offset=0, limit=100, task=None):
    q = Q() if not task else Q(task__name__iexact=task)
    return list(
        models.Step.objects.filter(q).values(
            "name", "action", "id",
            "payload", "success_pattern",
            "task_id", "task__name"
        )[offset:limit]
    )


def execute_step(name: str):
    return f'{models.Step.objects.get(name=name).execute()} ' \
           f'- {hardcode_reverse("admin:tasks_taskexecution_changelist")}'


def list_tasks(offset=0, limit=100):
    return list(models.Task.objects.values('name')[offset:limit])


def execute_task(name: str):
    return f'{models.Task.objects.get(name=name).execute()} ' \
           f'- {hardcode_reverse("admin:tasks_taskexecution_changelist")}'


def list_clocks(offset=0, limit=100):
    return list(models.Clock.objects.values(
        'name',
        'cron',
        'management',
        'status'
    )[offset:limit])


def tick_clock(name: str):
    return models.Clock.objects.get(name=name).tick()


def start_clock(name: str):
    _, message = models.Clock.objects.get(name=name).start_clock()
    return message


def pause_clock(name: str):
    _, message = models.Clock.objects.get(name=name).pause_clock()
    return message


def delete_clock(name: str):
    _, message = models.Clock.objects.get(name=name).delete_clock()
    return message


def sync_clock(name: str):
    _, message = models.Clock.objects.get(name=name).sync_clock()
    return message


def list_schedules(offset=0, limit=100, clock=None, task=None):
    q = Q()
    if clock:
        q &= Q(clock__name__iexact=clock)
    if task:
        q &= Q(task__name__iexact=task)
    return list(
        models.TaskSchedule.objects.filter(q).values(
            "id",
            "name",
            "enabled",
            "clock__name",
            "clock_id",
            "clock__cron",
            "task__name",
            "task_id"
        )[offset:limit]
    )


def execute_schedule(name: str):
    return f'{models.TaskSchedule.objects.get(name=name).run()} ' \
           f'- {hardcode_reverse("admin:tasks_taskexecution_changelist")}'


def list_executions(offset=0, limit=100, task=None):
    q = Q() if not task else Q(task__name__iexact=task)
    return list(
        models.TaskExecution.objects.filter(q).values(
            "id",
            "results",
            "status",
            "task__name",
            "task_id",
        )[offset:limit]
    )


def register_service_account(email: str):
    try:
        User.objects.get(email__iexact=email)
        return f'User for service account {email} already exists.'
    except User.DoesNotExist:
        User.objects.create(email=email, username=email)
        return f'Created User for service account {email}.'


def delete_service_account(email: str):
    try:
        User.objects.filter(email__iexact=email).delete()
        return f'Deleted User for service account {email}'
    except User.DoesNotExist:
        return f'User for service account {email} does not exist.'


def grant_required_roles(email: str):
    cmd_template = "gcloud projects add-iam-policy-binding {PROJECT_ID} --member serviceAccount:{email} --role {role}"
    roles = [
        'roles/cloudtasks.admin',
        'roles/cloudscheduler.admin',
        'roles/cloudfunctions.invoker',
    ]
    for role in roles:
        cmd = cmd_template.format(PROJECT_ID=conf.PROJECT_ID, email=email, role=role)
        process = subprocess.Popen(cmd.split(), stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        stdout, stderr = process.communicate()
        if stdout:
            sys.stdout.write(f'{stdout.decode()}\n')
        if stderr:
            sys.stderr.write(f'{stderr.decode()}\n')
        sys.stdout.flush()
        sys.stderr.flush()


def __output(func):
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


def __apply_output(current_dict):
    for key, value in current_dict.items():
        if callable(value):
            # works because dicts are mutable
            current_dict[key] = __output(value)
        else:
            __apply_output(value)


if __name__ == '__main__':
    main()
