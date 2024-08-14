from rest_framework import generics, permissions
from django.contrib.auth import get_user_model
from . import serializers
from .models import *

# class ListUserGeneric(generics.ListAPIView):
#     queryset = None
#     serializer_class = None
#
#     # tìm theo tên
#     def get_queryset(self):
#         query = self.queryset
#         kw = self.request.query_params.get('kw')
#         if kw:
#             query = query.filter(name__icontains=kw)
#         return query