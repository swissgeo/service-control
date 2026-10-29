from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("organization", "0012_attribution"),
    ]

    operations = [
        migrations.RenameField(
            model_name="organization",
            old_name="acronym_de",
            new_name="abbreviation_de",
        ),
        migrations.RenameField(
            model_name="organization",
            old_name="acronym_fr",
            new_name="abbreviation_fr",
        ),
        migrations.RenameField(
            model_name="organization",
            old_name="acronym_en",
            new_name="abbreviation_en",
        ),
        migrations.RenameField(
            model_name="organization",
            old_name="acronym_it",
            new_name="abbreviation_it",
        ),
        migrations.RenameField(
            model_name="organization",
            old_name="acronym_rm",
            new_name="abbreviation_rm",
        ),
        migrations.AlterField(
            model_name="organization",
            name="abbreviation_de",
            field=models.CharField(verbose_name="Abbreviation (German)"),
        ),
        migrations.AlterField(
            model_name="organization",
            name="abbreviation_fr",
            field=models.CharField(verbose_name="Abbreviation (French)"),
        ),
        migrations.AlterField(
            model_name="organization",
            name="abbreviation_en",
            field=models.CharField(verbose_name="Abbreviation (English)"),
        ),
        migrations.AlterField(
            model_name="organization",
            name="abbreviation_it",
            field=models.CharField(blank=True, null=True, verbose_name="Abbreviation (Italian)"),
        ),
        migrations.AlterField(
            model_name="organization",
            name="abbreviation_rm",
            field=models.CharField(blank=True, null=True, verbose_name="Abbreviation (Romansh)"),
        ),
    ]
