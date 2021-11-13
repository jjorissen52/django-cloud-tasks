import sys

import fire

from cloud_tasks.cli import CloudTasks


class Command:
    def __init__(self, *args, **kwargs):
        sys.argv.pop(1)  # remove the "cloud_tasks" arg from sys.argv

    @staticmethod
    def run_from_argv(argv):
        sys.argv = argv
        fire.Fire(CloudTasks)
