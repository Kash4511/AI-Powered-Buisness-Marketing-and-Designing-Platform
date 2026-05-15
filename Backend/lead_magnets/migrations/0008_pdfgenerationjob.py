from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('lead_magnets', '0007_alter_leadmagnet_status'),
    ]

    operations = [
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
    ]
