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
    path('task/<int:pk>/execute/', views.TaskExecute.as_view(), name="task_execute"),
    path('taskschedule/<int:pk>/run/', views.TaskScheduleRun.as_view(), name="taskschedule_run"),
    path('api/test-auth/', api.TestGoogleOpenIDAuth.as_view()),
    path('api/', include(router.urls))
]
