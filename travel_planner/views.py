from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters, status, viewsets
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.shortcuts import get_object_or_404

from .filters import ProjectPlaceFilterSet, TravelProjectFilterSet
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
    permission_classes = [IsAuthenticated]
    http_method_names = ['get', 'post', 'patch', 'delete']
    filterset_class = TravelProjectFilterSet
    search_fields = ['name', 'description']
    ordering_fields = ['name', 'start_date', 'created_at']
    ordering = ['-created_at']

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


class ProjectPlaceViewSet(viewsets.GenericViewSet):
    serializer_class = ProjectPlaceSerializer
    permission_classes = [IsAuthenticated]
    filterset_class = ProjectPlaceFilterSet
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    ordering_fields = ['created_at', 'is_visited']
    ordering = ['created_at']

    def get_queryset(self):
        if getattr(self, 'swagger_fake_view', False):
            return ProjectPlace.objects.none()
        get_object_or_404(TravelProject, pk=self.kwargs['project_pk'])
        return ProjectPlace.objects.filter(project_id=self.kwargs['project_pk'])

    def list(self, request, project_pk=None):
        queryset = self.filter_queryset(self.get_queryset())
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        return Response(self.get_serializer(queryset, many=True).data)

    def retrieve(self, request, project_pk=None, pk=None):
        place = get_object_or_404(self.get_queryset(), pk=pk)
        return Response(self.get_serializer(place).data)

    def create(self, request, project_pk=None):
        project = get_object_or_404(TravelProject, pk=project_pk)
        serializer = ProjectPlaceAddSerializer(
            data=request.data,
            context={'project': project},
        )
        serializer.is_valid(raise_exception=True)
        place = serializer.save()
        return Response(self.get_serializer(place).data, status=status.HTTP_201_CREATED)

    def partial_update(self, request, project_pk=None, pk=None):
        place = get_object_or_404(self.get_queryset(), pk=pk)
        serializer = ProjectPlaceUpdateSerializer(place, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(self.get_serializer(place).data)
