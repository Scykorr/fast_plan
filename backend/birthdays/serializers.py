from rest_framework import serializers

from birthdays.models import Birthday, Contact


class BirthdaySerializer(serializers.ModelSerializer):
    class Meta:
        model = Birthday
        fields = ("birth_date", "remind_before_days")


class ContactSerializer(serializers.ModelSerializer):
    birth_date = serializers.DateField(source="birthday.birth_date", read_only=True)
    remind_before_days = serializers.IntegerField(
        source="birthday.remind_before_days",
        read_only=True,
    )

    class Meta:
        model = Contact
        fields = (
            "id",
            "name",
            "relation",
            "notes",
            "birth_date",
            "remind_before_days",
            "created_at",
        )


class ContactWriteSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=255)
    relation = serializers.CharField(max_length=100, required=False, allow_blank=True)
    notes = serializers.CharField(required=False, allow_blank=True)
    birth_date = serializers.DateField()
    remind_before_days = serializers.IntegerField(required=False, min_value=0, default=7)

    def create(self, validated_data):
        workspace = self.context["workspace"]
        contact = Contact.objects.create(
            workspace=workspace,
            name=validated_data["name"],
            relation=validated_data.get("relation", ""),
            notes=validated_data.get("notes", ""),
        )
        Birthday.objects.create(
            contact=contact,
            birth_date=validated_data["birth_date"],
            remind_before_days=validated_data.get("remind_before_days", 7),
        )
        return contact

    def update(self, instance, validated_data):
        instance.name = validated_data.get("name", instance.name)
        instance.relation = validated_data.get("relation", instance.relation)
        instance.notes = validated_data.get("notes", instance.notes)
        instance.save()

        birthday = instance.birthday
        if "birth_date" in validated_data:
            birthday.birth_date = validated_data["birth_date"]
        if "remind_before_days" in validated_data:
            birthday.remind_before_days = validated_data["remind_before_days"]
        birthday.save()
        return instance


class UpcomingBirthdaySerializer(serializers.Serializer):
    contact_id = serializers.IntegerField()
    name = serializers.CharField()
    relation = serializers.CharField()
    birth_date = serializers.DateField()
    next_date = serializers.DateField()
    days_until = serializers.IntegerField()
