from django.contrib import admin

from audit.models import AuditLogEntry


@admin.register(AuditLogEntry)
class AuditLogEntryAdmin(admin.ModelAdmin):
    list_display = ("id", "workspace", "actor", "action", "entity_type", "entity_id", "created_at")
    list_filter = ("action", "entity_type")
    search_fields = ("summary",)
    readonly_fields = [field.name for field in AuditLogEntry._meta.fields]

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
