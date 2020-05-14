from django.contrib.postgres.fields import JSONField, ArrayField
from django.db import models, transaction

from . import cloud_scheduler
from . conf import ROOT_URL

MAX_NAME_LENGTH = 100


class Clock(models.Model):
    """
    Create an external time-keeper. Defaults to using Cloud Scheduler.
    Make sure the API is enabled at that the App Engine service account
    has Cloud Scheduler Admin. If you do not want App Engine to have
    this permission, you must select "Manual" instead.
    """
    _management_choices = {
        'gcp': 'Cloud Scheduler',
        'manual': 'Manual',
    }
    MANAGEMENT_CHOICES = (
        (key, value) for key, value in _management_choices.items()
    )

    name = models.CharField(max_length=MAX_NAME_LENGTH, help_text="Name of clock. Use something descriptive like "
                                                                  "\"Every Day\"")
    description = models.TextField(help_text="Description of what the Clock is for. Will be shown in Cloud Console.")
    cron = models.CharField(max_length=30, help_text="Cron-style schedule, (test with https://crontab.guru/)")
    enabled = models.BooleanField(null=True, default=True, help_text="Whether this clock is active. Does nothing if "
                                                                     "management is manual.")
    management = models.CharField(max_length=7, default='auto', choices=MANAGEMENT_CHOICES,
                                  help_text='Whether to automatically or manually schedule in Cloud Scheduler')

    def clean(self):
        # TODO: Implement
        return self

    @transaction.atomic
    def save(self, force_insert=False, force_update=False, using=None,
             update_fields=None):
        self.clean()
        should_create = self.pk is None
        super().save(force_insert, force_update, using, update_fields)
        if self.management == 'manual':
            return self
        # create/update new Cloud Scheduler job corresponding to Clock
        if should_create:
            job = cloud_scheduler.Job(name=self.name,
                                      description=self.description,
                                      schedule=self.cron,
                                      time_zone='America/Chicago',
                                      http_target=f'{ROOT_URL}/tasks/api/clocks/{self.pk}/tick/')
            cloud_scheduler.create_job(job)
        return self

    def __str__(self):
        return f'{self.name} ({self._management_choices[self.management]})'


class TaskExecution(models.Model):
    """
    Tasks that have been executed
    """
    _status_choices = {
        'started': 'Started',
        'success': 'Success',
        'failure': 'Failure',
    }
    STATUS_CHOICES = (
        (key, value) for key, value in _status_choices.items()
    )

    task = models.ForeignKey('tasks.Task', on_delete=models.CASCADE)
    status = models.CharField(max_length=7, default='started', choices=STATUS_CHOICES)

    results = JSONField(null=True, blank=True)

    def __str__(self):
        return f'{self.task} ({self._status_choices[self.status]})'


class TaskSchedule(models.Model):
    """
    Execution Schedule for a `Task`. Each time the `Clock` ticks, a `TaskExecution` will be created.
    """

    name = models.CharField(max_length=MAX_NAME_LENGTH, unique=True, help_text="Name of Task Schedule")
    task = models.ForeignKey('tasks.Task', on_delete=models.PROTECT)

    clock = models.ForeignKey(Clock, null=True, on_delete=models.SET_NULL)

    enabled = models.BooleanField(default=True, help_text="Whether or not task schedule is enabled.")

    def clock_active(self):
        if self.clock is None:
            return False
        return self.clock.enabled

    def active(self):
        return self.enabled and self.clock_active()

    def __str__(self):
        return f'{self.name}: {self.task}'


class Task(models.Model):
    """
    A series of `Steps` to be executed at a set time.
    """
    name = models.CharField(max_length=MAX_NAME_LENGTH, unique=True, help_text="Name of Task")

    def __str__(self):
        return self.name


class Step(models.Model):
    """
    A single step to be performed during execution of a `Task`. Currently,
    making requests to URLs authenticated with Google's OpenID as the App Engine service
    account are the only supported actions.
    """
    task = models.ForeignKey(Task, on_delete=models.PROTECT, )
    name = models.CharField(max_length=MAX_NAME_LENGTH, help_text="Name of Step")
    action = models.URLField(help_text="URL to place request")
    payload = JSONField(null=True, blank=True, help_text="JSON Payload of request")

    success_pattern = models.CharField(null=True, blank=True, max_length=255,
                                       help_text="Regex corresponding to successful execution")

    class Meta:
        unique_together = ("name", "task", )

    def __str__(self):
        return f'{self.name} (of {self.task})'
