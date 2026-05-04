import os
import sys
import django
from pathlib import Path

backend_dir = Path(__file__).resolve().parents[1]
sys.path.append(str(backend_dir))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'django_project.settings')
django.setup()

from lead_magnets.models import Template

def main():
    templates = list(Template.objects.all())
    print("Templates in DB:")
    for t in templates:
        print(f"- id={t.id} name={t.name}")
    # Keep only 'modern-guide'
    to_delete = [t for t in templates if t.id != 'modern-guide']
    if to_delete:
        print(f"Deleting {len(to_delete)} extra templates...")
        for t in to_delete:
            t.delete()
    else:
        print("No extra templates to delete.")

if __name__ == "__main__":
    main()
