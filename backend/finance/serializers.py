from rest_framework import serializers

from finance.models import Transaction


class TransactionSerializer(serializers.ModelSerializer):
    project_id = serializers.IntegerField(source="project.id", read_only=True, allow_null=True)
    organization_id = serializers.IntegerField(
        source="organization.id", read_only=True, allow_null=True
    )
    organization_name = serializers.SerializerMethodField()
    deal_id = serializers.IntegerField(source="deal.id", read_only=True, allow_null=True)

    class Meta:
        model = Transaction
        fields = (
            "id",
            "project_id",
            "organization_id",
            "organization_name",
            "deal_id",
            "title",
            "amount",
            "transaction_type",
            "category",
            "transaction_date",
            "notes",
            "created_at",
        )
        read_only_fields = (
            "id",
            "created_at",
            "project_id",
            "organization_id",
            "organization_name",
            "deal_id",
        )

    def get_organization_name(self, obj):
        return obj.organization.name if obj.organization_id else None


class TransactionWriteSerializer(serializers.ModelSerializer):
    project_id = serializers.IntegerField(required=False, allow_null=True)
    organization_id = serializers.IntegerField(required=False, allow_null=True)
    deal_id = serializers.IntegerField(required=False, allow_null=True)

    class Meta:
        model = Transaction
        fields = (
            "project_id",
            "organization_id",
            "deal_id",
            "title",
            "amount",
            "transaction_type",
            "category",
            "transaction_date",
            "notes",
        )
