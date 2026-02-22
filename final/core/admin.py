from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import Order, CustomUser, FoodItem, Review


@admin.register(CustomUser)
class CustomUserAdmin(BaseUserAdmin):
    list_display = ('email', 'first_name', 'user_type', 'phone')
    list_filter = ('user_type',)
    ordering = ('email',)
    fieldsets = (
        (None, {'fields': ('email', 'password')}),
        ('Personal info', {'fields': ('first_name', 'phone', 'address', 'user_type', 'speciality')}),
        ('Permissions', {'fields': ('is_active', 'is_staff', 'is_superuser')}),
    )
    add_fieldsets = (
        (None, {'fields': ('email', 'password1', 'password2')}),
        ('Personal info', {'fields': ('first_name', 'phone', 'address', 'user_type', 'speciality')}),
    )


@admin.register(FoodItem)
class FoodItemAdmin(admin.ModelAdmin):
    list_display = ('name', 'chef', 'category', 'price', 'created_at')
    list_filter = ('category', 'is_vegetarian')


@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    list_display = ('food_item', 'customer', 'rating', 'created_at')


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'chef', 'quantity', 'total', 'status', 'created_at')
    list_filter = ('status',)
    search_fields = ('name', 'phone', 'address')
