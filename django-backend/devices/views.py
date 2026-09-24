from rest_framework import generics, permissions
from .models import Device
from .serializers import DeviceSerializer
from pilots.permissions import enforce_pilot_scoping, IsStaffOrPilotOwner


class DeviceListCreateView(generics.ListCreateAPIView):
    serializer_class = DeviceSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        qs = Device.objects.all().order_by("-created_at")
        return enforce_pilot_scoping(self.request, qs, pilot_field="pilot")


class DeviceDetailView(generics.RetrieveUpdateAPIView):
    queryset = Device.objects.all()
    serializer_class = DeviceSerializer
    permission_classes = [permissions.IsAuthenticated, IsStaffOrPilotOwner]
