"""
Utility wrappers around Google's Cloud Scheduler API. See
https://googleapis.dev/python/cloudscheduler/latest/_modules/google/cloud/scheduler_v1/gapic/cloud_scheduler_client.html
for API reference.
"""
from typing import Union, Any

from pydantic import BaseModel

from google.cloud.scheduler_v1 import CloudSchedulerClient
from . conf import REGION, PROJECT_ID, SERVICE_ACCOUNT

client = CloudSchedulerClient()
parent = client.location_path(PROJECT_ID, REGION)


class JobRetrieveError(BaseException):
    pass


class JobCreationError(BaseException):
    pass


class JobUpdateError(BaseException):
    pass


class JobDeleteError(BaseException):
    pass


def get_error(exception):
    if hasattr(exception, 'message'):
        return exception.message
    return str(exception)


# Job attributes that can be changed.
MUTABLE_JOB_ATTRIBUTES = ('description', 'schedule', 'time_zone',)


class Job(BaseModel):
    name: str
    description: str
    target_url: str
    schedule: str
    time_zone: str

    @property
    def http_target(self):
        return {
            'uri': self.target_url,
            'oidc_token': {
                'service_account_email': SERVICE_ACCOUNT
            }
        }

    def __init__(self, name=None, **kwargs):
        super(Job, self).__init__(name=name, **kwargs)
        self.name = client.job_path(PROJECT_ID, REGION, name)

    def to_dict(self):
        _dict = {}
        for attr in ('name', ) + MUTABLE_JOB_ATTRIBUTES:
            _dict[attr] = self.__getattribute__(attr)
        _dict['http_target'] = self.http_target
        return _dict


def get_full_name(name):
    return client.job_path(PROJECT_ID, REGION, name)


def get_update_mask(old, new):
    _dict = {'paths': []}
    for attr in MUTABLE_JOB_ATTRIBUTES:
        if getattr(old, attr, False) != getattr(new, attr, False):
            _dict['paths'].append(attr)
    return _dict


def list_jobs():
    return tuple(client.list_jobs(parent))


def get_job(name: str):
    full_name = get_full_name(name)
    try:
        return client.get_job(full_name)
    except (BaseException, Exception) as e:
        error_message = get_error(e)
        raise JobRetrieveError(error_message)


def create_job(job: Job):
    """
    Creates a job in Cloud Scheduler

    :param job: Job to create
    :return:
    """

    try:
        return client.create_job(parent, job.to_dict())
    except (BaseException, Exception) as e:
        error_message = get_error(e)
        raise JobCreationError(error_message)


def pause_job(name: str):
    full_name = get_full_name(name)
    try:
        return client.pause_job(full_name)
    except (BaseException, Exception) as e:
        error_message = get_error(e)
        raise JobUpdateError(error_message)


def resume_job(name: str):
    full_name = get_full_name(name)
    try:
        return client.resume_job(full_name)
    except (BaseException, Exception) as e:
        error_message = get_error(e)
        raise JobUpdateError(error_message)


def update_job(name_or_job: Union[str, Any], new_job: Job):
    """
    Updates the job named `name` in Cloud Scheduler with the data
    provided by `new_job`.

    :param name_or_job: Name of job or job instance to be updated
    :param new_job: Job instance containing data to update Cloud Scheduler job with
    :return:
    """
    job = get_job(name_or_job) if isinstance(name_or_job, str) else name_or_job
    # update mask is used to specify which fields are being updated.
    update_mask = get_update_mask(job, new_job)
    try:
        return client.update_job(new_job.to_dict(), update_mask)
    except (BaseException, Exception) as e:
        error_message = get_error(e)
        raise JobUpdateError(error_message)


def delete_job(name: str):
    """
    Deletes the Cloud Scheduler job with the given name.

    :param name: Name of job to be deleted
    :return:
    """
    full_name = get_full_name(name)
    try:
        client.delete_job(full_name)
    except (BaseException, Exception) as e:
        error_message = get_error(e)
        raise JobDeleteError(error_message)
