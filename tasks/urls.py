from django.urls import path, include

from rest_framework import routers

from tasks import views
from tasks import api

router = routers.DefaultRouter()
router.register(r'clocks', api.ClockViewSet)
router.register(r'tasks', api.TaskViewSet)
router.register(r'steps', api.StepViewSet)
router.register(r'task_executions', api.TaskExecutionViewSet)
router.register(r'task_schedules', api.TaskScheduleViewSet)

urlpatterns = [
    path('clock/<int:pk>/<str:action>/', views.ClockActions.as_view(), name="clock_actions"),
    path('api/test-auth/', api.TestGoogleOpenIDAuth.as_view()),
    path('api/', include(router.urls))
]
