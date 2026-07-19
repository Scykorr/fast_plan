from django.urls import path

from accounts.views import (
    CsrfCookieView,
    LoginView,
    LogoutView,
    MeView,
    RefreshView,
    RegisterView,
)

urlpatterns = [
    path("register/", RegisterView.as_view(), name="register"),
    path("login/", LoginView.as_view(), name="login"),
    path("refresh/", RefreshView.as_view(), name="refresh"),
    path("logout/", LogoutView.as_view(), name="logout"),
    path("csrf/", CsrfCookieView.as_view(), name="csrf"),
    path("me/", MeView.as_view(), name="me"),
]
