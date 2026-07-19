from django.urls import path

from accounts.views import (
    CsrfCookieView,
    EmailVerificationResendView,
    EmailVerificationView,
    LoginView,
    LogoutView,
    MeView,
    PasswordChangeView,
    PasswordForgotView,
    PasswordResetView,
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
    path(
        "email/verify/",
        EmailVerificationView.as_view(),
        name="email-verification",
    ),
    path(
        "email/resend/",
        EmailVerificationResendView.as_view(),
        name="email-verification-resend",
    ),
    path("password/forgot/", PasswordForgotView.as_view(), name="password-forgot"),
    path("password/reset/", PasswordResetView.as_view(), name="password-reset"),
    path("password/change/", PasswordChangeView.as_view(), name="password-change"),
]
