from rest_framework import serializers

from tracking.models import (
    CustomField,
    CustomFieldEnumeration,
    CustomFieldTracker,
    IssueStatus,
    Tracker,
)


class TrackerSerializer(serializers.ModelSerializer):
    class Meta:
        model = Tracker
        fields = (
            "id",
            "name",
            "description",
            "target",
            "position",
            "is_default",
        )


class IssueStatusSerializer(serializers.ModelSerializer):
    class Meta:
        model = IssueStatus
        fields = (
            "id",
            "name",
            "position",
            "is_closed",
            "is_default",
        )


class CustomFieldEnumerationSerializer(serializers.ModelSerializer):
    parent_id = serializers.IntegerField(required=False, allow_null=True)

    class Meta:
        model = CustomFieldEnumeration
        fields = ("id", "name", "position", "is_active", "parent_id")


class CustomFieldSerializer(serializers.ModelSerializer):
    tracker_ids = serializers.ListField(
        child=serializers.IntegerField(),
        required=False,
        write_only=True,
    )
    enumerations = CustomFieldEnumerationSerializer(many=True, required=False)

    class Meta:
        model = CustomField
        fields = (
            "id",
            "name",
            "field_format",
            "description",
            "is_required",
            "position",
            "default_value",
            "tracker_ids",
            "enumerations",
        )

    def to_representation(self, instance):
        data = super().to_representation(instance)
        data["tracker_ids"] = list(instance.trackers.values_list("id", flat=True))
        data["enumerations"] = CustomFieldEnumerationSerializer(
            instance.enumerations.order_by("position", "id"),
            many=True,
        ).data
        return data

    def _sync_trackers(self, field: CustomField, tracker_ids: list[int]):
        CustomFieldTracker.objects.filter(custom_field=field).delete()
        for tracker_id in tracker_ids:
            CustomFieldTracker.objects.create(custom_field=field, tracker_id=tracker_id)

    def _sync_enumerations(self, field: CustomField, items: list[dict]):
        enum_formats = {
            CustomField.FieldFormat.LIST,
            CustomField.FieldFormat.LINK_LIST,
        }
        if field.field_format not in enum_formats:
            return
        field.enumerations.all().delete()

        roots = [item for item in items if item.get("parent_id") is None]
        children = [item for item in items if item.get("parent_id") is not None]
        id_map: dict[int, int] = {}

        for index, item in enumerate(roots):
            obj = CustomFieldEnumeration.objects.create(
                custom_field=field,
                name=item.get("name", f"Option {index + 1}"),
                position=item.get("position", index),
                is_active=item.get("is_active", True),
                parent=None,
            )
            old_id = item.get("id")
            if old_id is not None:
                id_map[int(old_id)] = obj.id

        for index, item in enumerate(children):
            parent_key = item.get("parent_id")
            if parent_key in (None, ""):
                continue
            parent_id = id_map.get(int(parent_key))
            if parent_id is None:
                continue
            CustomFieldEnumeration.objects.create(
                custom_field=field,
                name=item.get("name", f"Child {index + 1}"),
                position=item.get("position", index),
                is_active=item.get("is_active", True),
                parent_id=parent_id,
            )

    def create(self, validated_data):
        tracker_ids = validated_data.pop("tracker_ids", [])
        validated_data.pop("enumerations", None)
        field = CustomField.objects.create(**validated_data)
        self._sync_trackers(field, tracker_ids)
        raw_items = self.initial_data.get("enumerations", [])
        if raw_items:
            self._sync_enumerations(field, raw_items)
        return field

    def update(self, instance, validated_data):
        tracker_ids = validated_data.pop("tracker_ids", None)
        enumerations = validated_data.pop("enumerations", None)
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        if tracker_ids is not None:
            self._sync_trackers(instance, tracker_ids)
        if enumerations is not None:
            raw_items = self.initial_data.get("enumerations", enumerations)
            self._sync_enumerations(instance, raw_items)
        return instance


class CustomValueWriteSerializer(serializers.Serializer):
    custom_values = serializers.DictField(
        child=serializers.CharField(allow_blank=True),
        required=False,
    )
