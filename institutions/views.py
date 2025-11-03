from rest_framework.generics import ListAPIView
from .models import Institution
from users.permissions import IsInstitutuionAdmin, IsFaculty, IsHod, IsStudent


class AdminView(ListAPIView):
    model=Institution
    permission_classes=[IsFaculty]
    def get_queryset(self):
        return super().get_queryset()