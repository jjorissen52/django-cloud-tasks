from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from trades_portal import auth


class TestGoogleOpenIDAuth(APIView):
    authentication_classes = [auth.GoogleOpenIDAuthentication]

    def get(self, request, format=None):
        return Response({'ok': 'You did good.'}, status=status.HTTP_200_OK)

    def post(self, request, format=None):
        return Response({'ok': 'You did good.'}, status=status.HTTP_200_OK)
