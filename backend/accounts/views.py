# accounts/views.py

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
from company_master.models import Company


# ─── Custom permissions ───────────────────────────────────────────────────────

class IsAdmin(BasePermission):
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
    queryset = CustomUser.objects.all()
    permission_classes = [IsAuthenticated, IsAdmin]

    def get_serializer_class(self):
        if self.request.method in ('PUT', 'PATCH'):
            return AdminUpdateUserSerializer
        return UserSerializer

    def destroy(self, request, *args, **kwargs):
        user = self.get_object()

        # Prevent admins from deleting themselves
        if user.pk == request.user.pk:
            return Response(
                {'detail': 'You cannot delete your own account.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        from django.db import transaction

        with transaction.atomic():
            # ── groups app ────────────────────────────────────────────────────
            # GroupMember rows referencing this user (non-CASCADE FK: user_id)
            try:
                from groups.models import GroupMember
                GroupMember.objects.filter(user=user).delete()
            except ImportError:
                pass

            # ── projects app ──────────────────────────────────────────────────
            # ProjectMember rows (non-CASCADE FK: user_id)
            try:
                from projects.models import ProjectMember
                ProjectMember.objects.filter(user=user).delete()
            except ImportError:
                pass

            # ── milestones app ────────────────────────────────────────────────
            # SignOff.signed_by is SET_NULL in the model — null it out explicitly
            # to avoid any deferred-constraint timing issues.
            try:
                from milestones.models import SignOff
                SignOff.objects.filter(signed_by=user).update(signed_by=None)
            except ImportError:
                pass

            # Milestone.owner is also SET_NULL — same treatment.
            try:
                from milestones.models import Milestone
                Milestone.objects.filter(owner=user).update(owner=None)
            except ImportError:
                pass

            # ── extend here as needed ─────────────────────────────────────────
            # Any other table with a non-CASCADE / non-SET_NULL FK to CustomUser
            # must be handled here before user.delete() or you'll get another
            # IntegrityError. Pattern:
            #   SomeModel.objects.filter(user=user).delete()   # for owned rows
            #   SomeModel.objects.filter(user=user).update(user=None)  # for nullable FKs

            user.delete()

        return Response(status=status.HTTP_204_NO_CONTENT)


class AdminCreateUserView(generics.CreateAPIView):
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
    permission_classes = [IsAuthenticated, IsAdmin]

    def _get_guest_or_404(self, pk):
        try:
            return CustomUser.objects.get(pk=pk, role=UserRole.GUEST)
        except CustomUser.DoesNotExist:
            return None

    def get(self, request, pk):
        guest = self._get_guest_or_404(pk)
        if guest is None:
            return Response({'detail': 'Guest user not found.'}, status=status.HTTP_404_NOT_FOUND)
        perms = GuestPermission.objects.filter(guest=guest)
        return Response(GuestPermissionSerializer(perms, many=True).data)

    def put(self, request, pk):
        guest = self._get_guest_or_404(pk)
        if guest is None:
            return Response({'detail': 'Guest user not found.'}, status=status.HTTP_404_NOT_FOUND)
        serializer = GuestPermissionBulkSerializer(data=request.data)
        if serializer.is_valid():
            updated_perms = serializer.save(guest=guest)
            return Response(
                GuestPermissionSerializer(updated_perms, many=True).data,
                status=status.HTTP_200_OK,
            )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


# ─── Users (customer_admin / customer_user) filtered by company ───────────────
#
# GET /auth/admin/users-by-company/?company_id=<id>
#
# CustomUser.company is a CharField storing the company name string.
# We resolve the name from company_master.Company and filter users by it.
# Returns a lightweight list: [ {id, email, first_name, last_name, role}, … ]

class UsersByCompanyView(APIView):
    permission_classes = [IsAuthenticated, IsAdmin]

    def get(self, request):
        company_id = request.query_params.get('company_id')
        if not company_id:
            return Response(
                {'detail': 'company_id query parameter is required.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            company = Company.objects.get(pk=int(company_id))
        except (Company.DoesNotExist, ValueError, TypeError):
            return Response(
                {'detail': 'Company not found.'},
                status=status.HTTP_404_NOT_FOUND,
            )

        # Match users whose company CharField equals the company's name
        users = CustomUser.objects.filter(
            company__iexact=company.company_name,
            role__in=[UserRole.CUSTOMER_ADMIN, UserRole.CUSTOMER_USER],
            is_active=True,
        ).order_by('first_name', 'last_name')

        data = [
            {
                'id':         u.id,
                'email':      u.email,
                'first_name': u.first_name,
                'last_name':  u.last_name,
                'role':       u.role,
            }
            for u in users
        ]
        return Response(data)