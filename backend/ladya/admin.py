from django.contrib import admin

from ladya.models import (
    IntakeRequest,
    Laboratory,
    LadyaSettings,
    Package,
    PackageFile,
    PackageStatusEvent,
)


@admin.register(LadyaSettings)
class LadyaSettingsAdmin(admin.ModelAdmin):
    list_display = ("workspace", "ladya_hub_enabled", "updated_at")
    list_filter = ("ladya_hub_enabled",)


@admin.register(Laboratory)
class LaboratoryAdmin(admin.ModelAdmin):
    list_display = ("title", "slug", "kind", "workspace", "is_active", "created_at")
    list_filter = ("kind", "is_active")
    search_fields = ("title", "slug")


class PackageFileInline(admin.TabularInline):
    model = PackageFile
    extra = 0
    readonly_fields = ("sha256", "size", "content_type", "uploaded_by", "created_at")


class PackageStatusEventInline(admin.TabularInline):
    model = PackageStatusEvent
    extra = 0
    readonly_fields = (
        "from_status",
        "to_status",
        "from_laboratory",
        "to_laboratory",
        "reason",
        "changed_by",
        "created_at",
    )


@admin.register(Package)
class PackageAdmin(admin.ModelAdmin):
    list_display = (
        "public_number",
        "title",
        "status",
        "from_laboratory",
        "to_laboratory",
        "workspace",
        "created_at",
    )
    list_filter = ("status",)
    search_fields = ("title", "summary")
    inlines = [PackageFileInline, PackageStatusEventInline]


@admin.register(IntakeRequest)
class IntakeRequestAdmin(admin.ModelAdmin):
    list_display = ("id", "status", "source", "contact", "workspace", "created_at")
    list_filter = ("status", "source")
