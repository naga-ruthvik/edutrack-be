from rest_framework.generics import ListAPIView
from .models import Institution, Department
from users.permissions import IsInstitutuionAdmin, IsFaculty, IsHod, IsStudent
from common.views import InstitutionFilterMixin
from users.models import Profile
from .serializers import ProfileSerializer
from rest_framework.permissions import IsAuthenticated
from rest_framework.decorators import api_view
from rest_framework.response import Response
from django.http import FileResponse
from users.models import User, Profile
from utils.generate_credentials import generate_usename_password
# class AdminView(ListAPIView):
#     model=Institution
#     permission_classes=[IsFaculty]
#     def get_queryset(self):
#         return super().get_queryset()

class InstitutionStudentsAPIView(InstitutionFilterMixin, ListAPIView):
    """listing all students present in a institute"""
    model=Profile
    queryset=Profile.objects.all()
    permission_classes=[IsAuthenticated,IsInstitutuionAdmin]
    serializer_class=ProfileSerializer

    # filter only students
    def get_queryset(self):
        queryset=Profile.objects.filter(role='STUDENT')
        return queryset

@api_view(['POST'])
def create_profiles(request):
    """creating students of a institue"""

    if request.method=='POST':
        # get excel file from request body
        input_file=request.data.get('file')
        role=request.data.get('role').upper()
        college_code=request.data.get('body')

        if not excel_file:
            return Response({"error": "Upload a file"}, status=400)
        
        ################### logic to add students to db #####################
        df,updated_file_obj=generate_usename_password(input_file)
        # get institute user belongs to
        institution_id=request.user.institution

        # mapping all the departments with its ids of the institute
        department_map={}
        departments=Department.filter(institution=institution_id)
        for department in departments:
            department_map[department.name]=department.id

        # iteration on each row to add the profiles to db
        for _, row in df.iterrows():
            department=row["Department"]
        # Create User
            user = User.objects.create_user(
                username=row["Username"],
                email=row["Email"],
                first_name=row["First Name"],
                last_name=row["last Name"],
                is_active=True,
            )
            user.set_password(row["Password"])   # HASH PASSWORD
            user.save()
            # create userprofile
            Profile.objects.create(
                user=user,
                first_name=row["First Name"],
                last_name=row["last Name"],
                rollnumber=row["Roll Number"],
                department_id=department_map[row["Department"]],
                institution_id=institution_id,
                role=role
            )
        if not updated_file_obj:
            return Response({"error": "Could not generate file"}, status=500)

        return FileResponse(
            updated_file_obj,
            as_attachment=True,
            filename="credentials.xlsx"
        )
            