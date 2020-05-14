from django.urls import path
from rest_framework.urlpatterns import format_suffix_patterns

from . import views

urlpatterns = [
    path('test-auth/', views.TestGoogleOpenIDAuth.as_view()),
    path('clock/<int:pk>/<str:action>/', views.ClockActions.as_view(), name="clock_actions")
]

urlpatterns = format_suffix_patterns(urlpatterns)
