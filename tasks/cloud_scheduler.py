"""
Utility wrappers around Google's Cloud Scheduler API. See
https://googleapis.dev/python/cloudscheduler/latest/_modules/google/cloud/scheduler_v1/gapic/cloud_scheduler_client.html
for API reference.
"""

from pydantic import BaseModel

from google.cloud.scheduler_v1 import CloudSchedulerClient
from . conf import REGION, PROJECT_ID, ROOT_URL

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


class Job(BaseModel):
    name: str
    description: str
    http_target: str
    schedule: str
    time_zone: str

    def to_dict(self):
        _dict = {}
        attributes = ['name', 'description', 'schedule', 'time_zone']
        for attr in attributes:
            if attr == 'name':
                _dict[attr] = client.job_path(PROJECT_ID, REGION, self.__getattribute__(attr))
            else:
                _dict[attr] = self.__getattribute__(attr)
        _dict['http_target'] = {'uri': self.http_target}
        return _dict


def list_jobs():
    return tuple(client.list_jobs(parent))


def get_job(name: str):
    full_name = client.job_path(PROJECT_ID, REGION, name)
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
    full_name = client.job_path(PROJECT_ID, REGION, name)
    try:
        return client.pause_job(full_name)
    except (BaseException, Exception) as e:
        error_message = get_error(e)
        raise JobUpdateError(error_message)


def resume_job(name: str):
    full_name = client.job_path(PROJECT_ID, REGION, name)
    try:
        return client.resume_job(full_name)
    except (BaseException, Exception) as e:
        error_message = get_error(e)
        raise JobUpdateError(error_message)


def update_job(name: str, new_job: Job):
    """
    Updates the job named `name` in Cloud Scheduler with the data
    provided by `new_job`.

    :param name: Name of job to be updated
    :param new_job: Job instance containing data to update Cloud Scheduler job with
    :return:
    """
    job = get_job(name)
    # update mask is used to specify which fields are being updated.
    update_mask = job.to_dict()
    if name == new_job.name:
        update_mask.pop('name')
    try:
        return client.update_job(job, update_mask)
    except (BaseException, Exception) as e:
        error_message = get_error(e)
        raise JobUpdateError(error_message)


def delete_job(name: str):
    """
    Deletes the Cloud Scheduler job with the given name.

    :param name: Name of job to be deleted
    :return:
    """
    full_name = client.job_path(PROJECT_ID, REGION, name)
    try:
        client.delete_job(full_name)
    except (BaseException, Exception) as e:
        error_message = get_error(e)
        raise JobDeleteError(error_message)
