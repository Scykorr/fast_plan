from django.contrib import admin

from projects.models import (
    ActivityDependency,
    PhaseGate,
    Project,
    ScheduleActivity,
    WBSNode,
)


@admin.register(Project)
class ProjectAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "workspace",
        "status",
        "methodology",
        "schedule_locked",
        "manager",
        "created_at",
    )
    list_filter = ("status", "methodology", "schedule_locked")


@admin.register(WBSNode)
class WBSNodeAdmin(admin.ModelAdmin):
    list_display = (
        "code",
        "title",
        "project",
        "node_type",
        "phase_key",
        "gate_status",
        "parent",
    )
    list_filter = ("node_type", "phase_key", "gate_status", "project")


@admin.register(ScheduleActivity)
class ScheduleActivityAdmin(admin.ModelAdmin):
    list_display = ("wbs_node", "start_date", "end_date", "progress", "is_milestone")


@admin.register(ActivityDependency)
class ActivityDependencyAdmin(admin.ModelAdmin):
    list_display = ("predecessor", "dependency_type", "successor", "lag_days")


@admin.register(PhaseGate)
class PhaseGateAdmin(admin.ModelAdmin):
    list_display = (
        "project",
        "wbs_phase_node",
        "decision",
        "decided_by",
        "decided_at",
    )
    list_filter = ("decision",)
