from django.db import models
from django.conf import settings
from django.contrib.auth.models import AbstractUser, BaseUserManager


class CustomUserManager(BaseUserManager):
    def create_user(self, email=None, password=None, **extra_fields):
        if not email:
            raise ValueError('Email is required')
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email=None, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        if extra_fields.get('is_staff') is not True:
            raise ValueError('Superuser must have is_staff=True.')
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('Superuser must have is_superuser=True.')
        return self.create_user(email=email, password=password, **extra_fields)


class CustomUser(AbstractUser):
    USER_TYPE_CHOICES = (
        ('customer', 'Customer'),
        ('chef', 'Chef'),
    )

    username = None
    email = models.EmailField(unique=True)
    phone = models.CharField(max_length=15, blank=True)
    address = models.TextField(blank=True)
    user_type = models.CharField(max_length=10, choices=USER_TYPE_CHOICES, default='customer')
    speciality = models.CharField(max_length=200, blank=True, null=True)

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = []
    objects = CustomUserManager()

    def __str__(self):
        return self.email







class FoodItem(models.Model):
    CATEGORY_CHOICES = [
        ('rice', 'Rice'),
        ('veg', 'Veg'),
        ('non_veg', 'Non-veg'),
        ('sweets_mithai', 'Sweets (Mithai)'),
        ('breads', 'Breads'),
        ('sweets_desserts', 'Sweets & Desserts'),
        ('pickles_sides', 'Pickles & Side Dishes'),
        ('curries', 'Curries'),
        ('soups', 'Soups'),
        ('snacks', 'Snacks'),
        ('nepali', 'Nepali'),
        ('indian', 'Indian'),
        ('other', 'Other (add your own)'),
    ]
    AVAILABILITY_CHOICES = [
        ('daily', 'Daily'),
        ('weekdays', 'Weekdays Only'),
        ('weekends', 'Weekends Only'),
        ('custom', 'Custom'),
    ]
    chef = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='food_items')
    name = models.CharField(max_length=200)
    category = models.CharField(max_length=30, choices=CATEGORY_CHOICES, default='other')
    category_custom = models.CharField(max_length=100, blank=True, help_text='When category is Other, your own category name')
    price = models.DecimalField(max_digits=10, decimal_places=2)
    description = models.TextField(blank=True)
    image = models.ImageField(upload_to='food/%Y/%m/', blank=True, null=True)
    image_url = models.URLField(blank=True, max_length=500)
    servings_available = models.PositiveIntegerField(default=10)
    availability = models.CharField(max_length=20, choices=AVAILABILITY_CHOICES, default='daily')
    is_vegetarian = models.BooleanField(default=True)
    is_spicy = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def get_display_category(self):
        """Show custom category name when chef chose 'Other', else the choice label."""
        if self.category == 'other' and getattr(self, 'category_custom', None):
            return (self.category_custom or '').strip()
        try:
            return self.get_category_display()
        except (AttributeError, ValueError):
            return getattr(self, 'category', '') or 'Other'

    def __str__(self):
        return f"{self.name} by {self.chef.get_full_name() or self.chef.email}"


class Review(models.Model):
    RATING_CHOICES = [(i, str(i)) for i in range(1, 6)]
    food_item = models.ForeignKey(FoodItem, on_delete=models.CASCADE, related_name='reviews')
    customer = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='reviews')
    order = models.ForeignKey('Order', on_delete=models.SET_NULL, null=True, blank=True, related_name='reviews')
    rating = models.PositiveSmallIntegerField(choices=RATING_CHOICES)
    text = models.TextField()
    chef_reply = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.rating}★ for {self.food_item.name} by {self.customer.get_full_name() or self.customer.email}"


class Order(models.Model):
    DISH_CHOICES = [
        ('thali', 'Homemade Thali'),
        ('momo', 'Steamed Momo Platter'),
        ('biryani', 'Veg Biryani'),
        ('soup', 'Comfort Veg Soup'),
    ]
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('confirmed', 'Confirmed'),
        ('preparing', 'Preparing'),
        ('delivered', 'Delivered'),
        ('cancelled', 'Cancelled'),
    ]

    chef = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='orders_received', null=True, blank=True)
    customer = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='orders_placed')
    food_item = models.ForeignKey(FoodItem, on_delete=models.SET_NULL, null=True, blank=True, related_name='orders')

    name = models.CharField(max_length=200)
    phone = models.CharField(max_length=20)
    address = models.TextField()
    dish = models.CharField(max_length=20, choices=DISH_CHOICES, blank=True)
    quantity = models.PositiveIntegerField(default=1)
    total = models.CharField(max_length=50)
    delivery_time = models.CharField(max_length=100, blank=True)
    notes = models.TextField(blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        dish_name = self.food_item.name if self.food_item else (self.get_dish_display() if self.dish else 'Order')
        return f"Order #{self.id} - {dish_name} by {self.name}"


class ContactMessage(models.Model):
    """Contact form submissions - stored so you never lose a message."""
    name = models.CharField(max_length=200)
    email = models.EmailField()
    phone = models.CharField(max_length=20, blank=True)
    message = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.name} ({self.email}) - {self.created_at}"
