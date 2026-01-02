# Generated migration for adding slug field to BulkOrderLink
# Save this as: bulk_orders/migrations/0002_bulkorderlink_slug.py

from django.db import migrations, models
import random
import string
from django.utils.text import slugify


def generate_slugs_for_existing(apps, schema_editor):
    """Generate slugs for existing BulkOrderLink records"""
    BulkOrderLink = apps.get_model('bulk_orders', 'BulkOrderLink')
    
    for bulk_order in BulkOrderLink.objects.all():
        base_slug = slugify(bulk_order.organization_name)
        if len(base_slug) > 280:
            base_slug = base_slug[:280]
        
        # Generate random 4-character suffix
        suffix = ''.join(random.choices(string.ascii_lowercase + string.digits, k=4))
        slug = f"{base_slug}-{suffix}"
        
        # Ensure uniqueness
        while BulkOrderLink.objects.filter(slug=slug).exists():
            suffix = ''.join(random.choices(string.ascii_lowercase + string.digits, k=4))
            slug = f"{base_slug}-{suffix}"
        
        bulk_order.slug = slug
        bulk_order.save(update_fields=['slug'])


class Migration(migrations.Migration):

    dependencies = [
        ('bulk_orders', '0001_initial'),
    ]

    operations = [
        # Add slug field as nullable first
        migrations.AddField(
            model_name='bulkorderlink',
            name='slug',
            field=models.SlugField(max_length=300, null=True, blank=True, editable=False, help_text='Auto-generated from organization name'),
        ),
        # Generate slugs for existing records
        migrations.RunPython(generate_slugs_for_existing, reverse_code=migrations.RunPython.noop),
        # Make slug unique and non-nullable
        migrations.AlterField(
            model_name='bulkorderlink',
            name='slug',
            field=models.SlugField(max_length=300, unique=True, editable=False, help_text='Auto-generated from organization name'),
        ),
        # Add index for slug
        migrations.AddIndex(
            model_name='bulkorderlink',
            index=models.Index(fields=['slug'], name='bulk_order_slug_idx'),
        ),
    ]