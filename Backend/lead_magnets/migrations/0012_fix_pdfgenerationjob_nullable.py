from django.db import migrations, models
import django.db.models.deletion

class Migration(migrations.Migration):

    dependencies = [
        ('lead_magnets', '0011_alter_pdfgenerationjob_lead_magnet'),
    ]

    operations = [
        migrations.AlterField(
            model_name='pdfgenerationjob',
            name='lead_magnet',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='pdf_jobs',
                to='lead_magnets.leadmagnet'
            ),
        ),
    ]
