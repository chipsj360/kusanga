from django.urls import path, include
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from .views import (
    CourseGroupViewSet, UserCourseGroupViewSet, UserViewSet, CourseViewSet, ModuleViewSet,
    EnrollmentViewSet, SCORMTrackingViewSet, TrainingRecordViewSet,RoleChoicesView, DepartmentListView, DepartmentViewSet,CourseTypeView,ModuleProgressViewSet,launch_scorm, CurrentUserView
)
from .auth_views import RegisterView, LogoutView,CustomTokenObtainPairView

router=DefaultRouter()
router.register(r'users', UserViewSet)
router.register(r'courses', CourseViewSet)
router.register(r'modules', ModuleViewSet)
router.register(r'enrollments', EnrollmentViewSet)
router.register(r'scorm', SCORMTrackingViewSet)
router.register(r'training-records', TrainingRecordViewSet)
router.register(r'departments', DepartmentViewSet)
router.register(r'progress', ModuleProgressViewSet)
router.register(r'course-groups', CourseGroupViewSet)
router.register(r'user-course-groups', UserCourseGroupViewSet)


urlpatterns = [
    # Auth endpoints
    path("auth/register/", RegisterView.as_view(), name="register"),
    path("auth/login/", CustomTokenObtainPairView.as_view(), name="login"),
    path("auth/user/", CurrentUserView.as_view(), name="current-user"),
    path("auth/refresh/", TokenRefreshView.as_view(), name="token_refresh"),
    path("auth/roles/", RoleChoicesView.as_view(), name="roles"),
    path("auth/departments/", DepartmentListView.as_view(), name="departments"),
    path("auth/logout/", LogoutView.as_view(), name="logout"),
    path("scorm/launch/<int:module_id>/", launch_scorm),

    #Course endpoints
    path("course-types/", CourseTypeView.as_view(), name="course-types"),
    # API endpoints from ViewSets
    path("", include(router.urls)),
]