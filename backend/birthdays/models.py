from django.db import models

from workspaces.models import Workspace


class Contact(models.Model):
    workspace = models.ForeignKey(
        Workspace,
        on_delete=models.CASCADE,
        related_name="contacts",
    )
    name = models.CharField(max_length=255)
    relation = models.CharField(max_length=100, blank=True)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name


class Birthday(models.Model):
    contact = models.OneToOneField(
        Contact,
        on_delete=models.CASCADE,
        related_name="birthday",
    )
    birth_date = models.DateField()
    remind_before_days = models.PositiveSmallIntegerField(default=7)

    def __str__(self):
        return f"{self.contact.name} — {self.birth_date}"
