import re
from typing import Tuple

from django.contrib.postgres.fields import JSONField
from django.db import models

from . import cloud_scheduler
from . conf import ROOT_URL

# model invariants
MAX_NAME_LENGTH = 100
# status constants
RUNNING, PAUSED, UNKNOWN, BROKEN, STARTED, SUCCESS, FAILURE = \
    'running', 'paused', 'unknown', 'broken', 'started', 'success', 'failure'
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
        BROKEN: 'The clock is broken.',
    }
    STATUS_CHOICES = (
        (key, value) for key, value in _status_choices.items()
    )

    name = models.CharField(max_length=MAX_NAME_LENGTH, help_text="Name of clock. Use something descriptive like "
                                                                  "\"Every Day\"")
    gcp_name = models.TextField(null=True, help_text="Name of task in GCP with unaccepted characters removed.")
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
        return cloud_scheduler.Job(name=self.gcp_name,
                                   description=self.description,
                                   schedule=self.cron,
                                   time_zone='America/Chicago',
                                   http_target=f'{ROOT_URL}/tasks/api/clocks/{self.pk}/tick/')

    def clean(self):
        if self.management == MANUAL:
            self.status = UNKNOWN
        if not self.gcp_name:
            # make the name friendly for GCP. The value of this field will never change for a given clock.
            self.gcp_name = re.sub(r'[^\w-]', '-', self.name)
        return self

    def start_clock(self) -> Tuple[bool, str]:
        try:
            job = cloud_scheduler.get_job(self.gcp_name)
            job = cloud_scheduler.resume_job(self.gcp_name)

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
                    self.save(skip_cloud_update=True)
                    return False, f"Clock {job.name} could not be created: {error_message}"
            else:
                error_message = cloud_scheduler.get_error(e)
                self.status = BROKEN
                self.save(skip_cloud_update=True)
                return False, f"Encountered unknown error while attempting to create clock " \
                              f"{self.name}: {error_message}"
        except (Exception, BaseException) as e:
            error_message = cloud_scheduler.get_error(e)
            self.status = BROKEN
            self.save(skip_cloud_update=True)
            return False, f"Could not restart clock {self.name}: {error_message}"

        self.status = RUNNING
        self.save(skip_cloud_update=True)
        return True, f"Clock {job.name} is running."

    def pause_clock(self) -> Tuple[bool, str]:
        try:
            job = cloud_scheduler.get_job(self.gcp_name)
        except (Exception, BaseException) as e:
            error_message = cloud_scheduler.get_error(e)
            if "Job not found" in error_message:
                self.status = BROKEN
                self.save(skip_cloud_update=True)
                return False, f"Clock {self.name} (alias for {self.gcp_name}) does not exist in Cloud Scheduler."
            else:
                self.status = BROKEN
                self.save(skip_cloud_update=True)
                return False, f"Enountered unknown error while attempting to pause clock {self.name}: {error_message}"
        try:
            cloud_scheduler.pause_job(self.gcp_name)
        except (Exception, BaseException) as e:
            return False, f"Could not pause Clock {self.name}: {e}"

        self.status = PAUSED
        self.save(skip_cloud_update=True)
        return True, f'Clock {self.name} paused.'

    def update_clock(self) -> Tuple[bool, str]:
        old_job, return_message = None, f"Could not retrieve clock {self.new_job().name} " \
                                        f"for editing. (Missing logic branch)."
        new_job = self.new_job()
        try:
            old_job = cloud_scheduler.get_job(self.gcp_name)
        except (Exception, BaseException) as e:
            error_message = cloud_scheduler.get_error(e)
            return_message = f'Could not retrieve clock {self.name} ' \
                             f'(alias for {self.gcp_name}) for editing: {error_message}'

        if old_job is None:
            return False, return_message

        updated_job = None
        try:
            updated_job = cloud_scheduler.update_job(old_job, new_job)
        except (Exception, BaseException) as e:
            error_message = cloud_scheduler.get_error(e)
            return_message = f'Could not update clock {new_job.name}: {error_message}'

        if updated_job is None:
            self.status = BROKEN
            # prevent update_clock from being called with again with skip_cloud_update
            self.save(skip_cloud_update=True)
            return False, return_message
        return True, f'Clock {self.name} updated successfully.'

    def delete_clock(self) -> Tuple[bool, str]:
        job, return_message = None, f"Could not retrieve clock {self.name} for deletion. (Missing logic branch)."
        try:
            job = cloud_scheduler.get_job(self.gcp_name)
        except (Exception, BaseException) as e:
            error_message = cloud_scheduler.get_error(e)
            # in case clock was never created
            if "Job not found" not in error_message:
                return True, f"Clock {self.name} deleted successfully."
            return_message = f'Could not retrieve clock {self.name} ' \
                             f'(alias for {self.gcp_name}) for deletion: {error_message}'

        if job is None:
            return False, return_message

        try:
            cloud_scheduler.delete_job(self.gcp_name)
            job = True
        except (Exception, BaseException) as e:
            error_message = cloud_scheduler.get_error(e)
            return_message = f'Could not delete clock {self.name} ' \
                             f'(alias for {self.gcp_name}): {error_message}'
        if job is None:
            self.status = BROKEN
            # prevent update_clock from being called with with skip_cloud_update
            self.save(skip_cloud_update=True)
            return False, return_message
        return True, f"Clock {self.name} deleted successfully."

    def save(self, force_insert=False, force_update=False, using=None,
             update_fields=None, skip_cloud_update=None):
        self.clean()
        is_new = self.pk is None
        # create/update new Cloud Scheduler job corresponding to Clock
        # if this model instance is just now being created.
        super().save(force_insert, force_update, using, update_fields)
        if is_new:
            if self.management == MANUAL:
                return self
            self.start_clock()
        else:
            # skip_cloud_update is passed by the *_clock methods when they call Clock.save().
            # this flag prevents infinite recursion from continually calling Clock.update_clock,
            # and some undesired updates
            if skip_cloud_update:
                return self
            _, message = self.update_clock()
            print(message)
        return self

    def delete(self, using=None, keep_parents=False):
        success, message = self.delete_clock()
        if not success:
            message = f'Error encountered while attempting to clean up Clock: {message}'
            raise cloud_scheduler.JobDeleteError(message)
        return super(Clock, self).delete(using=using, keep_parents=keep_parents)

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
