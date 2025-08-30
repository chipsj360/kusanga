from rest_framework import serializers
from django.contrib.auth import get_user_model
from .models import Course, Module, Enrollment, SCORMTracking, ComplianceRecord
User = get_user_model()

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model=User
        fields = ["id", "username", "email", "role", "department", "job_title", "employee_id"]