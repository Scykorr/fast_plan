from django.contrib import admin

from delivery import models

admin.site.register(models.DeliverySettings)
admin.site.register(models.DeliveryProjectMeta)
admin.site.register(models.AgentProfile)
admin.site.register(models.AgentActionLog)
admin.site.register(models.Epic)
admin.site.register(models.Sprint)
admin.site.register(models.DeliveryTask)
admin.site.register(models.TaskDependency)
admin.site.register(models.DeliverySubTask)
admin.site.register(models.TaskStatusHistory)
admin.site.register(models.TaskFieldHistory)
admin.site.register(models.TaskBlocker)
admin.site.register(models.TaskHandoff)
admin.site.register(models.TaskComment)
admin.site.register(models.DeliveryAccessLog)
