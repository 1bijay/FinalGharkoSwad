from django.urls import path
from . import views

app_name = 'core'

urlpatterns = [
    path('', views.index, name='index'),
    path('order/', views.order, name='order'),
    path('order/confirmation/<int:order_id>/', views.order_confirmation, name='order_confirmation'),
    path('my-orders/', views.customer_dashboard, name='customer_dashboard'),
    path('login/', views.login_view, name='login'),
    path('register/', views.register_view, name='register'),
    path('contact/', views.contact, name='contact'),
    path('chefs/', views.chef_profile, name='chef_profile'),
    path('food/', views.food_details, name='food_details'),
    path('chef-dashboard/', views.chef_dashboard, name='chef_dashboard'),
]
