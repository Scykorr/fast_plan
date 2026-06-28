from rest_framework import serializers

from finance.models import Transaction


class TransactionSerializer(serializers.ModelSerializer):
    project_id = serializers.IntegerField(source="project.id", read_only=True, allow_null=True)

    class Meta:
        model = Transaction
        fields = (
            "id",
            "project_id",
            "title",
            "amount",
            "transaction_type",
            "category",
            "transaction_date",
            "notes",
            "created_at",
        )
        read_only_fields = ("id", "created_at", "project_id")


class TransactionWriteSerializer(serializers.ModelSerializer):
    project_id = serializers.IntegerField(required=False, allow_null=True)

    class Meta:
        model = Transaction
        fields = (
            "project_id",
            "title",
            "amount",
            "transaction_type",
            "category",
            "transaction_date",
            "notes",
        )
