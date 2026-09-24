from rest_framework import generics, permissions
from .models import Pilot
from .serializers import PilotSerializer
from .permissions import IsStaffOrPilotOwner, get_user_pilot


class PilotListCreateView(generics.ListCreateAPIView):
    serializer_class = PilotSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        qs = Pilot.objects.all().order_by("pilot_code")
        if self.request.user.is_staff or self.request.user.is_superuser:
            return qs
        pilot = get_user_pilot(self.request.user)
        if pilot is not None:
            return qs.filter(id=pilot.id)
        return qs


class PilotDetailView(generics.RetrieveUpdateAPIView):
    queryset = Pilot.objects.all()
    serializer_class = PilotSerializer
    permission_classes = [permissions.IsAuthenticated, IsStaffOrPilotOwner]
