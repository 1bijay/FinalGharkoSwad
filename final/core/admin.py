from django.contrib import admin
from .models import Order


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'dish', 'quantity', 'total', 'status', 'created_at')
    list_filter = ('status', 'dish')
    search_fields = ('name', 'phone', 'address')
