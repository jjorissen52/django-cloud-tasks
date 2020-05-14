from django.urls import path
from rest_framework.urlpatterns import format_suffix_patterns

from . import views

urlpatterns = [
    path('test-auth/', views.TestGoogleOpenIDAuth.as_view()),
]

urlpatterns = format_suffix_patterns(urlpatterns)
