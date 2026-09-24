from rest_framework import generics, permissions
from .models import Device
from .serializers import DeviceSerializer


class DeviceListCreateView(generics.ListCreateAPIView):
    queryset = Device.objects.all().order_by("-created_at")
    serializer_class = DeviceSerializer
    permission_classes = [permissions.IsAuthenticated]


class DeviceDetailView(generics.RetrieveUpdateAPIView):
    queryset = Device.objects.all()
    serializer_class = DeviceSerializer
    permission_classes = [permissions.IsAuthenticated]
