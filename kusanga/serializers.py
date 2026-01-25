from rest_framework import serializers
from django.contrib.auth import get_user_model
from .models import Course, Module, Enrollment, SCORMTracking, TrainingRecord, Department,ModuleProgress,CourseGroup, UserCourseGroup
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
User = get_user_model()

class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, required=True)

    class Meta:
        model = User
        fields = [
            "id","full_name", "username", "email", "password",
            "role", "department", "job_title", "employee_id"
        ]

    def create(self, validated_data):
        password = validated_data.pop("password")
        user = User(**validated_data)
        user.set_password(password)
        user.save()
        return user
    
class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model=User
        fields = ["id","full_name", "username", "email", "role", "department", "job_title", "employee_id"]


class ModuleSerializer(serializers.ModelSerializer):
    class Meta:
        model = Module
        fields = '__all__'


class CourseSerializer(serializers.ModelSerializer):
    modules = ModuleSerializer(many=True, read_only=True)
    class Meta:
        model=Course
        fields=["id", "title", "description", "course_type", "duration", "created_by", "created_at", "modules"]

# -------------------- ENROLLMENT --------------------
class EnrollmentSerializer(serializers.ModelSerializer):
    # read-only nested user details (for display)
    user_detail = serializers.SerializerMethodField(read_only=True)

    
    course_title = serializers.CharField(source="course.title", read_only=True)

    class Meta:
        model = Enrollment
        
        fields = [
            "id",
            "user",
            "course",
            "course_title",   
            "enrolled_at",
            "due_date",
            "completed",
            "user_detail",
        ]

    def get_user_detail(self, obj):
        u = obj.user
        return {
            "id": u.id,
            "full_name": getattr(u, "full_name", "") or u.username,
            "username": u.username,
            "email": u.email,
            "role": u.role,
        }

    
class ModuleProgressSerializer(serializers.ModelSerializer):
    class Meta:
        model = ModuleProgress
        fields = '__all__'

class SCORMTrackingSerializer(serializers.ModelSerializer):
    class Meta:
        model = SCORMTracking
        fields = ["id", "enrollment", "module", "lesson_status", "score_raw", "total_time", "suspend_data", "last_accessed"]

# -------------------- COMPLIANCE --------------------
class TrainingRecordSerializer(serializers.ModelSerializer):
    enrollment = EnrollmentSerializer(read_only=True)
    enrollment_id = serializers.PrimaryKeyRelatedField(
        queryset=Enrollment.objects.all(), source="enrollment", write_only=True
    )

    class Meta:
        model = TrainingRecord
        fields = ["id", "enrollment", "enrollment_id", "status", "achieved_on", "expires_on"]
class DepartmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Department
        fields = ["id", "name"]
class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    @classmethod
    def get_token(cls, user):
        # Generate token
        token = super().get_token(user)

        # Add custom claims
        token['username'] = user.username
        token['full_name'] = user.full_name
        token['role'] = user.role
        token['email'] = user.email

        return token

    def validate(self, attrs):
        data = super().validate(attrs)

        # Add extra response data
        data.update({
            "id": self.user.id,
            "username": self.user.username,
            "full_name": self.user.full_name,
            "role": self.user.role,
            "email": self.user.email,
        })

        return data
    
    # serializers.py
class CourseGroupSerializer(serializers.ModelSerializer):
    class Meta:
        model = CourseGroup
        fields = ["id", "name", "description", "created_by", "created_at", "courses"]


class UserCourseGroupSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserCourseGroup
        fields = ["id", "user", "group", "assigned_at", "due_date"]
