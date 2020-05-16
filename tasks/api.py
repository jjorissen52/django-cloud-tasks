from rest_framework import serializers, viewsets, status, authentication
from rest_framework.settings import api_settings
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView

from tasks import auth
from tasks.models import Clock, Step, Task, TaskExecution, TaskSchedule


class TestGoogleOpenIDAuth(APIView):
    authentication_classes = [*api_settings.DEFAULT_AUTHENTICATION_CLASSES, auth.GoogleOpenIDAuthentication, ]

    @staticmethod
    def get(request, format=None):
        return Response({'ok': 'You did good.'}, status=status.HTTP_200_OK)

    @staticmethod
    def post(request, format=None):
        return Response({'ok': 'You did good.'}, status=status.HTTP_200_OK)


class ClockSerializer(serializers.ModelSerializer):

    url = serializers.HyperlinkedIdentityField(view_name='tasks:clock-detail')
    gcp_name = serializers.ReadOnlyField()
    status = serializers.ReadOnlyField()

    class Meta:
        model = Clock
        fields = '__all__'


class ClockViewSet(viewsets.ModelViewSet):
    """
    Provides CRUD capabilities to the `Clock` model.
    """
    authentication_classes = [*api_settings.DEFAULT_AUTHENTICATION_CLASSES, auth.GoogleOpenIDAuthentication, ]
    queryset = Clock.objects.all()
    serializer_class = ClockSerializer

    @action(detail=True, methods=['post'])
    def tick(self, request, pk=None):
        """
        Execute Tasks associated with the clock on a tick

        :param request:
        :param pk:
        :return:
        """
        clock = self.get_object()
        schedules = clock.schedules.all()
        exceution_summary = {}
        for schedule in schedules:
            exceution_summary[schedule.name] = schedule.task.execute().results
        return Response(exceution_summary)


class StepSerializer(serializers.ModelSerializer):

    url = serializers.HyperlinkedIdentityField(view_name='tasks:step-detail')

    class Meta:
        model = Step
        fields = '__all__'


class StepViewSet(viewsets.ModelViewSet):
    """
    Provides CRUD capabilities to the `Step` model.
    """
    queryset = Step.objects.all()
    serializer_class = StepSerializer


class TaskSerializer(serializers.ModelSerializer):

    url = serializers.HyperlinkedIdentityField(view_name='tasks:task-detail')

    class Meta:
        model = Task
        fields = '__all__'


class TaskViewSet(viewsets.ModelViewSet):
    """
    Provides CRUD capabilities to the `Task` model.
    """
    queryset = Task.objects.all()
    serializer_class = TaskSerializer


class TaskExecutionSerializer(serializers.ModelSerializer):

    url = serializers.HyperlinkedIdentityField(view_name='tasks:taskexecution-detail')

    class Meta:
        model = TaskExecution
        fields = '__all__'


class TaskExecutionViewSet(viewsets.ModelViewSet):
    """
    Provides CRUD capabilities to the `TaskExecution` model.
    """
    queryset = TaskExecution.objects.all()
    serializer_class = TaskExecutionSerializer


class TaskScheduleSerializer(serializers.ModelSerializer):

    url = serializers.HyperlinkedIdentityField(view_name='tasks:taskschedule-detail')

    class Meta:
        model = TaskSchedule
        fields = '__all__'


class TaskScheduleViewSet(viewsets.ModelViewSet):
    """
    Provides CRUD capabilities to the `TaskSchedule` model.
    """
    queryset = TaskSchedule.objects.all()
    serializer_class = TaskScheduleSerializer
