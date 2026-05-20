import django_filters

from .models import ProjectPlace, TravelProject


class TravelProjectFilterSet(django_filters.FilterSet):
    start_date_after = django_filters.DateFilter(field_name='start_date', lookup_expr='gte')
    start_date_before = django_filters.DateFilter(field_name='start_date', lookup_expr='lte')

    class Meta:
        model = TravelProject
        fields = ['is_completed', 'start_date_after', 'start_date_before']


class ProjectPlaceFilterSet(django_filters.FilterSet):
    class Meta:
        model = ProjectPlace
        fields = ['is_visited']
