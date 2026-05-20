from rest_framework.routers import DefaultRouter
from django.urls import path, include

from travel_planner.views import ProjectPlaceViewSet, TravelProjectViewSet

router = DefaultRouter()
router.register("projects", TravelProjectViewSet, basename="project")

project_place_list = ProjectPlaceViewSet.as_view({"get": "list", "post": "create"})
project_place_detail = ProjectPlaceViewSet.as_view(
    {"get": "retrieve", "patch": "partial_update"}
)

urlpatterns = [
    path("", include(router.urls)),
    path(
        "projects/<int:project_pk>/places/",
        project_place_list,
        name="project-place-list",
    ),
    path(
        "projects/<int:project_pk>/places/<int:pk>/",
        project_place_detail,
        name="project-place-detail",
    ),
]
