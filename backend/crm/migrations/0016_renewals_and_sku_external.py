# Generated manually for P10 remaining backlog

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("crm", "0015_document_share_links"),
    ]

    operations = [
        migrations.AddField(
            model_name="crmdocument",
            name="renewal_date",
            field=models.DateField(
                blank=True,
                help_text="Next renewal date for contracts (ARR lite).",
                null=True,
            ),
        ),
        migrations.AddField(
            model_name="crmdocument",
            name="term_months",
            field=models.PositiveSmallIntegerField(
                blank=True, help_text="Contract term in months.", null=True
            ),
        ),
        migrations.AddField(
            model_name="crmdocument",
            name="arr_annual",
            field=models.DecimalField(
                blank=True,
                decimal_places=2,
                help_text="Annual recurring revenue override; falls back to amount.",
                max_digits=14,
                null=True,
            ),
        ),
        migrations.AddField(
            model_name="crmsku",
            name="external_ref",
            field=models.CharField(
                blank=True,
                db_index=True,
                default="",
                help_text="External system id (e.g. 1C nomenclature).",
                max_length=120,
            ),
        ),
    ]
