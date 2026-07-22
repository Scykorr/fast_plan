from django.contrib import admin

from crm.models import (
    Activity,
    CrmAttachment,
    CrmComment,
    Organization,
    OrganizationMembership,
    OrganizationTag,
    Person,
    PersonTag,
    ProjectPersonLink,
    Segment,
    Tag,
)

admin.site.register(Organization)
admin.site.register(Person)
admin.site.register(OrganizationMembership)
admin.site.register(Tag)
admin.site.register(PersonTag)
admin.site.register(OrganizationTag)
admin.site.register(Segment)
admin.site.register(CrmComment)
admin.site.register(CrmAttachment)
admin.site.register(ProjectPersonLink)
admin.site.register(Activity)
