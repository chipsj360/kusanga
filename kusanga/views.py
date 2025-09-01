from django.shortcuts import render
from rest_framework import viewsets, permissions
from django.contrib.auth import get_user_model
from .models import Course, Module, Enrollment, SCORMTracking, ComplianceRecord
from .serializers import (
    UserSerializer, CourseSerializer, ModuleSerializer,
    EnrollmentSerializer, SCORMTrackingSerializer, ComplianceRecordSerializer
)

User = get_user_model()

class UserViewSet(viewsets.ModelViewSet):
  queryset=User.objects.all()
  serializer_class=UserSerializer
  permission_classes = [permissions.IsAuthenticated]

class CourseViewSet(viewsets.ModelViewSet):
    queryset = Course.objects.all()
    serializer_class = CourseSerializer
    permission_classes = [permissions.IsAuthenticated]

class ModuleViewSet(viewsets.ModelViewSet):
    queryset = Module.objects.all()
    serializer_class = ModuleSerializer
    permission_classes = [permissions.IsAuthenticated]

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
