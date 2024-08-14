from django.urls import path, include
from rest_framework import routers
from .views import CustomTokenView, custom_refresh_token
from . import views
router = routers.DefaultRouter()
router.register(r'user', views.UserViewSet, basename='user')  # Specify the basename here
router.register(r'blog', views.BlogViewSet, basename='blog')  # Specify the basename here
router.register(r'comment', views.CommentViewSet, basename='comment')  # Specify the basename here
router.register(r'company', views.CompanyViewSet, basename='company')  # Specify the basename here
router.register(r'recruitment', views.RecruitmentViewSet, basename='recruitment')  # Specify the basename here
router.register(r'job-application', views.JobApplicationViewSet, basename='job-application')  # Specify the basename here
router.register(r'password', views.ChangePasswordViewSet, basename='password')  # Specify the basename here

urlpatterns = [
    path('', include(router.urls)),
    path('o/token/', CustomTokenView.as_view(), name='token'),
    path('o/token/refresh/', custom_refresh_token, name='token_refresh'),
]