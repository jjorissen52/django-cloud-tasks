#!/usr/bin/env python
if __name__ == '__main__':
    import os
    import sys
    from django import setup

    sys.path.insert(0, os.path.abspath(os.getcwd()))

    try:
        setup()
    except ModuleNotFoundError as e:
        raise ModuleNotFoundError(
            f"Your django project settings could not be imported. The indicated settings module is "
            f"{os.environ['DJANGO_SETTINGS_MODULE']}, and you executed cloud-tasks from the directory "
            f"{os.path.abspath(os.getcwd())}. Please make sure that the relative path from your "
            f"current working directory as indicated by DJANGO_SETTINGS_MODULE is accurate.")


import subprocess

from django.db.models import Q
from django.contrib.auth import get_user_model

import cloud_tasks.models as models
from cloud_tasks import gtasks, conf
from cloud_tasks.utils import hardcode_reverse
from cloud_tasks.openid import create_token, decode_token


User = get_user_model()


class CloudTasks:
    class tasks:
        @staticmethod
        def list(offset=0, limit=100):
            return list(models.Task.objects.values('name')[offset:limit])

        @staticmethod
        def exec(name: str):
            return f'{models.Task.objects.get(name=name).execute()} ' \
                   f'- {hardcode_reverse("admin:cloud_tasks_taskexecution_changelist")}'

        class steps:
            @staticmethod
            def list(offset=0, limit=100, task=None):
                q = Q() if not task else Q(task__name__iexact=task)
                return list(
                    models.Step.objects.filter(q).values(
                        "name", "action", "id",
                        "payload", "success_pattern",
                        "task_id", "task__name"
                    )[offset:limit]
                )

            @staticmethod
            def exec(name: str):
                return f'{models.Step.objects.get(name=name).execute()} ' \
                       f'- {hardcode_reverse("admin:cloud_tasks_taskexecution_changelist")}'

        class executions:
            @staticmethod
            def list(offset=0, limit=100, task=None):
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

        class schedules:
            @staticmethod
            def list(offset=0, limit=100, clock=None, task=None):
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

            @staticmethod
            def exec(name: str):
                return f'{models.TaskSchedule.objects.get(name=name).run()} ' \
                       f'- {hardcode_reverse("admin:cloud_tasks_taskexecution_changelist")}'

    class clocks:
        @staticmethod
        def list(offset=0, limit=100):
            return list(models.Clock.objects.values(
                'name',
                'cron',
                'management',
                'status'
            )[offset:limit])

        @staticmethod
        def tick(name: str):
            return models.Clock.objects.get(name=name).tick()

        @staticmethod
        def start(name: str):
            _, message = models.Clock.objects.get(name=name).start_clock()
            return message

        @staticmethod
        def pause(name: str):
            _, message = models.Clock.objects.get(name=name).pause_clock()
            return message

        @staticmethod
        def delete(name: str):
            _, message = models.Clock.objects.get(name=name).delete_clock()
            return message

        @staticmethod
        def sync(name: str):
            _, message = models.Clock.objects.get(name=name).sync_clock()
            return message

        class schedules:
            @staticmethod
            def list(offset=0, limit=100, clock=None, task=None):
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

    class auth:
        class open_id:
            class tokens:
                @staticmethod
                def create(audience):
                    return create_token(audience)

                @staticmethod
                def decode(token, audience=None):
                    return decode_token(token, audience)

            class accounts:
                @staticmethod
                def register(email: str):
                    try:
                        User.objects.get(email__iexact=email)
                        return f'User for service account {email} already exists.'
                    except User.DoesNotExist:
                        User.objects.create(email=email, username=email)
                        return f'Created User for service account {email}.'

                @staticmethod
                def delete(email: str):
                    try:
                        User.objects.filter(email__iexact=email).delete()
                        return f'Deleted User for service account {email}'
                    except User.DoesNotExist:
                        return f'User for service account {email} does not exist.'

    class cloud:
        class account:
            @staticmethod
            def grant_required_roles(email: str):
                cmd_template = "gcloud projects add-iam-policy-binding {PROJECT_ID} " \
                               "--member serviceAccount:{email} --role {role}"
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

        class tasks:
            list = staticmethod(gtasks.list_tasks)
            create = staticmethod(gtasks.create_task)
            delete = staticmethod(gtasks.delete_task)


def main():
    import fire
    fire.Fire(CloudTasks)


if __name__ == '__main__':
    main()
