from django.urls import path, include

from rest_framework.urlpatterns import format_suffix_patterns
from rest_framework import routers

from . import views
from . import api

router = routers.SimpleRouter()
router.register(r'clocks', api.ClockViewSet)

urlpatterns = [
    path('clock/<int:pk>/<str:action>/', views.ClockActions.as_view(), name="clock_actions"),
    path('api/test-auth/', api.TestGoogleOpenIDAuth.as_view()),
    path('api/', include(router.urls))
]

urlpatterns = format_suffix_patterns(urlpatterns)
