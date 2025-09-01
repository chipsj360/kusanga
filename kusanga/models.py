from django.db import models
from django.contrib.auth.models import AbstractUser

class Department(models.Model):
     name=models.CharField(max_length=200,blank=False,null=False)

     def __str__(self):
         return self.name

class User(AbstractUser):
    ROLE_CHOICES = [
        ('employee', 'Employee'),
        ('trainer', 'Trainer'),
        ('admin', 'Admin'),
    ]

    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='employee')
    department = models.ForeignKey(Department, on_delete=models.CASCADE, related_name="users")
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
    title=models.CharField(max_length=200)
    description=models.TextField(blank=True, null=True)
    course_type=models.CharField(max_length=20, choices=COURSE_TYPES)
    duration = models.IntegerField(help_text="Duration in minutes", blank=True, null=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name="created_courses")
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.title

class Module(models.Model):
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name="modules")
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True, null=True)
    order = models.PositiveIntegerField(default=1)

    def __str__(self):
        return f"{self.course.title} - {self.title}"
    

    # 3. Enrollment (user assigned to course)
class Enrollment(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="enrollments")
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name="enrollments")
    enrolled_at = models.DateTimeField(auto_now_add=True)
    due_date = models.DateTimeField(blank=True, null=True)

    class Meta:
        unique_together = ('user', 'course')

    def __str__(self):
        return f"{self.user.username} → {self.course.title}"


# 4. SCORM Tracking (runtime data like cmi.core.* values)
class SCORMTracking(models.Model):
    enrollment = models.ForeignKey(Enrollment, on_delete=models.CASCADE, related_name="tracking")
    module = models.ForeignKey(Module, on_delete=models.CASCADE, related_name="tracking")
    lesson_status = models.CharField(max_length=50, default="not attempted")  # completed/passed/failed/incomplete
    score_raw = models.FloatField(blank=True, null=True)
    total_time = models.CharField(max_length=50, blank=True, null=True)  # SCORM time format (HH:MM:SS)
    suspend_data = models.TextField(blank=True, null=True)  # SCORM suspend_data (resume info)
    last_accessed = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('enrollment', 'module')

    def __str__(self):
        return f"{self.enrollment.user.username} - {self.module.title} ({self.lesson_status})"


# 5. Compliance Record (final compliance status)
class ComplianceRecord(models.Model):
    enrollment = models.OneToOneField(Enrollment, on_delete=models.CASCADE, related_name="compliance")
    status = models.CharField(max_length=50, choices=[("Compliant", "Compliant"), ("Not Compliant", "Not Compliant")])
    achieved_on = models.DateTimeField(blank=True, null=True)
    expires_on = models.DateTimeField(blank=True, null=True)

    def __str__(self):
        return f"{self.enrollment.user.username} - {self.status}"