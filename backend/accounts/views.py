from django.conf import settings
from django.contrib.auth.tokens import PasswordResetTokenGenerator
from django.middleware.csrf import get_token
from django.utils.decorators import method_decorator
from django.utils.encoding import force_bytes, force_str
from django.utils.http import urlsafe_base64_decode, urlsafe_base64_encode
from django.views.decorators.csrf import ensure_csrf_cookie
from rest_framework import generics, status
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.exceptions import InvalidToken, TokenError
from rest_framework_simplejwt.serializers import TokenRefreshSerializer
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenObtainPairView

from accounts.authentication import enforce_csrf
from accounts.cookies import clear_auth_cookies, set_auth_cookies
from accounts.models import User
from accounts.serializers import (
    EmailVerificationResendSerializer,
    EmailVerificationSerializer,
    PasswordChangeSerializer,
    PasswordForgotSerializer,
    PasswordResetSerializer,
    ProfileSerializer,
    RegisterSerializer,
    UserSerializer,
)
from accounts.tokens import (
    EmailTokenObtainPairSerializer,
    email_verification_token_generator,
)
from notifications.mail import absolute_frontend_url, send_app_email

password_reset_token_generator = PasswordResetTokenGenerator()


def _send_verification_email(user):
    uid = urlsafe_base64_encode(force_bytes(user.pk))
    token = email_verification_token_generator.make_token(user)
    verification_url = absolute_frontend_url(
        f"/verify-email?uid={uid}&token={token}"
    )
    return send_app_email(
        to=user.email,
        subject="Подтверждение email — Fast Plan",
        template_base="email/email_verification",
        context={"verification_url": verification_url, "user": user},
    )


class RegisterView(generics.CreateAPIView):
    serializer_class = RegisterSerializer
    permission_classes = [AllowAny]

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        _send_verification_email(user)
        return Response(
            UserSerializer(user, context={"request": request}).data,
            status=status.HTTP_201_CREATED,
        )


@method_decorator(ensure_csrf_cookie, name="dispatch")
class CsrfCookieView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        return Response({"csrfToken": get_token(request)})


class MeView(APIView):
    permission_classes = [IsAuthenticated]
    parser_classes = [JSONParser, FormParser, MultiPartParser]

    def get(self, request):
        return Response(
            UserSerializer(request.user, context={"request": request}).data
        )

    def patch(self, request):
        serializer = ProfileSerializer(
            request.user,
            data=request.data,
            partial=True,
            context={"request": request},
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(
            UserSerializer(request.user, context={"request": request}).data
        )


class EmailVerificationView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = EmailVerificationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            user_id = force_str(
                urlsafe_base64_decode(serializer.validated_data["uid"])
            )
            user = User.objects.get(pk=user_id)
        except (User.DoesNotExist, ValueError, TypeError, OverflowError):
            return Response(
                {"detail": "Недействительная ссылка подтверждения."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if user.is_email_verified:
            return Response({"detail": "Email уже подтверждён."})
        if not email_verification_token_generator.check_token(
            user, serializer.validated_data["token"]
        ):
            return Response(
                {"detail": "Ссылка подтверждения недействительна или устарела."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        user.verify_email()
        return Response({"detail": "Email подтверждён."})


class EmailVerificationResendView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = EmailVerificationResendSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        email = serializer.validated_data["email"].lower().strip()
        user = User.objects.filter(email__iexact=email).first()
        if user is not None and not user.is_email_verified:
            _send_verification_email(user)
        return Response(
            {
                "detail": (
                    "Если аккаунт существует и email ещё не подтверждён, "
                    "новая ссылка отправлена."
                )
            }
        )


@method_decorator(ensure_csrf_cookie, name="dispatch")
class LoginView(TokenObtainPairView):
    permission_classes = [AllowAny]
    serializer_class = EmailTokenObtainPairSerializer

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        access = serializer.validated_data["access"]
        refresh = serializer.validated_data["refresh"]
        response = Response(
            {
                "detail": "ok",
                "user": UserSerializer(
                    serializer.user, context={"request": request}
                ).data,
            },
            status=status.HTTP_200_OK,
        )
        set_auth_cookies(response, access=access, refresh=refresh)
        return response


class RefreshView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        raw_refresh = request.COOKIES.get(settings.JWT_REFRESH_COOKIE) or request.data.get(
            "refresh"
        )
        if not raw_refresh:
            return Response(
                {"detail": "Refresh token missing."},
                status=status.HTTP_401_UNAUTHORIZED,
            )
        if request.COOKIES.get(settings.JWT_REFRESH_COOKIE):
            enforce_csrf(request)
        serializer = TokenRefreshSerializer(data={"refresh": raw_refresh})
        try:
            serializer.is_valid(raise_exception=True)
        except TokenError as exc:
            raise InvalidToken(exc.args[0]) from exc

        access = serializer.validated_data["access"]
        refresh = serializer.validated_data.get("refresh", raw_refresh)
        response = Response({"detail": "ok"}, status=status.HTTP_200_OK)
        set_auth_cookies(response, access=access, refresh=refresh)
        return response


class LogoutView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        raw_refresh = request.COOKIES.get(settings.JWT_REFRESH_COOKIE)
        if raw_refresh:
            try:
                RefreshToken(raw_refresh).blacklist()
            except TokenError:
                pass
        response = Response({"detail": "ok"}, status=status.HTTP_200_OK)
        clear_auth_cookies(response)
        return response


def _blacklist_refresh_cookie(request, response):
    raw_refresh = request.COOKIES.get(settings.JWT_REFRESH_COOKIE)
    if raw_refresh:
        try:
            RefreshToken(raw_refresh).blacklist()
        except TokenError:
            pass
    clear_auth_cookies(response)
    return response


class PasswordForgotView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = PasswordForgotSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        email = serializer.validated_data["email"].lower().strip()
        user = User.objects.filter(email__iexact=email).first()
        if user is not None:
            uid = urlsafe_base64_encode(force_bytes(user.pk))
            token = password_reset_token_generator.make_token(user)
            reset_url = absolute_frontend_url(
                f"/reset-password?uid={uid}&token={token}"
            )
            send_app_email(
                to=user.email,
                subject="Сброс пароля — Fast Plan",
                template_base="email/password_reset",
                context={"reset_url": reset_url},
            )
        return Response(
            {"detail": "If an account exists for this email, a reset link was sent."},
            status=status.HTTP_200_OK,
        )


class PasswordResetView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = PasswordResetSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        uid = serializer.validated_data["uid"]
        token = serializer.validated_data["token"]
        new_password = serializer.validated_data["new_password"]
        try:
            user_id = force_str(urlsafe_base64_decode(uid))
            user = User.objects.get(pk=user_id)
        except (User.DoesNotExist, ValueError, TypeError, OverflowError):
            return Response(
                {"detail": "Invalid reset link."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if not password_reset_token_generator.check_token(user, token):
            return Response(
                {"detail": "Invalid or expired reset token."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        user.set_password(new_password)
        user.save(update_fields=["password"])
        response = Response({"detail": "ok"}, status=status.HTTP_200_OK)
        return _blacklist_refresh_cookie(request, response)


class PasswordChangeView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = PasswordChangeSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        current_password = serializer.validated_data["current_password"]
        new_password = serializer.validated_data["new_password"]
        if not request.user.check_password(current_password):
            return Response(
                {"current_password": ["Неверный текущий пароль."]},
                status=status.HTTP_400_BAD_REQUEST,
            )
        request.user.set_password(new_password)
        request.user.save(update_fields=["password"])
        response = Response({"detail": "ok"}, status=status.HTTP_200_OK)
        return _blacklist_refresh_cookie(request, response)
