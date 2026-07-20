from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("chats", "0003_reactions_gif_and_dm_e2e"),
    ]

    operations = [
        migrations.AddField(
            model_name="chatusercryptokey",
            name="recovery_blob",
            field=models.TextField(blank=True, default=""),
        ),
        migrations.AddField(
            model_name="chatusercryptokey",
            name="recovery_salt",
            field=models.CharField(blank=True, default="", max_length=64),
        ),
    ]
