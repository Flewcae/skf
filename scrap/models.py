from django.db import models

class Product(models.Model):
    STATUS_CHOICES = (
        ("pending", "Pending"),
        ("processing", "Processing"),
        ("done", "Done"),
        ("error", "Error"),
    )

    url = models.URLField(max_length=1000, unique=True)
    name = models.CharField(null=True, blank=True, max_length=1000)
    desc = models.TextField(null=True, blank=True)
    code = models.CharField(null=True, blank=True, max_length=1000)
    category_hierarchy = models.CharField(null=True, blank=True, max_length=1000)
    image_url = models.URLField(null=True, blank=True, max_length=1000)

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default="pending"
    )

    locked_by = models.CharField(
        null=True,
        blank=True,
        max_length=255
    )

    locked_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return self.url
