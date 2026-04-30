# accounts/urls.py
from django.urls import path
from .views import (
    LoginView,
    RegisterView,
    ProfileView,
    ChangePasswordView,
    LogoutView,
    AdminUserListView,
    AdminUserDetailView,
    AdminCreateUserView,
    CustomerUserListView,
)

urlpatterns = [
    path('login/',           LoginView.as_view(),           name='login'),
    path('register/',        RegisterView.as_view(),         name='register'),
    path('profile/',         ProfileView.as_view(),          name='profile'),
    path('change-password/', ChangePasswordView.as_view(),   name='change-password'),
    path('logout/',          LogoutView.as_view(),           name='logout'),

    # Admin
    path('admin/users/',              AdminUserListView.as_view(),    name='admin-user-list'),
    path('admin/users/create/',       AdminCreateUserView.as_view(),  name='admin-user-create'),
    path('admin/users/<int:pk>/',     AdminUserDetailView.as_view(),  name='admin-user-detail'),
    path('admin/customer-users/',     CustomerUserListView.as_view(), name='admin-customer-user-list'),
]