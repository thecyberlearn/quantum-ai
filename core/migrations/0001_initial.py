# Generated by Django 5.2.4 on 2025-07-25 20:53

import uuid
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name="ContactSubmission",
            fields=[
                (
                    "id",
                    models.UUIDField(
                        default=uuid.uuid4,
                        editable=False,
                        primary_key=True,
                        serialize=False,
                    ),
                ),
                ("name", models.CharField(max_length=100)),
                ("email", models.EmailField(max_length=254)),
                ("company", models.CharField(blank=True, max_length=100)),
                ("message", models.TextField(max_length=1000)),
                ("ip_address", models.GenericIPAddressField()),
                ("user_agent", models.TextField(blank=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("is_processed", models.BooleanField(default=False)),
                ("processed_at", models.DateTimeField(blank=True, null=True)),
            ],
            options={
                "ordering": ["-created_at"],
                "indexes": [
                    models.Index(
                        fields=["-created_at"], name="core_contac_created_fecead_idx"
                    ),
                    models.Index(
                        fields=["is_processed"], name="core_contac_is_proc_10c42d_idx"
                    ),
                    models.Index(
                        fields=["ip_address"], name="core_contac_ip_addr_88d5d9_idx"
                    ),
                ],
            },
        ),
    ]
