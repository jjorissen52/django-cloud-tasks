from django.shortcuts import redirect
from django.urls import reverse
from django.utils.safestring import mark_safe
from django.views.generic import UpdateView
from django.contrib import messages

from tasks.models import Clock, Task, TaskSchedule
from tasks import cloud_scheduler

from tasks.constants import START, PAUSE, FIX, SYNC


class ClockActions(UpdateView):

    def get(self, request, *args, pk=-1, action=None, **kwargs):
        return self.post(request, *args, pk=pk, action=action, **kwargs)

    def post(self, request, *args, pk=-1, action=None, **kwargs):
        try:
            clock = Clock.objects.get(id=pk)
        except Clock.DoesNotExist:
            messages.error(request, f"Clock {pk} does not exist. Was it deleted?")
            return redirect("admin:tasks_clock_changelist")

        except cloud_scheduler.JobRetrieveError as e:
            messages.error(request, f"Could not retrieve the clock from Cloud Scheduler: "
                                    f"{cloud_scheduler.get_error(e)}")
            return redirect("admin:tasks_clock_changelist")
        if action == START:
            success, message = clock.start_clock()
            messages.success(request, message) if success else messages.error(request, message)
        if action == PAUSE:
            success, message = clock.pause_clock()
            messages.success(request, message) if success else messages.error(request, message)
        if action in FIX:
            success, message = clock.start_clock()
            if not success:
                message = f'Could not (re)start clock: {message}'
                messages.error(request, message)
                return redirect("admin:tasks_clock_changelist")
            success, message = clock.update_clock()
            messages.success(request, message) if success else messages.error(request, message)
        if action == SYNC:
            success, message = clock.sync_clock()
            messages.success(request, message) if success else messages.error(request, message)

        return redirect("admin:tasks_clock_changelist")


class TaskExecute(UpdateView):

    def get(self, request, *args, pk=-1, action=None, **kwargs):
        return self.post(request, *args, pk=pk, action=action, **kwargs)

    def post(self, request, *args, pk=-1, action=None, **kwargs):
        try:
            task = Task.objects.get(id=pk)
        except Task.DoesNotExist:
            messages.error(request, f"Task {pk} does not exist. Was it deleted?")
            return redirect("admin:tasks_task_changelist")

        task_execution = task.execute()
        task_execution_url = reverse("admin:tasks_taskexecution_change", kwargs={"object_id": task_execution.pk})
        message = mark_safe(f'Task {task.name} is complete. '
                            f'See <a href="{task_execution_url}">Task Execution</a> for details.')
        messages.success(request, message)
        return redirect("admin:tasks_task_changelist")


class TaskScheduleRun(UpdateView):

    def get(self, request, *args, pk=-1, action=None, **kwargs):
        return self.post(request, *args, pk=pk, action=action, **kwargs)

    def post(self, request, *args, pk=-1, action=None, **kwargs):
        try:
            task_schedule = TaskSchedule.objects.get(id=pk)
            task = task_schedule.task
        except TaskSchedule.DoesNotExist:
            messages.error(request, f"TaskSchedule {pk} does not exist. Was it deleted?")
            return redirect("admin:tasks_taskschedule_changelist")

        task_execution = task_schedule.run()
        task_execution_url = reverse("admin:tasks_taskexecution_change", kwargs={"object_id": task_execution.pk})
        message = mark_safe(f'Task {task.name} has been scheduled. '
                            f'See <a href="{task_execution_url}">Task Execution</a> for details.')
        messages.success(request, message)
        return redirect("admin:tasks_taskschedule_changelist")
