from django.contrib import admin

from crm.models import (
    Activity,
    Organization,
    OrganizationMembership,
    Person,
    ProjectPersonLink,
)

admin.site.register(Organization)
admin.site.register(Person)
admin.site.register(OrganizationMembership)
admin.site.register(ProjectPersonLink)
admin.site.register(Activity)
