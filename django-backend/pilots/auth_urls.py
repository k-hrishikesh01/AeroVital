from django.urls import path
from .auth_views import ObtainAuthTokenView, CurrentUserView, LogoutView

urlpatterns = [
    path("token/", ObtainAuthTokenView.as_view(), name="auth-token"),
    path("me/", CurrentUserView.as_view(), name="auth-me"),
    path("logout/", LogoutView.as_view(), name="auth-logout"),
]
