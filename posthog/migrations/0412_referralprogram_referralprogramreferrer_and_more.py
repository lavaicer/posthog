# Generated by Django 4.2.11 on 2024-05-15 08:48

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import posthog.models.utils
import posthog.utils


class Migration(migrations.Migration):
    dependencies = [
        ("posthog", "0411_eventproperty_indexes"),
    ]

    operations = [
        migrations.CreateModel(
            name="ReferralProgram",
            fields=[
                (
                    "id",
                    models.UUIDField(
                        default=posthog.models.utils.UUIDT, editable=False, primary_key=True, serialize=False
                    ),
                ),
                ("short_id", models.CharField(blank=True, default=posthog.utils.generate_short_id, max_length=12)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("title", models.TextField(blank=True, default="", null=True)),
                ("description", models.TextField(blank=True, default="", null=True)),
                ("max_total_redemption_count", models.PositiveIntegerField(blank=True, null=True)),
                ("max_redemption_count_per_referrer", models.PositiveIntegerField(blank=True, null=True)),
                (
                    "created_by",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="created_referral_programs",
                        related_query_name="created_referral_program",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "team",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="referral_codes",
                        related_query_name="referral_code",
                        to="posthog.team",
                    ),
                ),
            ],
        ),
        migrations.CreateModel(
            name="ReferralProgramReferrer",
            fields=[
                (
                    "id",
                    models.UUIDField(
                        default=posthog.models.utils.UUIDT, editable=False, primary_key=True, serialize=False
                    ),
                ),
                ("user_id", models.CharField(max_length=128)),
                ("code", models.TextField(default=posthog.utils.generate_short_id, max_length=128)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("max_redemption_count", models.PositiveIntegerField(blank=True, null=True)),
                (
                    "referral_program",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="referrers",
                        related_query_name="referrer",
                        to="posthog.referralprogram",
                    ),
                ),
            ],
        ),
        migrations.CreateModel(
            name="ReferralProgramRedeemer",
            fields=[
                (
                    "id",
                    models.UUIDField(
                        default=posthog.models.utils.UUIDT, editable=False, primary_key=True, serialize=False
                    ),
                ),
                ("user_id", models.CharField(max_length=128)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("points_awarded", models.PositiveIntegerField(blank=True, null=True)),
                (
                    "referral_program",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="redeemers",
                        related_query_name="redeemer",
                        to="posthog.referralprogram",
                    ),
                ),
                (
                    "referrer",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="redeemers",
                        related_query_name="redeemer",
                        to="posthog.referralprogramreferrer",
                    ),
                ),
            ],
        ),
        migrations.AddConstraint(
            model_name="referralprogramreferrer",
            constraint=models.UniqueConstraint(
                fields=("user_id", "referral_program"), name="unique user_id for program referrer"
            ),
        ),
        migrations.AddConstraint(
            model_name="referralprogramredeemer",
            constraint=models.UniqueConstraint(
                fields=("user_id", "referral_program"), name="unique user_id for program redeemer"
            ),
        ),
        migrations.AddConstraint(
            model_name="referralprogram",
            constraint=models.UniqueConstraint(fields=("team", "short_id"), name="unique short_id for team"),
        ),
    ]
