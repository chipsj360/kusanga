from django.db import models
from django.contrib.auth.models import AbstractUser
import zipfile, os
from django.conf import settings

class Department(models.Model):
     name=models.CharField(max_length=200,blank=False,null=False)

     def __str__(self):
         return self.name

class User(AbstractUser):
    ROLE_CHOICES = [
        ('student', 'Student'),
        ('trainer', 'Trainer'),
        ('admin', 'Admin'),
    ]
    id=models.AutoField(primary_key=True)
    full_name = models.CharField(max_length=255, blank=True, null=True)
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='student')
    department = models.ForeignKey(Department, on_delete=models.CASCADE, related_name="users",null=True,blank=True)
    job_title = models.CharField(max_length=100, blank=True, null=True)
    employee_id = models.CharField(max_length=20, unique=True, blank=True, null=True)

    def __str__(self):
        return self.username


#Course Content

class Course (models.Model):
    COURSE_TYPES= [
        ('scorm' , 'SCORM'),
        ('xapi', 'xAPI'),
        ('video', 'Video'),
        ('pdf', 'PDF'),
        ('text', 'Text'),
    ]

    RECORD_TYPES = [
        ('compliance', 'Compliance'),
        ('competence', 'Competence'),
    ]

    title=models.CharField(max_length=200)
    description=models.TextField(blank=True, null=True)
    course_type=models.CharField(max_length=20, choices=COURSE_TYPES)
    record_type = models.CharField(
        max_length=20,
        choices=RECORD_TYPES,
        default='compliance'
    )
    duration = models.IntegerField(help_text="Duration in minutes", blank=True, null=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name="created_courses")
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.title

class Module(models.Model):
    CONTENT_TYPES = [
        ('video', 'Video'),
        ('pdf', 'PDF'),
        ('scorm', 'SCORM'),
        ('xapi', 'xAPI'),
        ('text', 'Text'),
    ]
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name="modules")
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True, null=True)
    order = models.PositiveIntegerField(default=1)
    content_type = models.CharField(max_length=20, choices=CONTENT_TYPES,default='video')
    file = models.FileField(upload_to="modules/files/", blank=True, null=True)
    video_url = models.URLField(blank=True, null=True)
    text_content = models.TextField(blank=True, null=True)
    scorm_package = models.FileField(upload_to="modules/scorm/", blank=True, null=True)

    def __str__(self):
        return f"{self.course.title} - {self.title}"
    
    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)

        if self.content_type == "scorm" and self.scorm_package:
            zip_path = self.scorm_package.path
            extract_to = os.path.join(settings.MEDIA_ROOT, f"modules/scorm/{self.id}/")

            os.makedirs(extract_to, exist_ok=True)

            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                zip_ref.extractall(extract_to)

class Enrollment(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="enrollments")
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name="enrollments")
    enrolled_at = models.DateTimeField(auto_now_add=True)
    due_date = models.DateTimeField(blank=True, null=True)
    completed = models.BooleanField(default=False)

    class Meta:
        unique_together = ('user', 'course')

    def __str__(self):
        return f"{self.user.username} → {self.course.title}"


class ModuleProgress(models.Model):
    enrollment = models.ForeignKey(Enrollment, on_delete=models.CASCADE, related_name="module_progress")
    module = models.ForeignKey(Module, on_delete=models.CASCADE)
    status = models.CharField(max_length=50, choices=[
        ("not_started", "Not Started"),
        ("in_progress", "In Progress"),
        ("completed", "Completed"),
        ("failed", "Failed"),
    ], default="not_started")
    score = models.FloatField(blank=True, null=True)
    last_accessed = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('enrollment', 'module')

    def __str__(self):
        return f"{self.enrollment.user.username} - {self.module.title} ({self.status})"

# 4. SCORM Tracking (runtime data like cmi.core.* values)
class SCORMTracking(models.Model):
    enrollment = models.ForeignKey(Enrollment, on_delete=models.CASCADE, related_name="tracking")
    module = models.ForeignKey(Module, on_delete=models.CASCADE, related_name="tracking")
    lesson_status = models.CharField(max_length=50, default="not attempted")
    lesson_location = models.CharField(max_length=255, blank=True, null=True)
    score_raw = models.FloatField(blank=True, null=True)
    total_time = models.CharField(max_length=50, blank=True, null=True)
    suspend_data = models.TextField(blank=True, null=True)
    last_accessed = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('enrollment', 'module')

    def __str__(self):
        return f"{self.enrollment.user.username} - {self.module.title} ({self.lesson_status})"


class TrainingRecord(models.Model):
    TRAINING_STATUS_CHOICES = [
        ('compliant', 'Compliant'),
        ('non_compliant', 'Non-Compliant'),
        ('competent', 'Competent'),
        ('not_competent', 'Not Competent'),
    ]
    enrollment = models.OneToOneField(Enrollment, on_delete=models.CASCADE, related_name="training_record")
    status = models.CharField(max_length=50, choices=TRAINING_STATUS_CHOICES)
    achieved_on = models.DateTimeField(blank=True, null=True)
    expires_on = models.DateTimeField(blank=True, null=True)

    def __str__(self):
        return f"{self.enrollment.user.username} - {self.status}"
    

    # models.py
class CourseGroup(models.Model):
    name = models.CharField(max_length=200, unique=True)
    description = models.TextField(blank=True, null=True)
    created_by = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, related_name="created_course_groups"
    )
    created_at = models.DateTimeField(auto_now_add=True)

    # group contains many courses
    courses = models.ManyToManyField(Course, related_name="course_groups", blank=True)

    def __str__(self):
        return self.name


class UserCourseGroup(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="assigned_course_groups")
    group = models.ForeignKey(CourseGroup, on_delete=models.CASCADE, related_name="assigned_users")
    assigned_at = models.DateTimeField(auto_now_add=True)

    # optional group-level due date to apply to newly-created enrollments
    due_date = models.DateTimeField(blank=True, null=True)

    class Meta:
        unique_together = ("user", "group")

    def __str__(self):
        return f"{self.user.username} → {self.group.name}"
