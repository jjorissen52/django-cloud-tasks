from django.urls import path, include

from rest_framework import routers

from cloud_tasks import views
from cloud_tasks import api

router = routers.DefaultRouter()
router.register(r'clocks', api.ClockViewSet)
router.register(r'tasks', api.TaskViewSet)
router.register(r'steps', api.StepViewSet)
router.register(r'task_executions', api.TaskExecutionViewSet)
router.register(r'task_schedules', api.TaskScheduleViewSet)

urlpatterns = [
    path("cloud-tasks/", include(([
        path('clock/<int:pk>/<str:action>/', views.ClockActions.as_view(), name="clock_actions"),
        path('task/<int:pk>/execute/', views.TaskExecute.as_view(), name="task_execute"),
        path('taskschedule/<int:pk>/run/', views.TaskScheduleRun.as_view(), name="taskschedule_run"),
        path('api/test-auth/', api.TestGoogleOpenIDAuth.as_view(), name="test_openid_auth"),
        path('api/', include(router.urls))
    ], 'cloud_tasks'), namespace="cloud_tasks"))
]
