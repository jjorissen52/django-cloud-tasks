from typing import Tuple

from django.contrib.postgres.fields import JSONField
from django.db import models

from . import cloud_scheduler
from . conf import ROOT_URL

# model invariants
MAX_NAME_LENGTH = 100
# status constants
RUNNING, PAUSED, UNKNOWN, BROKEN, STARTED, SUCCESS, FAILURE = \
    'enabled', 'disabled', 'unknown', 'broken', 'started', 'success', 'failure'
# action constants
START, PAUSE, FIX = 'start', 'pause', 'fix'
# management constants
GCP, MANUAL = 'gcp', 'manual'


class Clock(models.Model):
    """
    Create an external time-keeper. Defaults to using Cloud Scheduler.
    Make sure the API is enabled at that the App Engine service account
    has Cloud Scheduler Admin. If you do not want App Engine to have
    this permission, you must select "Manual" instead.
    """
    _management_choices = {
        GCP: 'Cloud Scheduler',
        MANUAL: 'Manual',
    }
    MANAGEMENT_CHOICES = (
        (key, value) for key, value in _management_choices.items()
    )
    _status_choices = {
        RUNNING: 'Running',
        PAUSED: 'Paused',
        UNKNOWN: 'Unknown',
        BROKEN: 'Broken',
    }
    _status_info = {
        RUNNING: 'The clock is running.',
        PAUSED: 'The clock has been paused.',
        UNKNOWN: 'Clock status unknown (likely manually managed).',
        BROKEN: 'The could not be creeated.',
    }
    STATUS_CHOICES = (
        (key, value) for key, value in _status_choices.items()
    )

    name = models.CharField(max_length=MAX_NAME_LENGTH, help_text="Name of clock. Use something descriptive like "
                                                                  "\"Every Day\"")
    description = models.TextField(help_text="Description of what the Clock is for. Will be shown in Cloud Console.")
    cron = models.CharField(max_length=30, help_text="Cron-style schedule, (test with https://crontab.guru/)")
    management = models.CharField(max_length=7, default=GCP, choices=MANAGEMENT_CHOICES,
                                  help_text='Whether to automatically or manually control Clock in Cloud Scheduler')
    status = models.CharField(max_length=8, default=RUNNING, choices=STATUS_CHOICES,
                              help_text="Status of the clock. ")

    @property
    def status_info(self):
        return self._status_info[self.status]

    def new_job(self):
        assert self.pk is not None, "Cannot create job without a primary key."
        return cloud_scheduler.Job(name=self.name,
                                   description=self.description,
                                   schedule=self.cron,
                                   time_zone='America/Chicago',
                                   http_target=f'{ROOT_URL}/tasks/api/clocks/{self.pk}/tick/')

    def clean(self):
        if self.management == MANUAL:
            self.status = UNKNOWN
        return self

    def start(self) -> Tuple[bool, str]:
        try:
            job = cloud_scheduler.get_job(self.name)
            job = cloud_scheduler.resume_job(self.name)

        except cloud_scheduler.JobRetrieveError as e:
            error_message = cloud_scheduler.get_error(e)
            if "lacks IAM permission" in error_message:
                return False, f"The GCP service account for the website does not have sufficient " \
                              f"permissions to edit the clock. "
            elif "Job not found" in error_message:
                job = self.new_job()
                try:
                    cloud_scheduler.create_job(job)
                except cloud_scheduler.JobCreationError as e:
                    error_message = cloud_scheduler.get_error(e)
                    self.status = BROKEN
                    self.save()
                    return False, f"Clock {job.name} could not be created: {error_message}"
            else:
                error_message = cloud_scheduler.get_error(e)
                self.status = BROKEN
                self.save()
                return False, f"Encountered unknown error while attempting to create clock " \
                              f"{self.name}: {error_message}"
        except cloud_scheduler.JobUpdateError as e:
            error_message = cloud_scheduler.get_error(e)
            self.status = BROKEN
            self.save()
            return False, f"Could not restart clock {job.name}: {error_message}"

        self.status = RUNNING
        self.save()
        return True, f"Clock {job.name} is running."

    def pause(self):
        try:
            job = cloud_scheduler.get_job(self.name)
        except cloud_scheduler.JobRetrieveError as e:
            error_message = cloud_scheduler.get_error(e)
            if "Job not found" in error_message:
                self.status = BROKEN
                self.save()
                return False, f"Clock {self.name} does not exist in Cloud Scheduler."
            else:
                self.status = BROKEN
                self.save()
                return False, f"Enountered unknown error while attempting to pause clock {self.name}: {error_message}"
        try:
            cloud_scheduler.pause_job(self.name)
        except cloud_scheduler.JobUpdateError as e:
            return False, f"Could not pause Clock {job.name}: {e}"

        self.status = PAUSED
        self.save()
        return True, f'Clock {job.name} paused.'

    def save(self, force_insert=False, force_update=False, using=None,
             update_fields=None):
        self.clean()
        should_start = self.pk is None
        super().save(force_insert, force_update, using, update_fields)
        if self.management == MANUAL:
            return self
        # create/update new Cloud Scheduler job corresponding to Clock
        # if this model instance is just now being created.
        if should_start:
            self.start()
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
