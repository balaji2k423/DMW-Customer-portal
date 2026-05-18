from rest_framework import generics, status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated, BasePermission
from rest_framework_simplejwt.views import TokenObtainPairView
from api.throttling import LoginThrottle
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.exceptions import TokenError
from .models import CustomUser, UserRole, GuestPermission
from .serializers import (
    AdminCreateUserSerializer,
    AdminUpdateUserSerializer,
    CustomTokenObtainPairSerializer,
    GuestPermissionBulkSerializer,
    GuestPermissionSerializer,
    UserSerializer,
    RegisterSerializer,
    ChangePasswordSerializer,
)


# ─── Custom permissions ───────────────────────────────────────────────────────

class IsAdmin(BasePermission):
    """Allow access only to users with role='admin'."""
    def has_permission(self, request, view):
        return bool(
            request.user and
            request.user.is_authenticated and
            request.user.role == UserRole.ADMIN
        )


# ─── Auth views ───────────────────────────────────────────────────────────────

class LoginView(TokenObtainPairView):
    serializer_class = CustomTokenObtainPairSerializer
    throttle_classes = [LoginThrottle]
    permission_classes = [AllowAny]


class RegisterView(generics.CreateAPIView):
    queryset = CustomUser.objects.all()
    permission_classes = [AllowAny]
    serializer_class = RegisterSerializer


class ProfileView(generics.RetrieveUpdateAPIView):
    serializer_class = UserSerializer
    permission_classes = [IsAuthenticated]

    def get_object(self):
        return self.request.user


class ChangePasswordView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = ChangePasswordSerializer(data=request.data)
        if serializer.is_valid():
            user = request.user
            if not user.check_password(serializer.validated_data['old_password']):
                return Response(
                    {'error': 'Wrong current password.'},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            user.set_password(serializer.validated_data['new_password'])
            user.save()
            return Response({'message': 'Password updated successfully.'})
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class LogoutView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        refresh_token = request.data.get('refresh')
        if not refresh_token:
            return Response(
                {'detail': 'Refresh token is required.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            token = RefreshToken(refresh_token)
            token.blacklist()
        except TokenError:
            return Response(
                {'detail': 'Token is invalid or already blacklisted.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        return Response({'detail': 'Successfully logged out.'}, status=status.HTTP_200_OK)


# ─── Admin-only views ─────────────────────────────────────────────────────────

class AdminUserListView(generics.ListAPIView):
    queryset = CustomUser.objects.all().order_by('-date_joined')
    serializer_class = UserSerializer
    permission_classes = [IsAuthenticated, IsAdmin]


class AdminUserDetailView(generics.RetrieveUpdateDestroyAPIView):
    """
    GET    /admin/users/<pk>/  → retrieve (UserSerializer)
    PATCH  /admin/users/<pk>/  → partial update incl. optional password (AdminUpdateUserSerializer)
    PUT    /admin/users/<pk>/  → full update incl. optional password (AdminUpdateUserSerializer)
    DELETE /admin/users/<pk>/  → delete
    """
    queryset = CustomUser.objects.all()
    permission_classes = [IsAuthenticated, IsAdmin]

    def get_serializer_class(self):
        if self.request.method in ('PUT', 'PATCH'):
            return AdminUpdateUserSerializer
        return UserSerializer


class AdminCreateUserView(generics.CreateAPIView):
    """
    POST /admin/users/create/
    password is optional — a random one is auto-generated when omitted.
    """
    queryset = CustomUser.objects.all()
    serializer_class = AdminCreateUserSerializer
    permission_classes = [IsAuthenticated, IsAdmin]


class CustomerUserListView(generics.ListAPIView):
    """Returns only users with customer_admin or customer_user roles."""
    serializer_class = UserSerializer
    permission_classes = [IsAuthenticated, IsAdmin]

    def get_queryset(self):
        return CustomUser.objects.filter(
            role__in=[UserRole.CUSTOMER_ADMIN, UserRole.CUSTOMER_USER]
        ).order_by('first_name', 'last_name')


# ─── Guest permission views ───────────────────────────────────────────────────

class GuestPermissionView(APIView):
    """
    GET  /admin/users/<pk>/guest-permissions/
        → Returns the current list of GuestPermission rows for the guest.

    PUT  /admin/users/<pk>/guest-permissions/
        → Replaces ALL permissions for this guest with the submitted list.
        Payload: { "permissions": [ {"module": "dashboard"}, ... ] }

    Only accessible by admins. The target user must have role='guest'.
    """
    permission_classes = [IsAuthenticated, IsAdmin]

    def _get_guest_or_404(self, pk):
        try:
            user = CustomUser.objects.get(pk=pk, role=UserRole.GUEST)
        except CustomUser.DoesNotExist:
            return None
        return user

    def get(self, request, pk):
        guest = self._get_guest_or_404(pk)
        if guest is None:
            return Response(
                {'detail': 'Guest user not found.'},
                status=status.HTTP_404_NOT_FOUND,
            )
        perms = GuestPermission.objects.filter(guest=guest)
        return Response(GuestPermissionSerializer(perms, many=True).data)

    def put(self, request, pk):
        guest = self._get_guest_or_404(pk)
        if guest is None:
            return Response(
                {'detail': 'Guest user not found.'},
                status=status.HTTP_404_NOT_FOUND,
            )
        serializer = GuestPermissionBulkSerializer(data=request.data)
        if serializer.is_valid():
            updated_perms = serializer.save(guest=guest)
            return Response(
                GuestPermissionSerializer(updated_perms, many=True).data,
                status=status.HTTP_200_OK,
            )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)