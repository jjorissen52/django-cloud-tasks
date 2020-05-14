from django.shortcuts import redirect
from django.views.generic import UpdateView
from django.contrib import messages

from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from . import auth
from .models import Clock
from . import cloud_scheduler


class TestGoogleOpenIDAuth(APIView):
    authentication_classes = [auth.GoogleOpenIDAuthentication]

    def get(self, request, format=None):
        return Response({'ok': 'You did good.'}, status=status.HTTP_200_OK)

    def post(self, request, format=None):
        return Response({'ok': 'You did good.'}, status=status.HTTP_200_OK)


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
            success, message = clock.start()
            messages.success(request, message) if success else message.error(request, message)
            return redirect("admin:tasks_clock_changelist")
        if action == PAUSE:
            success, message = clock.pause()
            messages.success(request, message) if success else message.error(request, message)
            return redirect("admin:tasks_clock_changelist")
