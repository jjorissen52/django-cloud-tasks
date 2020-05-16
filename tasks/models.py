import functools
import json
import re
from typing import Tuple

from django.contrib.postgres.fields import JSONField
from django.db import models
from django.forms import model_to_dict

from tasks import cloud_scheduler
from tasks.conf import ROOT_URL
from tasks.constants import *
from tasks import session as requests


def ignore_unmanaged_clock(method):
    def inner(self, *args, **kwargs):
        if self.management == MANUAL:
            return True, f"Skipping action {method.__name__} for manually managed clock {self.name}"
        return method(self, *args, **kwargs)
    inner.__name__ = method.__name__
    return inner


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
                                   target_url=f'{ROOT_URL}/tasks/api/clocks/{self.pk}/tick/')

    def clean(self):
        if self.management == MANUAL:
            self.status = UNKNOWN
        if not self.gcp_name:
            # make the name friendly for GCP. The value of this field will never change for a given clock.
            self.gcp_name = re.sub(r'[^\w-]', '-', self.name)
        return self

    @ignore_unmanaged_clock
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
            return False, f"Could not (re)start clock {self.name}: {error_message}"

        self.status = RUNNING
        self.save(skip_cloud_update=True)
        return True, f"Clock {job.name} is running."

    @ignore_unmanaged_clock
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

    @ignore_unmanaged_clock
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

    @ignore_unmanaged_clock
    def delete_clock(self) -> Tuple[bool, str]:
        job, return_message = None, f"Could not retrieve clock {self.name} for deletion. (Missing logic branch)."
        try:
            job = cloud_scheduler.get_job(self.gcp_name)
        except (Exception, BaseException) as e:
            error_message = cloud_scheduler.get_error(e)
            # in case clock was never created
            if "Job not found" in error_message:
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

    def sync_clock(self) -> Tuple[bool, str]:
        self.management = GCP
        success, message = self.start_clock()
        if not success:
            message = f'Could not sync clock: {message}'
            return success, message
        success, message = self.update_clock()
        if not success:
            message = f'Could not sync clock: {message}'
        return success, message

    def save(self, force_insert=False, force_update=False, using=None,
             update_fields=None, skip_cloud_update=None):
        self.clean()
        is_new = self.pk is None
        # create/update new Cloud Scheduler job corresponding to Clock
        # if this model instance is just now being created.
        super().save(force_insert, force_update, using, update_fields)
        # do not manage the clock via save in manual mode
        if self.management == MANUAL:
            return self
        if is_new:
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


class TaskSchedule(models.Model):
    """
    Execution Schedule for a `Task`. Each time the `Clock` ticks, a `TaskExecution` will be created.
    """

    name = models.CharField(max_length=MAX_NAME_LENGTH, unique=True, help_text="Name of Task Schedule")
    task = models.ForeignKey('tasks.Task', on_delete=models.PROTECT, related_name='schedules')

    clock = models.ForeignKey(Clock, null=True, on_delete=models.SET_NULL, related_name='schedules')

    enabled = models.BooleanField(default=True, help_text="Whether or not task schedule is enabled.")

    @property
    def status(self):
        if self.clock is None:
            return "No associated clock; manual execution only."
        if not self.enabled:
            return "Disabled; manual execution only."
        if self.clock.status == RUNNING:
            return f"Will execute on next tick of clock {self.clock.name}"
        elif self.clock.status == PAUSED:
            return f"Clock {self.clock.name} paused; manual execution only."
        elif self.clock.status == UNKNOWN:
            return f"Unknown; clock {self.clock.name} is manually managed and it's state is unknown."
        elif self.clock.status == BROKEN:
            return f"Clock {self.clock.name} broken; manual execution only."
        else:
            return f"Clock {self.clock.name} is in corrupted state {self.clock.status}; this should not have happened."

    def __str__(self):
        return f'{self.name}: {self.task}'


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


class Task(models.Model):
    """
    A series of `Steps` to be executed at a set time.
    """
    name = models.CharField(max_length=MAX_NAME_LENGTH, unique=True, help_text="Name of Task")

    def execute(self):
        task_execution = TaskExecution.objects.create(task=self)
        successes = []
        task_results = {'steps': {}}
        steps = self.steps.all()
        for step in steps:
            success, status_code, response_dict = step.execute()
            successes.append(success)
            task_results['steps'].update({
                step.name: response_dict
            })

        num_successes = len(steps) if all(successes) else len(tuple(filter(lambda x: x, successes)))
        all_completed = num_successes == len(steps)
        task_results.update({
            'all_completed': all_completed,
            'steps_completed': num_successes,
            'steps_failed': len(steps) - num_successes,
        })
        task_execution.status = SUCCESS if all_completed else FAILURE
        task_execution.results = task_results
        task_execution.save()
        return task_execution

    def __str__(self):
        return self.name


def format_response_tuple(method):
    """
    Convenience wrapper for formatting a tuple(success, status_code, response_text, failure_reason) response
    :param method: method to be wrapped
    :return:
    """
    @functools.wraps(method)
    def inner(*args, **kwargs) -> Tuple[bool, int, dict]:
        try:
            step_summary, success, status_code, response_text, failure_reason = method(*args, **kwargs)
        except (Exception, BaseException) as e:
            step_summary, success, status_code, response_text, failure_reason = \
                'unknown', False, 500, None, f'{e.__class__.__name__}("{e}")'
        response_dict = {
            'summary': step_summary,
            'response': {
                'success': success,
                'status': status_code,
            }
        }
        try:
            response_dict['response']['content'] = json.loads(response_text)
            response_dict['response']['is_json'] = True
        except (json.JSONDecodeError, TypeError):
            response_dict['response']['content'] = response_text
            response_dict['response']['is_json'] = False
        if failure_reason:
            response_dict['response']['error'] = failure_reason

        return success, status_code, response_dict
    return inner


class Step(models.Model):
    """
    A single step to be performed during execution of a `Task`. Currently,
    making requests to URLs authenticated with Google's OpenID as the App Engine service
    account are the only supported actions.
    """
    task = models.ForeignKey(Task, on_delete=models.PROTECT, related_name='steps')
    name = models.CharField(max_length=MAX_NAME_LENGTH, unique=True, help_text="Name of Step")
    action = models.URLField(help_text="URL to place request")
    payload = JSONField(null=True, blank=True, help_text="JSON Payload of request")

    success_pattern = models.CharField(null=True, blank=True, max_length=255,
                                       help_text="Regex corresponding to successful execution")

    @format_response_tuple
    def execute(self, session=None) -> Tuple[dict, bool, int, str, str]:
        """
        Make a POST request, check the response
        :param session: http session to use for step
        :return: success: bool, response.status_code: int, response.text: str
        """
        step_summary = model_to_dict(self)
        session = requests.create_openid_session(audience=self.action) if not session else session
        with session as s:
            response = s.post(self.action, data=self.payload)
        # if redirect or some error code
        if response.status_code > 299:
            return step_summary, False, response.status_code, response.text, "HTTP Error"
        success, failure_reason = True, None
        if self.success_pattern is not None:
            success_regex = re.compile(self.success_pattern)
            # success if our patten matches any part of the response text
            success = success_regex.search(response.text) is not None
            failure_reason = None if success else f"response content did not match success_regex={self.success_pattern}"
        return step_summary, success, response.status_code, response.text, failure_reason

    class Meta:
        unique_together = ("name", "task", )

    def __str__(self):
        return f'{self.name} (of {self.task})'
