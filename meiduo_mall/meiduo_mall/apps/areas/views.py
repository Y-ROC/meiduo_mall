from django.shortcuts import render
from rest_framework.generics import ListAPIView
from rest_framework_extensions.cache.mixins import CacheResponseMixin

from areas.models import Area
from areas.serializers import AreaSerializer


class AreaView(CacheResponseMixin, ListAPIView):
    queryset = Area.objects.filter(parent=None)
    serializer_class = AreaSerializer


class SubAreaView(CacheResponseMixin, ListAPIView):
    serializer_class = AreaSerializer

    def get_queryset(self):
        pk = self.kwargs['pk']
        return Area.objects.filter(parent_id=pk)
