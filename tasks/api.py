from rest_framework import serializers, viewsets, status
from rest_framework.reverse import reverse
from rest_framework.settings import api_settings
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.exceptions import APIException

from tasks import auth
from tasks.models import Clock, Step, Task, TaskExecution, TaskSchedule
from tasks.permissions import DjangoModelPermissionsWithRead, IsTimekeeper, StepExecutor, TaskExecutor


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


class BrokenClockError(APIException):
    pass


class StepFailureError(APIException):
    pass


class ClockViewSet(viewsets.ModelViewSet):
    """
    Provides CRUD capabilities to the `Clock` model.
    """
    authentication_classes = [*api_settings.DEFAULT_AUTHENTICATION_CLASSES, auth.GoogleOpenIDAuthentication, ]
    permission_classes = [DjangoModelPermissionsWithRead]
    queryset = Clock.objects.all()
    serializer_class = ClockSerializer

    @action(detail=True, methods=['post', 'get'], permission_classes=[IsTimekeeper])
    def tick(self, request, pk=None):
        """
        Execute Tasks associated with the clock on a tick.

        :param request:
        :param pk:
        :return:
        """
        clock = self.get_object()
        return Response(clock.tick())

    # allowing GET for use from browser
    @action(detail=True, methods=['post', 'get'], permission_classes=[IsTimekeeper])
    def start(self, request, pk=None):
        clock = self.get_object()
        success, message = clock.start_clock()
        if not success:
            raise BrokenClockError(message)
        return Response({"message": message})

    # allowing GET for use from browser
    @action(detail=True, methods=['post', 'get'], permission_classes=[IsTimekeeper])
    def pause(self, request, pk=None):
        clock = self.get_object()
        success, message = clock.pause_clock()
        if not success:
            raise BrokenClockError(message)
        return Response({"message": message})

    @action(detail=True, methods=['post'], url_path="update", permission_classes=[IsTimekeeper])
    def clock_update(self, request, pk=None):
        clock = self.get_object()
        success, message = clock.update_clock()
        if not success:
            raise BrokenClockError(message)
        return Response({"message": message})

    # allowing GET for use from browser
    @action(detail=True, methods=['post', 'get'], url_path="delete", permission_classes=[IsTimekeeper])
    def clock_delete(self, request, pk=None):
        clock = self.get_object()
        success, message = clock.delete_clock()
        if not success:
            raise BrokenClockError(message)
        return Response({"message": message})

    # allowing GET for use from browser
    @action(detail=True, methods=['post', 'get'], permission_classes=[IsTimekeeper])
    def sync(self, request, pk=None):
        clock = self.get_object()
        success, message = clock.sync_clock()
        if not success:
            raise BrokenClockError(message)
        return Response({"message": message})


class StepSerializer(serializers.ModelSerializer):

    url = serializers.HyperlinkedIdentityField(view_name='tasks:step-detail')

    class Meta:
        model = Step
        fields = '__all__'


class StepViewSet(viewsets.ModelViewSet):
    """
    Provides CRUD capabilities to the `Step` model.
    """
    authentication_classes = [*api_settings.DEFAULT_AUTHENTICATION_CLASSES, auth.GoogleOpenIDAuthentication, ]
    permission_classes = [DjangoModelPermissionsWithRead]
    queryset = Step.objects.all()
    serializer_class = StepSerializer

    # allowing GET for use from browser
    @action(detail=True, methods=['post', 'get'], permission_classes=[StepExecutor])
    def execute(self, request, pk=None):
        step = self.get_object()
        success, status_code, response_dict = step.execute()
        if not success:
            raise StepFailureError(code=f'task_{status_code}', detail=response_dict)
        return Response({"result": response_dict})


class TaskSerializer(serializers.ModelSerializer):

    url = serializers.HyperlinkedIdentityField(view_name='tasks:task-detail')

    class Meta:
        model = Task
        fields = '__all__'


class TaskViewSet(viewsets.ModelViewSet):
    """
    Provides CRUD capabilities to the `Task` model.
    """
    authentication_classes = [*api_settings.DEFAULT_AUTHENTICATION_CLASSES, auth.GoogleOpenIDAuthentication, ]
    permission_classes = [DjangoModelPermissionsWithRead]
    queryset = Task.objects.all()
    serializer_class = TaskSerializer

    # allowing GET for use from browser
    @action(detail=True, methods=['post', 'get'], permission_classes=[TaskExecutor])
    def execute(self, request, pk=None):
        task = self.get_object()
        task_execution_id = request.query_params.get('task_execution_id', None)
        task_execution = task.execute(task_execution_id)
        return Response(task_execution.results)


class TaskExecutionSerializer(serializers.ModelSerializer):

    url = serializers.HyperlinkedIdentityField(view_name='tasks:taskexecution-detail')
    task = serializers.HyperlinkedRelatedField(view_name='tasks:task-detail', read_only=True)

    class Meta:
        model = TaskExecution
        fields = '__all__'


class TaskExecutionViewSet(viewsets.ModelViewSet):
    """
    Provides CRUD capabilities to the `TaskExecution` model.
    """
    authentication_classes = [*api_settings.DEFAULT_AUTHENTICATION_CLASSES, auth.GoogleOpenIDAuthentication, ]
    permission_classes = [DjangoModelPermissionsWithRead]
    queryset = TaskExecution.objects.all().order_by('id')
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
    authentication_classes = [*api_settings.DEFAULT_AUTHENTICATION_CLASSES, auth.GoogleOpenIDAuthentication, ]
    permission_classes = [DjangoModelPermissionsWithRead]
    queryset = TaskSchedule.objects.all()
    serializer_class = TaskScheduleSerializer

    # allowing GET for use from browser
    @action(detail=True, methods=['post', 'get'], permission_classes=[TaskExecutor])
    def run(self, request, pk=None):
        task_schedule = self.get_object()
        task_execution = task_schedule.run()
        if isinstance(task_execution, TaskExecution):
            return Response({
                "result": "Execution scheduled.",
                "task_execution": {
                    'canonical': reverse("tasks:taskexecution-detail",
                                         request=request, kwargs={"pk": task_execution.pk}),
                    'admin': reverse("admin:tasks_taskexecution_change",
                                     request=request, kwargs={"object_id": task_execution.pk}),
                }
            })

        return Response(task_execution.results)
