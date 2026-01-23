from django.shortcuts import render
from rest_framework import viewsets, permissions,filters, status
from django.contrib.auth import get_user_model
from .models import Course, Module, Enrollment, SCORMTracking, TrainingRecord, Department,ModuleProgress, CourseGroup, UserCourseGroup
from .serializers import (
    TrainingRecordSerializer, UserSerializer, CourseSerializer, ModuleSerializer,
    EnrollmentSerializer, SCORMTrackingSerializer, TrainingRecordSerializer, DepartmentSerializer,ModuleProgressSerializer,CourseGroupSerializer, UserCourseGroupSerializer
)
from rest_framework.decorators import action
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import BasePermission
from rest_framework.permissions import BasePermission, SAFE_METHODS
from django.utils.dateparse import parse_datetime
User = get_user_model()



class IsTrainerOrAdmin(BasePermission):
    def has_permission(self, request, view):
        return request.user.role in ["trainer", "admin"]
    
class IsTrainerOrAdminOnly(BasePermission):
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.role in ["trainer", "admin"]


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
    queryset = Enrollment.objects.select_related("user", "course").all()
    serializer_class = EnrollmentSerializer

    def get_queryset(self):
        user = self.request.user
        qs = super().get_queryset()

        # allow filtering by course
        course_id = self.request.query_params.get("course")
        if course_id:
            qs = qs.filter(course_id=course_id)

        # students only see their own enrollments
        if user.role == "student":
            qs = qs.filter(user=user)

        return qs

    def get_permissions(self):
        if self.request.method in SAFE_METHODS:
            return [permissions.IsAuthenticated()]
        return [permissions.IsAuthenticated(), IsTrainerOrAdminOnly()]


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

class CourseGroupViewSet(viewsets.ModelViewSet):
    queryset = CourseGroup.objects.all().order_by("-created_at")
    serializer_class = CourseGroupSerializer
    permission_classes = [permissions.IsAuthenticated, IsTrainerOrAdmin]

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)

    @action(detail=True, methods=["post"], permission_classes=[permissions.IsAuthenticated, IsTrainerOrAdmin])
    def assign(self, request, pk=None):
        """
        POST /api/course-groups/<id>/assign/
        Body:
        {
          "user_ids": [1,2,3],
          "due_date": "2026-02-01T00:00:00Z"   (optional)
        }
        Effect:
        - links users to group (UserCourseGroup)
        - creates Enrollment rows for all courses in group (idempotent)
        """
        group = self.get_object()
        user_ids = request.data.get("user_ids", [])
        due_date_raw = request.data.get("due_date")

        if not isinstance(user_ids, list) or not user_ids:
            return Response({"detail": "user_ids must be a non-empty list"}, status=400)

        due_date = parse_datetime(due_date_raw) if due_date_raw else None
        courses = list(group.courses.all())

        created_links = 0
        created_enrollments = 0

        for uid in user_ids:
            # link user to group (idempotent)
            link, link_created = UserCourseGroup.objects.get_or_create(
                user_id=uid, group=group, defaults={"due_date": due_date}
            )
            if link_created:
                created_links += 1
            elif due_date is not None and link.due_date != due_date:
                link.due_date = due_date
                link.save(update_fields=["due_date"])

            # create enrollments for all courses in group (idempotent)
            for c in courses:
                enr, enr_created = Enrollment.objects.get_or_create(
                    user_id=uid,
                    course=c,
                    defaults={"due_date": due_date, "completed": False},
                )
                if enr_created:
                    created_enrollments += 1

        return Response(
            {
                "group_id": group.id,
                "created_group_links": created_links,
                "created_enrollments": created_enrollments,
            },
            status=status.HTTP_201_CREATED,
        )

    @action(detail=True, methods=["post"], permission_classes=[permissions.IsAuthenticated, IsTrainerOrAdmin])
    def unassign(self, request, pk=None):
        """
        POST /api/course-groups/<id>/unassign/
        Body:
        { "user_id": 5, "remove_enrollments": false }

        Default behavior keeps enrollments (preserves progress).
        If remove_enrollments=true, deletes enrollments for group's courses.
        """
        group = self.get_object()
        user_id = request.data.get("user_id")
        remove_enrollments = bool(request.data.get("remove_enrollments", False))

        if not user_id:
            return Response({"detail": "user_id is required"}, status=400)

        UserCourseGroup.objects.filter(user_id=user_id, group=group).delete()

        removed = 0
        if remove_enrollments:
            course_ids = list(group.courses.values_list("id", flat=True))
            removed = Enrollment.objects.filter(user_id=user_id, course_id__in=course_ids).delete()[0]

        return Response({"detail": "unassigned", "removed_enrollments": removed})
    
class UserCourseGroupViewSet(viewsets.ModelViewSet):
    queryset = UserCourseGroup.objects.select_related("user", "group").all()
    serializer_class = UserCourseGroupSerializer
    permission_classes = [permissions.IsAuthenticated, IsTrainerOrAdmin]
