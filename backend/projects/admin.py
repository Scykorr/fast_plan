from django.contrib import admin

from projects.models import ActivityDependency, Project, ScheduleActivity, WBSNode


@admin.register(Project)
class ProjectAdmin(admin.ModelAdmin):
    list_display = ("name", "workspace", "status", "manager", "created_at")
    list_filter = ("status",)


@admin.register(WBSNode)
class WBSNodeAdmin(admin.ModelAdmin):
    list_display = ("code", "title", "project", "node_type", "parent")
    list_filter = ("node_type", "project")


@admin.register(ScheduleActivity)
class ScheduleActivityAdmin(admin.ModelAdmin):
    list_display = ("wbs_node", "start_date", "end_date", "progress", "is_milestone")


@admin.register(ActivityDependency)
class ActivityDependencyAdmin(admin.ModelAdmin):
    list_display = ("predecessor", "dependency_type", "successor", "lag_days")
