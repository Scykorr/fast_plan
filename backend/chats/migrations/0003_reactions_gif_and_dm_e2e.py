import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models
from django.db.models import Q


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("chats", "0002_chat_ext_dm_threads_reactions_voice_guest_archive"),
    ]

    operations = [
        migrations.AddField(
            model_name="chatmessage",
            name="is_encrypted",
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name="chatreaction",
            name="kind",
            field=models.CharField(
                choices=[("emoji", "Emoji"), ("gif", "GIF")],
                default="emoji",
                max_length=10,
            ),
        ),
        migrations.AddField(
            model_name="chatreaction",
            name="gif_url",
            field=models.URLField(blank=True, default="", max_length=500),
        ),
        migrations.AlterField(
            model_name="chatreaction",
            name="emoji",
            field=models.CharField(blank=True, default="", max_length=32),
        ),
        migrations.RemoveConstraint(
            model_name="chatreaction",
            name="uniq_chat_reaction_user_emoji",
        ),
        migrations.AddConstraint(
            model_name="chatreaction",
            constraint=models.UniqueConstraint(
                fields=("message", "user", "kind", "emoji", "gif_url"),
                name="uniq_chat_reaction_user_token",
            ),
        ),
        migrations.AddConstraint(
            model_name="chatreaction",
            constraint=models.CheckConstraint(
                condition=(
                    Q(kind="emoji", emoji__gt="", gif_url="")
                    | Q(kind="gif", gif_url__gt="", emoji="")
                ),
                name="chat_reaction_kind_payload",
            ),
        ),
        migrations.CreateModel(
            name="ChatUserCryptoKey",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("public_jwk", models.JSONField()),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "user",
                    models.OneToOneField(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="chat_crypto_key",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
        ),
        migrations.CreateModel(
            name="ChatRoomKeyWrap",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("wrapped_key", models.TextField()),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "room",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="key_wraps",
                        to="chats.chatroom",
                    ),
                ),
                (
                    "user",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="chat_key_wraps",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "constraints": [
                    models.UniqueConstraint(
                        fields=("room", "user"),
                        name="uniq_chat_room_key_wrap_user",
                    )
                ],
            },
        ),
    ]
