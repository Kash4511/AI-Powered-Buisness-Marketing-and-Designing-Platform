from django.db import migrations

class Migration(migrations.Migration):

    dependencies = [
        ('lead_magnets', '0011_alter_pdfgenerationjob_lead_magnet'),
    ]

    operations = [
        migrations.RunSQL(
            sql='ALTER TABLE lead_magnets_pdfgenerationjob ALTER COLUMN lead_magnet_id DROP NOT NULL;',
            reverse_sql='ALTER TABLE lead_magnets_pdfgenerationjob ALTER COLUMN lead_magnet_id SET NOT NULL;',
        ),
    ]
