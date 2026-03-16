from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("profiles", "0003_studentprofile_skills"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="studentprofile",
            name="batch_year",
        ),
        migrations.AddField(
            model_name="studentprofile",
            name="batch_year",
            field=models.DateField(null=True),
        ),
    ]