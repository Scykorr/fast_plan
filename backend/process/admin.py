from django.contrib import admin

from process.models import (
    CaseDefinition,
    CaseInstance,
    DecisionDefinition,
    ProcessDefinition,
    ProcessDeployment,
    ProcessInstance,
    UserTask,
)

admin.site.register(ProcessDefinition)
admin.site.register(ProcessDeployment)
admin.site.register(ProcessInstance)
admin.site.register(UserTask)
admin.site.register(DecisionDefinition)
admin.site.register(CaseDefinition)
admin.site.register(CaseInstance)
