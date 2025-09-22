from django.urls import path, include
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from .views import (
    UserViewSet, CourseViewSet, ModuleViewSet,
    EnrollmentViewSet, SCORMTrackingViewSet, ComplianceRecordViewSet,RoleChoicesView, DepartmentListView, DepartmentViewSet
)
from .auth_views import RegisterView, LogoutView,CustomTokenObtainPairView

router=DefaultRouter()
router.register(r'users', UserViewSet)
router.register(r'courses', CourseViewSet)
router.register(r'modules', ModuleViewSet)
router.register(r'enrollments', EnrollmentViewSet)
router.register(r'scorm', SCORMTrackingViewSet)
router.register(r'compliance', ComplianceRecordViewSet)
router.register(r'departments', DepartmentViewSet)

urlpatterns = [
    # Auth endpoints
    path("auth/register/", RegisterView.as_view(), name="register"),
    path("auth/login/", CustomTokenObtainPairView.as_view(), name="login"),
    path("auth/refresh/", TokenRefreshView.as_view(), name="token_refresh"),
    path("auth/roles/", RoleChoicesView.as_view(), name="roles"),
    path("auth/departments/", DepartmentListView.as_view(), name="departments"),
    path("auth/logout/", LogoutView.as_view(), name="logout"),

    # API endpoints from ViewSets
    path("", include(router.urls)),
]