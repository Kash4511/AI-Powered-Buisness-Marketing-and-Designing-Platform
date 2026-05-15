from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('lead_magnets', '0007_alter_leadmagnet_status'),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            state_operations=[
                migrations.CreateModel(
                    name='PDFGenerationJob',
                    fields=[
                        ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                        ('job_id', models.CharField(max_length=100, unique=True)),
                        ('status', models.CharField(default='pending', max_length=20)),
                        ('progress', models.IntegerField(default=0)),
                        ('message', models.CharField(blank=True, max_length=255)),
                        ('pdf_url', models.URLField(blank=True, null=True)),
                        ('error', models.TextField(blank=True, null=True)),
                        ('stop_requested', models.BooleanField(default=False)),
                        ('created_at', models.DateTimeField(auto_now_add=True)),
                        ('updated_at', models.DateTimeField(auto_now=True)),
                        ('lead_magnet', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='pdf_jobs', to='lead_magnets.leadmagnet')),
                    ],
                    options={
                        'ordering': ['-created_at'],
                    },
                ),
            ],
            database_operations=[
                migrations.RunSQL(
                    sql="""
                    CREATE TABLE IF NOT EXISTS lead_magnets_pdfgenerationjob (
                        id bigserial PRIMARY KEY,
                        job_id varchar(100) NOT NULL UNIQUE,
                        status varchar(20) NOT NULL DEFAULT 'pending',
                        progress integer NOT NULL DEFAULT 0,
                        message varchar(255) NOT NULL DEFAULT '',
                        pdf_url varchar(200),
                        error text,
                        stop_requested boolean NOT NULL DEFAULT false,
                        created_at timestamptz NOT NULL DEFAULT now(),
                        updated_at timestamptz NOT NULL DEFAULT now(),
                        lead_magnet_id bigint NOT NULL REFERENCES lead_magnets_leadmagnet(id) ON DELETE CASCADE
                    );
                    CREATE INDEX IF NOT EXISTS lead_magnets_pdfgenerationjob_lead_magnet_id_idx ON lead_magnets_pdfgenerationjob(lead_magnet_id);
                    """,
                    reverse_sql="DROP TABLE IF EXISTS lead_magnets_pdfgenerationjob;"
                )
            ]
        )
    ]
