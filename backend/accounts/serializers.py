from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from .models import CustomUser


class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)
        token['email'] = user.email
        token['role']  = user.role
        token['name']  = user.full_name
        return token


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model  = CustomUser
        fields = [
            'id', 'email', 'first_name', 'last_name', 'role',
            'company', 'phone', 'mfa_enabled', 'is_active', 'date_joined',
        ]
        read_only_fields = ['id', 'date_joined']


class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=8)

    class Meta:
        model  = CustomUser
        fields = ['email', 'password', 'first_name', 'last_name', 'role', 'company', 'phone']

    def create(self, validated_data):
        return CustomUser.objects.create_user(**validated_data)


class AdminCreateUserSerializer(serializers.ModelSerializer):
    """
    Used by AdminCreateUserView.
    - password is optional; a random one is generated when omitted.
    - role is writable so admins can assign any role at creation time.
    """
    password = serializers.CharField(write_only=True, min_length=8, required=False, allow_blank=True)

    class Meta:
        model  = CustomUser
        fields = ['email', 'password', 'first_name', 'last_name', 'role', 'company', 'phone']

    def create(self, validated_data):
        raw_password = validated_data.pop('password', None) or None
        user = CustomUser.objects.create_user(password=raw_password, **validated_data)
        return user


class AdminUpdateUserSerializer(serializers.ModelSerializer):
    """
    Used by AdminUserDetailView for PATCH / PUT.
    - password is optional; when supplied it is hashed and saved.
    - Allows updating role, is_active, and all profile fields.
    """
    password = serializers.CharField(write_only=True, min_length=8, required=False, allow_blank=True)

    class Meta:
        model  = CustomUser
        fields = [
            'email', 'password', 'first_name', 'last_name', 'role',
            'company', 'phone', 'is_active',
        ]

    def update(self, instance, validated_data):
        raw_password = validated_data.pop('password', None)
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        if raw_password:
            instance.set_password(raw_password)
        instance.save()
        return instance


class ChangePasswordSerializer(serializers.Serializer):
    old_password = serializers.CharField(write_only=True)
    new_password = serializers.CharField(write_only=True, min_length=8)