from rest_framework import serializers, viewsets, status, authentication
from rest_framework.settings import api_settings
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView

from . import auth
from tasks.models import Clock


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
        print(schedules)
        return Response({"status": "ok"})
