from django.shortcuts import redirect
from django.views.generic import UpdateView
from django.contrib import messages

from tasks.models import Clock
from tasks import cloud_scheduler

START, PAUSE, FIX, = 'start', 'pause', 'fix'


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
        if action == FIX:
            success, message = clock.start_clock()
            if not success:
                message = f'Could not start or restart clock: {message}'
                messages.error(request, message)
                return redirect("admin:tasks_clock_changelist")
            success, message = clock.update_clock()
            messages.success(request, message) if success else messages.error(request, message)

        return redirect("admin:tasks_clock_changelist")
