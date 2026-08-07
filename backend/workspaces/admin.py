from django.contrib import admin

from .models import ObsRole, OrgUnit, Workspace, WorkspaceMember


class WorkspaceMemberInline(admin.TabularInline):
    model = WorkspaceMember
    extra = 0


@admin.register(Workspace)
class WorkspaceAdmin(admin.ModelAdmin):
    list_display = ("name", "owner", "created_at")
    inlines = [WorkspaceMemberInline]


@admin.register(WorkspaceMember)
class WorkspaceMemberAdmin(admin.ModelAdmin):
    list_display = ("workspace", "user", "role", "joined_at")


@admin.register(OrgUnit)
class OrgUnitAdmin(admin.ModelAdmin):
    list_display = ("name", "code", "workspace", "parent", "position")
    list_filter = ("workspace",)


@admin.register(ObsRole)
class ObsRoleAdmin(admin.ModelAdmin):
    list_display = ("name", "code", "workspace", "position")
    list_filter = ("workspace",)
