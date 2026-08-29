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
    course_title = serializers.CharField(source="course.title", read_only=True)
    progress_status = serializers.SerializerMethodField()

    class Meta:
        model = Module
        fields = '__all__'

    def get_progress_status(self, obj):
        request = self.context.get("request")
        if not request or not request.user.is_authenticated:
            return "not_started"

        user = request.user
        enrollment = Enrollment.objects.filter(user=user, course=obj.course).first()
        if not enrollment:
            return "not_started"

        progress = ModuleProgress.objects.filter(
            enrollment=enrollment,
            module=obj
        ).first()

        return progress.status if progress else "not_started"

class CourseSerializer(serializers.ModelSerializer):
    modules = ModuleSerializer(many=True, read_only=True)
    class Meta:
        model=Course
        fields=["id", "title", "description", "course_type","record_type", "duration", "expiry_months", "created_by", "created_at", "modules"]
        read_only_fields = ["created_by", "created_at"]

    def validate_expiry_months(self, value):
        if value is None or value < 1:
            raise serializers.ValidationError("Expiry time frame must be at least 1 month.")
        return value

    def validate(self, attrs):
        if not self.instance and not attrs.get("expiry_months"):
            raise serializers.ValidationError({
                "expiry_months": "Expiry time frame is required."
            })
        return attrs

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
        fields = [
            "id",
            "enrollment",
            "module",
            "lesson_status",
            "lesson_location",
            "score_raw",
            "total_time",
            "suspend_data",
            "last_accessed",
        ]

# -------------------- COMPLIANCE --------------------
class TrainingRecordSerializer(serializers.ModelSerializer):
    enrollment = EnrollmentSerializer(read_only=True)
    enrollment_id = serializers.PrimaryKeyRelatedField(
        queryset=Enrollment.objects.all(),
        source="enrollment",
        write_only=True
    )

    user_id = serializers.IntegerField(source="enrollment.user.id", read_only=True)
    username = serializers.CharField(source="enrollment.user.username", read_only=True)
    full_name = serializers.CharField(source="enrollment.user.full_name", read_only=True)
    course_id = serializers.IntegerField(source="enrollment.course.id", read_only=True)
    course_title = serializers.CharField(source="enrollment.course.title", read_only=True)
    course_record_type = serializers.CharField(source="enrollment.course.record_type", read_only=True)

    class Meta:
        model = TrainingRecord
        fields = [
            "id",
            "enrollment",
            "enrollment_id",
            "user_id",
            "username",
            "full_name",
            "course_id",
            "course_title",
            "course_record_type",
            "status",
            "achieved_on",
            "expires_on",
        ]
class DepartmentSerializer(serializers.ModelSerializer):
    user_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = Department
        fields = ["id", "name", "user_count"]

    def validate_name(self, value):
        name = value.strip()
        if not name:
            raise serializers.ValidationError("Department name is required.")

        duplicate = Department.objects.filter(name__iexact=name)
        if self.instance:
            duplicate = duplicate.exclude(pk=self.instance.pk)
        if duplicate.exists():
            raise serializers.ValidationError("A department with this name already exists.")

        return name
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