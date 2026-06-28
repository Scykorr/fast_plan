from django.contrib import admin

from birthdays.models import Birthday, Contact


class BirthdayInline(admin.StackedInline):
    model = Birthday
    extra = 0


@admin.register(Contact)
class ContactAdmin(admin.ModelAdmin):
    list_display = ("name", "relation", "workspace", "created_at")
    search_fields = ("name", "relation")
    inlines = [BirthdayInline]


@admin.register(Birthday)
class BirthdayAdmin(admin.ModelAdmin):
    list_display = ("contact", "birth_date", "remind_before_days")
