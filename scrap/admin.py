from django.contrib import admin
from scrap.models import Product

@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.exclude(status="pending")