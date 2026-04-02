from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0006_alter_apiresourcepermission_resource"),
    ]

    operations = [
        migrations.AddField(
            model_name="module",
            name="show_in_dashboard",
            field=models.BooleanField(default=True),
        ),
        migrations.AddField(
            model_name="module",
            name="show_in_sidebar",
            field=models.BooleanField(default=True),
        ),
    ]
