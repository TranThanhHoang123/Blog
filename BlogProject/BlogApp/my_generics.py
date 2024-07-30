from rest_framework import generics, permissions
from django.contrib.auth import get_user_model
from . import serializers
from .models import *