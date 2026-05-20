from rest_framework import status, viewsets
from rest_framework.response import Response
from django.shortcuts import get_object_or_404

from .models import ProjectPlace, TravelProject
from .serializers import (
    ProjectPlaceAddSerializer,
    ProjectPlaceSerializer,
    ProjectPlaceUpdateSerializer,
    TravelProjectCreateSerializer,
    TravelProjectSerializer,
    TravelProjectUpdateSerializer,
)


class TravelProjectViewSet(viewsets.ModelViewSet):
    queryset = TravelProject.objects.prefetch_related('places').all()
    http_method_names = ['get', 'post', 'patch', 'delete']

    def get_serializer_class(self):
        if self.action == 'create':
            return TravelProjectCreateSerializer
        if self.action == 'partial_update':
            return TravelProjectUpdateSerializer
        return TravelProjectSerializer

    def destroy(self, request, *args, **kwargs):
        project = self.get_object()
        if project.places.filter(is_visited=True).exists():
            return Response(
                {'detail': 'Cannot delete a project that has visited places.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        project.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

    def partial_update(self, request, *args, **kwargs):
        project = self.get_object()
        serializer = TravelProjectUpdateSerializer(project, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(TravelProjectSerializer(project, context={'request': request}).data)


class ProjectPlaceViewSet(viewsets.ViewSet):

    def _get_project(self, project_pk):
        return get_object_or_404(TravelProject, pk=project_pk)

    def list(self, request, project_pk=None):
        project = self._get_project(project_pk)
        serializer = ProjectPlaceSerializer(project.places.all(), many=True)
        return Response(serializer.data)

    def retrieve(self, request, project_pk=None, pk=None):
        project = self._get_project(project_pk)
        place = get_object_or_404(ProjectPlace, pk=pk, project=project)
        return Response(ProjectPlaceSerializer(place).data)

    def create(self, request, project_pk=None):
        project = self._get_project(project_pk)
        serializer = ProjectPlaceAddSerializer(
            data=request.data,
            context={'project': project},
        )
        serializer.is_valid(raise_exception=True)
        place = serializer.save()
        return Response(ProjectPlaceSerializer(place).data, status=status.HTTP_201_CREATED)

    def partial_update(self, request, project_pk=None, pk=None):
        project = self._get_project(project_pk)
        place = get_object_or_404(ProjectPlace, pk=pk, project=project)
        serializer = ProjectPlaceUpdateSerializer(place, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(ProjectPlaceSerializer(place).data)
