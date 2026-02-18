from django.db import models


class Order(models.Model):
    DISH_CHOICES = [
        ('thali', 'Homemade Thali'),
        ('momo', 'Steamed Momo Platter'),
        ('biryani', 'Veg Biryani'),
        ('soup', 'Comfort Veg Soup'),
    ]
    STATUS_CHOICES = [
        ('confirmed', 'Confirmed'),
        ('preparing', 'Preparing'),
        ('delivered', 'Delivered'),
        ('cancelled', 'Cancelled'),
    ]

    name = models.CharField(max_length=200)
    phone = models.CharField(max_length=20)
    address = models.TextField()
    dish = models.CharField(max_length=20, choices=DISH_CHOICES)
    quantity = models.PositiveIntegerField(default=1)
    total = models.CharField(max_length=50)
    delivery_time = models.CharField(max_length=100, blank=True)
    notes = models.TextField(blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='confirmed')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Order #{self.id} - {self.get_dish_display()} by {self.name}"
