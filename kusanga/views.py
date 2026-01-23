from django.shortcuts import render
from rest_framework import viewsets, permissions,filters
from django.contrib.auth import get_user_model
from .models import Course, Module, Enrollment, SCORMTracking, TrainingRecord, Department,ModuleProgress
from .serializers import (
    TrainingRecordSerializer, UserSerializer, CourseSerializer, ModuleSerializer,
    EnrollmentSerializer, SCORMTrackingSerializer, TrainingRecordSerializer, DepartmentSerializer,ModuleProgressSerializer
)
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import BasePermission
from rest_framework.permissions import BasePermission, SAFE_METHODS
User = get_user_model()



class IsTrainerOrAdmin(BasePermission):
    def has_permission(self, request, view):
        return request.user.role in ["trainer", "admin"]
    
class IsTrainerOrAdminOrReadOnly(BasePermission):
    """
    - Students: can only GET/HEAD/OPTIONS
    - Trainer/Admin: full access
    """
    def has_permission(self, request, view):
        if request.method in SAFE_METHODS:
            return request.user.is_authenticated
        return request.user.is_authenticated and request.user.role in ["trainer", "admin"]

class UserViewSet(viewsets.ModelViewSet):
  queryset=User.objects.all()
  serializer_class=UserSerializer
  permission_classes = [permissions.IsAuthenticated, IsTrainerOrAdmin]

class CourseViewSet(viewsets.ModelViewSet):
    queryset = Course.objects.all().order_by("-created_at")   # ✅ add this back
    serializer_class = CourseSerializer
    filter_backends = [filters.SearchFilter]
    search_fields = ["title", "description"]
    permission_classes = [permissions.IsAuthenticated, IsTrainerOrAdminOrReadOnly]

    def get_queryset(self):
        qs = super().get_queryset()
        user = self.request.user
        if user.role == "student":
            qs = qs.filter(enrollments__user=user).distinct()
        return qs


    

class ModuleViewSet(viewsets.ModelViewSet):
    queryset = Module.objects.all().order_by('order')
    serializer_class = ModuleSerializer
    filter_backends = [filters.SearchFilter]
    search_fields = ['title', 'description']
    permission_classes = [permissions.IsAuthenticated, IsTrainerOrAdminOrReadOnly]

    def get_queryset(self):
        qs = super().get_queryset()
        course_id = self.request.query_params.get('course')
        if course_id:
            qs = qs.filter(course_id=course_id)

        if self.request.user.role == "student":
            qs = qs.filter(course__enrollments__user=self.request.user).distinct()

        return qs


   

class EnrollmentViewSet(viewsets.ModelViewSet):
    queryset = Enrollment.objects.all()
    serializer_class = EnrollmentSerializer

    def get_queryset(self):
        user = self.request.user
        qs = super().get_queryset()

        # students only see their enrollments
        if user.role == "student":
            return qs.filter(user=user)

        return qs

    def get_permissions(self):
        # students can read only; trainer/admin can CRUD
        if self.request.method in SAFE_METHODS:
            return [permissions.IsAuthenticated()]
        return [permissions.IsAuthenticated(), IsTrainerOrAdminOrReadOnly()]

class ModuleProgressViewSet(viewsets.ModelViewSet):
    queryset = ModuleProgress.objects.all()
    serializer_class = ModuleProgressSerializer
# -------------------- SCORM TRACKING --------------------
class SCORMTrackingViewSet(viewsets.ModelViewSet):
    queryset = SCORMTracking.objects.all()
    serializer_class = SCORMTrackingSerializer
    permission_classes = [permissions.IsAuthenticated]

# -------------------- COMPLIANCE --------------------
class TrainingRecordViewSet(viewsets.ModelViewSet):
    queryset = TrainingRecord.objects.all()
    serializer_class = TrainingRecordSerializer
    permission_classes = [permissions.IsAuthenticated]

class DepartmentViewSet(viewsets.ModelViewSet):
    queryset=Department.objects.all()
    serializer_class=DepartmentSerializer
    
class RoleChoicesView(APIView):
    def get(self, request):
        roles = [{"value": choice[0], "label": choice[1]} for choice in User.ROLE_CHOICES]
        return Response(roles)
    
class CourseTypeView(APIView):
    def get(self, request):
        course_type = [{"value": choice[0], "label": choice[1]} for choice in Course. COURSE_TYPES]
        return Response(course_type)

class DepartmentListView(APIView):
    def get(self, request):
        departments = Department.objects.all().values("id", "name")
        return Response(departments)
    
def launch_scorm(request, module_id):
    module = Module.objects.get(id=module_id)
    launch_url = f"/media/modules/scorm/{module_id}/story.html"
    return render(request, "scorm_player.html", {"launch_url": launch_url})
