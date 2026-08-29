from django.shortcuts import render
from rest_framework import viewsets, permissions,filters, status
from django.contrib.auth import get_user_model
from .models import Course, Module, Enrollment, SCORMTracking, TrainingRecord, Department,ModuleProgress, CourseGroup, UserCourseGroup
from .serializers import (
    TrainingRecordSerializer, UserSerializer, CourseSerializer, ModuleSerializer,
    EnrollmentSerializer, SCORMTrackingSerializer, TrainingRecordSerializer, DepartmentSerializer,ModuleProgressSerializer,CourseGroupSerializer, UserCourseGroupSerializer
)
from django.db.models import Count, Q
from rest_framework.decorators import action
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import BasePermission
from rest_framework.permissions import BasePermission, SAFE_METHODS
from django.utils.dateparse import parse_datetime
from django.utils import timezone
from django.db import transaction
User = get_user_model()


class CurrentUserView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        return Response(UserSerializer(request.user).data)



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
    queryset = Course.objects.all().order_by("-created_at")
    serializer_class = CourseSerializer
    permission_classes = [permissions.IsAuthenticated, IsTrainerOrAdminOrReadOnly]

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)

    def perform_update(self, serializer):
        course = serializer.save()
        now = timezone.now()

        records = TrainingRecord.objects.filter(
            enrollment__course=course,
            achieved_on__isnull=False,
        )
        for record in records:
            record.expires_on = course.calculate_expiry_date(record.achieved_on)
            is_expired = record.expires_on and record.expires_on <= now

            if course.record_type == "compliance":
                record.status = "non_compliant" if is_expired else "compliant"
            elif course.record_type == "competence":
                record.status = "not_competent" if is_expired else "competent"

            record.save(update_fields=["expires_on", "status"])

    def get_queryset(self):
        qs = super().get_queryset()
        user = self.request.user

        if user.role == "student":
            qs = qs.filter(
                Q(course_groups__assigned_users__user=user) |   # via group
                Q(enrollments__user=user)                       # direct enrollment
            ).distinct()

        return qs



    

class ModuleViewSet(viewsets.ModelViewSet):
    queryset = Module.objects.all().order_by("order")
    serializer_class = ModuleSerializer
    permission_classes = [permissions.IsAuthenticated, IsTrainerOrAdminOrReadOnly]

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context["request"] = self.request
        return context


    def get_queryset(self):
        qs = super().get_queryset()
        user = self.request.user

        # ✅ Always filter by course if provided (fixes “all modules showing” bug)
        course_id = self.request.query_params.get("course")
        if course_id:
            qs = qs.filter(course_id=course_id)

        # ✅ Students: modules visible if course is direct-enrolled OR group-assigned
        if user.role == "student":
            qs = qs.filter(
                Q(course__enrollments__user=user) |                        # direct enrollment
                Q(course__course_groups__assigned_users__user=user)        # group enrollment
            ).distinct()

        # ✅ Trainer/Admin: no restriction
        return qs

    def _get_enrollment_for_user_and_course(self, user, course):
        return Enrollment.objects.filter(user=user, course=course).first()

    @action(detail=True, methods=["post"], permission_classes=[permissions.IsAuthenticated])
    def start(self, request, pk=None):
        module = self.get_object()
        user = request.user

        enrollment = self._get_enrollment_for_user_and_course(user, module.course)

        # ✅ Students must be enrolled
        if user.role == "student" and not enrollment:
            return Response({"detail": "You are not enrolled in this course."}, status=403)

        # ✅ Trainer/Admin can start even without enrollment (auto-create)
        if user.role in ["trainer", "admin"] and not enrollment:
            enrollment, _ = Enrollment.objects.get_or_create(user=user, course=module.course)

        mp, _ = ModuleProgress.objects.get_or_create(
            enrollment=enrollment,
            module=module,
            defaults={"status": "in_progress"},
        )

        if mp.status == "not_started":
            mp.status = "in_progress"
            mp.last_accessed = timezone.now()
            mp.save(update_fields=["status", "last_accessed"])

        return Response({"detail": "Module started", "status": mp.status}, status=200)




    @action(detail=True, methods=["post"], permission_classes=[permissions.IsAuthenticated])
    def complete(self, request, pk=None):
        module = self.get_object()
        user = request.user

        enrollment = self._get_enrollment_for_user_and_course(user, module.course)

        if user.role == "student" and not enrollment:
            return Response({"detail": "You are not enrolled in this course."}, status=403)

        if user.role in ["trainer", "admin"] and not enrollment:
            enrollment, _ = Enrollment.objects.get_or_create(user=user, course=module.course)

        # Enforce video completion rules
        if module.content_type == "video":
            watched_to_end = request.data.get("watched_to_end", False)
            final_position = request.data.get("final_position")
            duration = request.data.get("duration")
            seek_blocked = request.data.get("seek_blocked", False)

            try:
                final_position = float(final_position)
                duration = float(duration)
            except (TypeError, ValueError):
                return Response(
                    {"detail": "Invalid video tracking data."},
                    status=400
                )

            if not watched_to_end:
                return Response(
                    {"detail": "Video must be watched to the end before completion."},
                    status=400
                )

            if duration <= 0:
                return Response(
                    {"detail": "Invalid video duration."},
                    status=400
                )

            # Allow 1 second tolerance
            if final_position < duration - 1:
                return Response(
                    {"detail": "Video was not watched to the end."},
                    status=400
                )

        try:
            with transaction.atomic():
                mp, _ = ModuleProgress.objects.get_or_create(
                    enrollment=enrollment,
                    module=module,
                    defaults={"status": "completed"},
                )

                if mp.status != "completed":
                    mp.status = "completed"
                    mp.last_accessed = timezone.now()
                    mp.save(update_fields=["status", "last_accessed"])

                total_modules = Module.objects.filter(course=module.course).count()
                completed_modules = ModuleProgress.objects.filter(
                    enrollment=enrollment,
                    status="completed",
                    module__course=module.course
                ).count()

                training_record = None

                if total_modules > 0 and completed_modules == total_modules:
                    enrollment.completed = True
                    enrollment.save(update_fields=["completed"])

                    record_type = getattr(module.course, "record_type", None)

                    if record_type == "compliance":
                        training_status = "compliant"
                    elif record_type == "competence":
                        training_status = "competent"
                    else:
                        training_status = None

                    if training_status:
                        achieved_on = timezone.now()
                        training_record, _ = TrainingRecord.objects.update_or_create(
                            enrollment=enrollment,
                            defaults={
                                "status": training_status,
                                "achieved_on": achieved_on,
                                "expires_on": module.course.calculate_expiry_date(achieved_on),
                            }
                        )

            return Response(
                {
                    "detail": "Module completed",
                    "module_status": mp.status,
                    "course_completed": enrollment.completed,
                    "training_record_status": training_record.status if training_record else None,
                },
                status=200,
            )

        except Exception as e:
            return Response(
                {
                    "detail": "Error completing module",
                    "error": str(e),
                },
                status=500,
            )
                    
    @action(detail=True, methods=["post"], permission_classes=[permissions.IsAuthenticated])
    def scorm_progress(self, request, pk=None):
        module = self.get_object()
        user = request.user

        if module.content_type != "scorm":
            return Response({"detail": "This endpoint is only for SCORM modules."}, status=400)

        enrollment = self._get_enrollment_for_user_and_course(user, module.course)

        if user.role == "student" and not enrollment:
            return Response({"detail": "You are not enrolled in this course."}, status=403)

        if user.role in ["trainer", "admin"] and not enrollment:
            enrollment, _ = Enrollment.objects.get_or_create(user=user, course=module.course)

        lesson_status = request.data.get("lesson_status", "incomplete")
        lesson_location = request.data.get("lesson_location")
        score_raw = request.data.get("score_raw")
        total_time = request.data.get("total_time")
        suspend_data = request.data.get("suspend_data")

        # ✅ Parse/validate score_raw BEFORE it's used anywhere below
        try:
            score_value = float(score_raw) if score_raw not in [None, ""] else None
        except (TypeError, ValueError):
            score_value = None

        try:
            with transaction.atomic():
                tracking, _ = SCORMTracking.objects.update_or_create(
                    enrollment=enrollment,
                    module=module,
                    defaults={
                        "lesson_status": lesson_status,
                        "lesson_location": lesson_location,
                        "score_raw": score_value,
                        "total_time": total_time,
                        "suspend_data": suspend_data,
                    }
                )

                mp, _ = ModuleProgress.objects.get_or_create(
                    enrollment=enrollment,
                    module=module,
                    defaults={"status": "in_progress"},
                )

                if mp.status == "not_started":
                    mp.status = "in_progress"
                    mp.last_accessed = timezone.now()
                    mp.save(update_fields=["status", "last_accessed"])

                training_record = None

                # Complete when the learner PASSES the assessment, or when the
                # package reports plain "completed" (some SCORM publish settings
                # never send "passed", even after a passing score).
                lesson_status_normalized = str(lesson_status).lower()
                passed_assessment = lesson_status_normalized in ("passed", "completed")

                if passed_assessment:
                    if mp.status != "completed":
                        mp.status = "completed"
                        mp.last_accessed = timezone.now()
                        mp.save(update_fields=["status", "last_accessed"])

                    total_modules = Module.objects.filter(course=module.course).count()
                    completed_modules = ModuleProgress.objects.filter(
                        enrollment=enrollment,
                        status="completed",
                        module__course=module.course
                    ).count()

                    if total_modules > 0 and completed_modules == total_modules:
                        enrollment.completed = True
                        enrollment.save(update_fields=["completed"])

                        record_type = getattr(module.course, "record_type", None)
                        if record_type == "compliance":
                            training_status = "compliant"
                        elif record_type == "competence":
                            training_status = "competent"
                        else:
                            training_status = None

                        if training_status:
                            achieved_on = timezone.now()
                            training_record, _ = TrainingRecord.objects.update_or_create(
                                enrollment=enrollment,
                                defaults={
                                    "status": training_status,
                                    "achieved_on": achieved_on,
                                    "expires_on": module.course.calculate_expiry_date(achieved_on),
                                }
                            )

                return Response(
                    {
                        "detail": "SCORM progress saved",
                        "module_status": mp.status,
                        "lesson_status": tracking.lesson_status,
                        "lesson_location": tracking.lesson_location,
                        "score_raw": tracking.score_raw,
                        "course_completed": enrollment.completed,
                        "training_record_status": training_record.status if training_record else None,
                    },
                    status=200,
                )

        except Exception as e:
            return Response(
                {
                    "detail": "Error saving SCORM progress",
                    "error": str(e),
                },
                status=500,
            )

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
    queryset = TrainingRecord.objects.select_related("enrollment__user", "enrollment__course").all()
    serializer_class = TrainingRecordSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        qs = super().get_queryset()

        # students only see their own records
        if user.role == "student":
            qs = qs.filter(enrollment__user=user)

        records_without_expiry = qs.filter(
            expires_on__isnull=True,
            achieved_on__isnull=False,
            enrollment__course__expiry_months__isnull=False,
        )
        for record in records_without_expiry:
            record.expires_on = record.enrollment.course.calculate_expiry_date(
                record.achieved_on
            )
            record.save(update_fields=["expires_on"])

        expired = qs.filter(expires_on__isnull=False, expires_on__lte=timezone.now())
        expired.filter(enrollment__course__record_type="compliance").exclude(
            status="non_compliant"
        ).update(status="non_compliant")
        expired.filter(enrollment__course__record_type="competence").exclude(
            status="not_competent"
        ).update(status="not_competent")

        return qs.order_by("-achieved_on", "-id")

class DepartmentViewSet(viewsets.ModelViewSet):
    queryset = Department.objects.annotate(user_count=Count("users")).order_by("name")
    serializer_class = DepartmentSerializer
    permission_classes = [permissions.IsAuthenticated, IsTrainerOrAdmin]

    def destroy(self, request, *args, **kwargs):
        department = self.get_object()
        if department.users.exists():
            return Response(
                {"detail": "This department cannot be deleted while users are assigned to it."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        return super().destroy(request, *args, **kwargs)
    
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
    launch_url = f"/media/modules/scorm/{module_id}/index_lms.html"
    return render(request, "scorm_player.html", {
        "launch_url": launch_url,
        "module_id": module_id,
    })

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