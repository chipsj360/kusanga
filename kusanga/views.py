from django.shortcuts import render
from rest_framework import viewsets, permissions
from django.contrib.auth import get_user_model
from .models import Course, Module, Enrollment, SCORMTracking, ComplianceRecord, Department
from .serializers import (
    UserSerializer, CourseSerializer, ModuleSerializer,
    EnrollmentSerializer, SCORMTrackingSerializer, ComplianceRecordSerializer, DepartmentSerializer
)
from rest_framework.views import APIView
from rest_framework.response import Response

User = get_user_model()

class UserViewSet(viewsets.ModelViewSet):
  queryset=User.objects.all()
  serializer_class=UserSerializer
  permission_classes = [permissions.IsAuthenticated]

class CourseViewSet(viewsets.ModelViewSet):
    queryset = Course.objects.all()
    serializer_class = CourseSerializer
    

class ModuleViewSet(viewsets.ModelViewSet):
    queryset = Module.objects.all()
    serializer_class = ModuleSerializer
   

# -------------------- ENROLLMENT --------------------
class EnrollmentViewSet(viewsets.ModelViewSet):
    queryset = Enrollment.objects.all()
    serializer_class = EnrollmentSerializer
    permission_classes = [permissions.IsAuthenticated]

# -------------------- SCORM TRACKING --------------------
class SCORMTrackingViewSet(viewsets.ModelViewSet):
    queryset = SCORMTracking.objects.all()
    serializer_class = SCORMTrackingSerializer
    permission_classes = [permissions.IsAuthenticated]

# -------------------- COMPLIANCE --------------------
class ComplianceRecordViewSet(viewsets.ModelViewSet):
    queryset = ComplianceRecord.objects.all()
    serializer_class = ComplianceRecordSerializer
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