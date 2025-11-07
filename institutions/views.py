from rest_framework.generics import ListAPIView
from .models import Institution
from users.permissions import IsInstitutuionAdmin, IsFaculty, IsHod, IsStudent
from common.views import InstitutionFilterMixin
from users.models import Profile
from .serializers import ProfileSerializer
# class AdminView(ListAPIView):
#     model=Institution
#     permission_classes=[IsFaculty]
#     def get_queryset(self):
#         return super().get_queryset()

class InstitutionStudentsAPIView(InstitutionFilterMixin, ListAPIView):
    model=Profile
    queryset=Profile.objects.all()
    permission_classes=[IsInstitutuionAdmin]
    serializer_class=ProfileSerializer
