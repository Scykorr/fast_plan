from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("delivery", "0005_github_links_field_acl"),
    ]

    operations = [
        migrations.AddField(
            model_name="deliverytask",
            name="previous_assignee",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="previously_assigned_delivery_tasks",
                to=settings.AUTH_USER_MODEL,
            ),
        ),
        migrations.AddField(
            model_name="deliverytask",
            name="implementation_summary",
            field=models.TextField(blank=True, default=""),
        ),
        migrations.AddField(
            model_name="deliverytask",
            name="expected_next_step",
            field=models.TextField(blank=True, default=""),
        ),
        migrations.AddField(
            model_name="deliverytask",
            name="github_commits",
            field=models.JSONField(blank=True, default=list),
        ),
        migrations.AlterField(
            model_name="deliverytask",
            name="status",
            field=models.CharField(
                choices=[
                    ("draft", "Черновик"),
                    ("ready", "Готово к назначению"),
                    ("assigned", "Назначено"),
                    ("in_progress", "В работе"),
                    ("blocked", "Заблокировано"),
                    ("review", "На проверке"),
                    ("qa", "На проверке"),
                    ("needs_rework", "Нужна доработка"),
                    ("ready_for_owner", "Готово к решению владельца"),
                    ("done", "Завершено"),
                    ("archived", "Архив"),
                ],
                default="draft",
                max_length=20,
            ),
        ),
        migrations.AddField(
            model_name="taskhandoff",
            name="from_user",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="delivery_handoffs_sent",
                to=settings.AUTH_USER_MODEL,
            ),
        ),
        migrations.AddField(
            model_name="taskhandoff",
            name="to_user",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="delivery_handoffs_received",
                to=settings.AUTH_USER_MODEL,
            ),
        ),
        migrations.AddField(
            model_name="taskhandoff",
            name="reason",
            field=models.TextField(blank=True, default=""),
        ),
        migrations.AddField(
            model_name="taskhandoff",
            name="expected_next_step",
            field=models.TextField(blank=True, default=""),
        ),
        migrations.AlterField(
            model_name="taskcomment",
            name="kind",
            field=models.CharField(
                choices=[
                    ("comment", "Рабочий комментарий"),
                    ("result", "Результат выполнения"),
                    ("handoff_note", "Передача следующему исполнителю"),
                    ("review_finding", "Замечание проверки"),
                    ("blocker_note", "Блокер"),
                    ("owner_request", "Запрос решения владельца"),
                    ("owner_decision", "Решение владельца"),
                ],
                default="comment",
                max_length=20,
            ),
        ),
    ]
