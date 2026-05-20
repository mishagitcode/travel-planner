from rest_framework import serializers

from travel_planner.models import ProjectPlace, TravelProject
from travel_planner.services import fetch_place_from_api


class ProjectPlaceSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProjectPlace
        fields = [
            "id",
            "external_id",
            "name",
            "notes",
            "is_visited",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "name", "created_at", "updated_at"]


class ProjectPlaceAddSerializer(serializers.Serializer):
    external_id = serializers.CharField()

    def validate_external_id(self, value):
        project = self.context["project"]
        if project.places.filter(external_id=value).exists():
            raise serializers.ValidationError("This place is already in the project.")
        if project.places.count() >= 10:
            raise serializers.ValidationError(
                "A project cannot have more than 10 places."
            )
        place_data = fetch_place_from_api(value)
        if place_data is None:
            raise serializers.ValidationError("Place not found in the external API.")
        self._place_data = place_data
        return value

    def create(self, validated_data):
        return ProjectPlace.objects.create(
            project=self.context["project"],
            external_id=validated_data["external_id"],
            name=self._place_data["name"],
        )


class ProjectPlaceUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProjectPlace
        fields = ["notes", "is_visited"]


class PlaceExternalIdSerializer(serializers.Serializer):
    external_id = serializers.CharField()


class TravelProjectSerializer(serializers.ModelSerializer):
    places = ProjectPlaceSerializer(many=True, read_only=True)

    class Meta:
        model = TravelProject
        fields = [
            "id",
            "name",
            "description",
            "start_date",
            "is_completed",
            "places",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "is_completed", "created_at", "updated_at"]


class TravelProjectCreateSerializer(serializers.ModelSerializer):
    place_ids = PlaceExternalIdSerializer(
        many=True, write_only=True, required=False, default=list
    )

    class Meta:
        model = TravelProject
        fields = ["id", "name", "description", "start_date", "place_ids"]
        read_only_fields = ["id"]

    def validate_place_ids(self, value):
        if len(value) > 10:
            raise serializers.ValidationError(
                "A project cannot have more than 10 places."
            )
        seen = set()
        resolved = []
        for item in value:
            ext_id = item["external_id"]
            if ext_id in seen:
                raise serializers.ValidationError(f"Duplicate external_id: {ext_id}.")
            seen.add(ext_id)
            place_data = fetch_place_from_api(ext_id)
            if place_data is None:
                raise serializers.ValidationError(
                    f'Place "{ext_id}" not found in the external API.'
                )
            resolved.append({"external_id": ext_id, "name": place_data["name"]})
        return resolved

    def create(self, validated_data):
        place_ids = validated_data.pop("place_ids", [])
        project = TravelProject.objects.create(**validated_data)
        ProjectPlace.objects.bulk_create(
            [ProjectPlace(project=project, **place) for place in place_ids]
        )
        return project

    def to_representation(self, instance):
        return TravelProjectSerializer(instance, context=self.context).data


class TravelProjectUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = TravelProject
        fields = ["name", "description", "start_date"]
