import os
import sys
import json
import django

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

django.setup()

import tasks.models as models


def execute_step(name: str):
    return models.Step.objects.get(name=name).execute()


def execute_task(name: str):
    task_execution = models.Task.objects.get(name=name).execute()
    sys.stdout.write(f'{json.dumps(task_execution.results, indent=2)}\n')
    sys.stdout.flush()


if __name__ == '__main__':
    import fire
    fire.Fire({
        'exec': {
            'task': execute_task,
            'step': execute_step
        }
    })
