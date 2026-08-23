from django.apps import AppConfig


class DeliveryConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "delivery"
    verbose_name = "Agent Ops / Delivery"

    def ready(self):
        from delivery import signals  # noqa: F401
