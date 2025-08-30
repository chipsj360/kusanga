from rest_framework import serializers
from django.contrib.auth import get_user_model
from .models import Course, Module, Enrollment, SCORMTracking, ComplianceRecord
User = get_user_model()

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model=User
        fields = ["id", "username", "email", "role", "department", "job_title", "employee_id"]


class ModuleSerializer(serializers.ModelSerializer):
    class meta:
        model=Module
        fields = ["id", "title", "description", "order"]


class CourseSerializer(serializers.ModelSerializer):
    modules = ModuleSerializer(many=True, read_only=True)
    class meta:
        model=Course
        fields=["id", "title", "description", "course_type", "duration", "created_by", "created_at", "modules"]

# -------------------- ENROLLMENT --------------------
class EnrollmentSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)
    course = CourseSerializer(read_only=True)

    user_id = serializers.PrimaryKeyRelatedField(
        queryset=User.objects.all(), source="user", write_only=True
    )
    course_id = serializers.PrimaryKeyRelatedField(
        queryset=Course.objects.all(), source="course", write_only=True
    )
    class Meta:
        model = Enrollment
        fields = ["id", "user", "course", "user_id", "course_id", "enrolled_at", "due_date"]

class SCORMTrackingSerializer(serializers.ModelSerializer):
    class Meta:
        model = SCORMTracking
        fields = ["id", "enrollment", "module", "lesson_status", "score_raw", "total_time", "suspend_data", "last_accessed"]

# -------------------- COMPLIANCE --------------------
class ComplianceRecordSerializer(serializers.ModelSerializer):
    enrollment = EnrollmentSerializer(read_only=True)
    enrollment_id = serializers.PrimaryKeyRelatedField(
        queryset=Enrollment.objects.all(), source="enrollment", write_only=True
    )

    class Meta:
        model = ComplianceRecord
        fields = ["id", "enrollment", "enrollment_id", "status", "achieved_on", "expires_on"]