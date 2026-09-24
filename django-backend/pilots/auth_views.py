from django.contrib.auth import authenticate
from rest_framework import status, permissions
from rest_framework.authtoken.models import Token
from rest_framework.response import Response
from rest_framework.views import APIView
from .serializers import PilotSerializer


class ObtainAuthTokenView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        username = request.data.get("username")
        password = request.data.get("password")

        if not username or not password:
            return Response(
                {"detail": "Both username and password are required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        user = authenticate(username=username, password=password)
        if not user:
            return Response(
                {"detail": "Invalid credentials."},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        token, _ = Token.objects.get_or_create(user=user)
        pilot_data = None
        if hasattr(user, "pilot_profile"):
            pilot_data = PilotSerializer(user.pilot_profile).data

        return Response({
            "token": token.key,
            "user_id": user.pk,
            "username": user.username,
            "pilot": pilot_data,
        })


class CurrentUserView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        user = request.user
        pilot_data = None
        if hasattr(user, "pilot_profile"):
            pilot_data = PilotSerializer(user.pilot_profile).data

        return Response({
            "user_id": user.pk,
            "username": user.username,
            "email": user.email,
            "pilot": pilot_data,
        })


class LogoutView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        if hasattr(request.user, "auth_token"):
            request.user.auth_token.delete()
        return Response({"detail": "Successfully logged out."})
