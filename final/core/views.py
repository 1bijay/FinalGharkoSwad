from django.shortcuts import render, redirect, get_object_or_404
from django.views.generic import TemplateView
from django.contrib import messages
from .models import Order


def index(request):
    return render(request, 'core/index.html')


def order(request):
    if request.method == 'POST':
        name = request.POST.get('name', '').strip()
        phone = request.POST.get('phone', '').strip()
        address = request.POST.get('address', '').strip()
        dish = request.POST.get('dish', 'thali')
        quantity = int(request.POST.get('quantity', 1) or 1)
        total = request.POST.get('total', '₹0')
        delivery_time = request.POST.get('delivery_time', '')
        notes = request.POST.get('notes', '').strip()
        if delivery_time:
            delivery_time = delivery_time + ' (preferred)'
        else:
            delivery_time = 'Will be confirmed'
        Order.objects.create(
            name=name,
            phone=phone,
            address=address,
            dish=dish,
            quantity=quantity,
            total=total,
            delivery_time=delivery_time,
            notes=notes,
            status='confirmed',
        )
        order_obj = Order.objects.latest('created_at')
        request.session['last_order_id'] = order_obj.id
        return redirect('core:order_confirmation', order_id=order_obj.id)
    return render(request, 'core/order.html')


def order_confirmation(request, order_id):
    order_obj = get_object_or_404(Order, id=order_id)
    return render(request, 'core/order_confirmation.html', {'order': order_obj})


def customer_dashboard(request):
    orders = Order.objects.all()
    return render(request, 'core/customer_dashboard.html', {'orders': orders})


def login_view(request):
    if request.method == 'POST':
        # Demo: redirect to home (real auth would use Django's authenticate/login)
        messages.success(request, 'Welcome back! You are now logged in.')
        return redirect('core:index')
    return render(request, 'core/login.html')


def register_view(request):
    if request.method == 'POST':
        # Demo: redirect to home (real auth would create user and log in)
        messages.success(request, 'Account created successfully! You can now log in.')
        return redirect('core:login')
    return render(request, 'core/register.html')


def contact(request):
    if request.method == 'POST':
        messages.success(request, 'Thank you! Your message has been sent. We will get back to you soon.')
        return redirect('core:contact')
    return render(request, 'core/contact.html')


def chef_profile(request):
    return render(request, 'core/chef_profile.html')


def food_details(request):
    return render(request, 'core/food_details.html')


def chef_dashboard(request):
    return render(request, 'core/chef_dashboard.html')
