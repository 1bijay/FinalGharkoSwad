import re
from decimal import Decimal
from urllib.parse import urlencode
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse
from django.contrib.auth import login as auth_login, logout as auth_logout, authenticate
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.contrib import messages
from django.db.models import Count, Avg, Q
from django.utils import timezone
from django.utils.http import url_has_allowed_host_and_scheme
from .models import Order, FoodItem, Review

User = get_user_model()
EMAIL_REGEX = re.compile(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$')


def _parse_total(s):
    """Parse '₹180' or '180' to Decimal."""
    if not s:
        return Decimal('0')
    s = re.sub(r'[^\d.]', '', str(s))
    try:
        return Decimal(s)
    except Exception:
        return Decimal('0')


def index(request):
    from django.db.models import Avg
    # Only show food items that still have servings available (not sold out / delivered)
    food_items = (
        FoodItem.objects.filter(servings_available__gt=0)
        .select_related('chef')
        .annotate(
            review_count=Count('reviews'),
            avg_rating=Avg('reviews__rating'),
        )
    )[:24]
    return render(request, 'core/index.html', {'food_items': food_items})


def order(request):
    # Require login to view order form or place order
    if not request.user.is_authenticated:
        messages.warning(request, 'Please log in to place an order.')
        next_url = request.get_full_path()
        login_url = reverse('core:login')
        if next_url:
            login_url += '?' + urlencode({'next': next_url})
        return redirect(login_url)

    food_item = None
    item_id = request.GET.get('item') or (request.POST.get('food_item_id') if request.method == 'POST' else None)
    if item_id:
        try:
            food_item = FoodItem.objects.get(id=int(item_id))
        except (ValueError, FoodItem.DoesNotExist):
            food_item = None

    if request.method == 'POST':
        # Chef cannot order their own food
        if food_item and getattr(request.user, 'user_type', None) == 'chef' and food_item.chef_id == request.user.id:
            messages.error(request, 'You cannot order your own food. Please order from other chefs.')
            order_name = (request.user.get_full_name() or request.user.first_name or request.user.email or '').strip()
            order_phone = getattr(request.user, 'phone', '') or ''
            order_address = getattr(request.user, 'address', '') or ''
            return render(request, 'core/order.html', {
                'food_item': food_item,
                'order_name': order_name,
                'order_phone': order_phone,
                'order_address': order_address,
            })

        name = request.POST.get('name', '').strip()
        phone = request.POST.get('phone', '').strip()
        address = request.POST.get('address', '').strip()
        quantity = int(request.POST.get('quantity', 1) or 1)
        total = request.POST.get('total', '₹0')
        delivery_time = request.POST.get('delivery_time', '')
        notes = request.POST.get('notes', '').strip()
        food_item_id = request.POST.get('food_item_id')
        if food_item_id and not food_item:
            try:
                food_item = FoodItem.objects.get(id=int(food_item_id))
            except (ValueError, FoodItem.DoesNotExist):
                pass
        # Re-check after resolving food_item from POST (chef might have selected own item)
        if food_item and getattr(request.user, 'user_type', None) == 'chef' and food_item.chef_id == request.user.id:
            messages.error(request, 'You cannot order your own food.')
            order_name = (request.user.get_full_name() or request.user.first_name or request.user.email or '').strip()
            order_phone = getattr(request.user, 'phone', '') or ''
            order_address = getattr(request.user, 'address', '') or ''
            return render(request, 'core/order.html', {
                'food_item': food_item,
                'order_name': order_name,
                'order_phone': order_phone,
                'order_address': order_address,
            })
        if delivery_time:
            delivery_time = delivery_time + ' (preferred)'
        else:
            delivery_time = 'Will be confirmed'

        chef = food_item.chef if food_item else None
        customer = request.user
        dish_name = food_item.name if food_item else request.POST.get('dish', 'thali')
        dish_key = ''
        if not food_item:
            dish_key = request.POST.get('dish', 'thali')

        Order.objects.create(
            chef=chef,
            customer=customer,
            food_item=food_item,
            name=name,
            phone=phone,
            address=address,
            dish=dish_key,
            quantity=quantity,
            total=total,
            delivery_time=delivery_time,
            notes=notes,
            status='pending' if chef else 'confirmed',
        )
        order_obj = Order.objects.latest('created_at')
        request.session['last_order_id'] = order_obj.id
        return redirect('core:order_confirmation', order_id=order_obj.id)

    # Pre-fill name, phone, address from logged-in user's profile (registration data)
    order_name = ''
    order_phone = ''
    order_address = ''
    if request.user.is_authenticated:
        user = request.user
        order_name = (user.get_full_name() or user.first_name or user.email or '').strip()
        order_phone = getattr(user, 'phone', '') or ''
        order_address = getattr(user, 'address', '') or ''

    return render(request, 'core/order.html', {
        'food_item': food_item,
        'order_name': order_name,
        'order_phone': order_phone,
        'order_address': order_address,
    })


def order_confirmation(request, order_id):
    order_obj = get_object_or_404(Order, id=order_id)
    return render(request, 'core/order_confirmation.html', {'order': order_obj})


def _user_role(user):
    """Return role 'customer' or 'chef' for templates (works with CustomUser.user_type)."""
    if not user.is_authenticated:
        return None
    return getattr(user, 'user_type', None)


@login_required(login_url='core:login')
def customer_dashboard(request):
    if _user_role(request.user) != 'customer':
        messages.warning(request, 'Only customers can access My Orders.')
        return redirect('core:index')
    orders = Order.objects.filter(customer=request.user).select_related('chef', 'food_item')
    return render(request, 'core/customer_dashboard.html', {'orders': orders})


def login_view(request):
    next_url = request.GET.get('next') or request.POST.get('next', '')
    if request.user.is_authenticated:
        if next_url and url_has_allowed_host_and_scheme(next_url, allowed_hosts=request.get_host()):
            return redirect(next_url)
        if _user_role(request.user) == 'chef':
            return redirect('core:chef_dashboard')
        return redirect('core:index')
    if request.method == 'POST':
        email = request.POST.get('username', '').strip().lower()
        password = request.POST.get('password', '')
        user = authenticate(request, username=email, password=password)
        if user is not None:
            auth_login(request, user)
            next_url = request.POST.get('next', '')
            if next_url and url_has_allowed_host_and_scheme(next_url, allowed_hosts=request.get_host()):
                messages.success(request, 'Welcome back! You can now place your order.')
                return redirect(next_url)
            if _user_role(user) == 'chef':
                messages.success(request, 'Welcome back, Chef!')
                return redirect('core:chef_dashboard')
            messages.success(request, 'Welcome back! You are now logged in.')
            return redirect('core:index')
        messages.error(request, 'Invalid email or password. Please try again.')
    return render(request, 'core/login.html', {'next': next_url})


def register_view(request):
    if request.user.is_authenticated:
        if _user_role(request.user) == 'chef':
            return redirect('core:chef_dashboard')
        return redirect('core:index')
    if request.method == 'POST':
        email = request.POST.get('email', '').strip().lower()
        name = request.POST.get('name', '').strip()
        password1 = request.POST.get('password1', '')
        password2 = request.POST.get('password2', '')
        user_type = request.POST.get('userType', 'customer')
        if user_type not in ('customer', 'chef'):
            user_type = 'customer'
        phone = request.POST.get('phone', '').strip()
        address = request.POST.get('address', '').strip()
        speciality = request.POST.get('speciality', '').strip() if user_type == 'chef' else ''
        terms = request.POST.get('terms') == 'on'

        errors = []

        if not name:
            errors.append('Full name is required.')
        elif len(name) < 2:
            errors.append('Full name must be at least 2 characters.')

        if not email:
            errors.append('Email is required.')
        elif not EMAIL_REGEX.match(email):
            errors.append('Enter a valid email address.')
        elif User.objects.filter(email=email).exists():
            errors.append('An account with this email already exists.')

        if not phone:
            errors.append('Phone number is required.')
        else:
            digits_only = re.sub(r'\D', '', phone)
            if len(digits_only) < 10:
                errors.append('Enter a valid phone number (at least 10 digits).')

        if not address:
            errors.append('Address is required.')
        elif len(address) < 10:
            errors.append('Address must be at least 10 characters.')

        if user_type == 'chef' and not speciality:
            errors.append('Please tell us your cooking speciality (for chefs).')

        if not password1:
            errors.append('Password is required.')
        else:
            if len(password1) < 8:
                errors.append('Password must be at least 8 characters.')
            elif password1 != password2:
                errors.append('Passwords do not match.')
            else:
                try:
                    validate_password(password1, User(email=email, first_name=name))
                except ValidationError as e:
                    errors.extend(e.messages)

        if not terms:
            errors.append('You must agree to the terms & conditions.')

        if errors:
            for e in errors:
                messages.error(request, e)
            context = {
                'form_data': {
                    'name': name,
                    'email': email,
                    'phone': phone,
                    'address': address,
                    'userType': user_type,
                    'speciality': speciality,
                }
            }
            return render(request, 'core/register.html', context)

        User.objects.create_user(
            email=email,
            password=password1,
            first_name=name,
            phone=phone,
            address=address,
            user_type=user_type,
            speciality=speciality or '',
        )
        messages.success(request, 'Account created successfully! Please log in with your email and password.')
        return redirect('core:login')
    return render(request, 'core/register.html', {'form_data': {}})


def contact(request):
    if request.method == 'POST':
        messages.success(request, 'Thank you! Your message has been sent. We will get back to you soon.')
        return redirect('core:contact')
    return render(request, 'core/contact.html')


def chef_profile(request):
    # Only show chefs who have at least one food item available for sell (servings_available > 0)
    chefs = (
        User.objects.filter(user_type='chef')
        .filter(food_items__servings_available__gt=0)
        .distinct()
        .annotate(
            food_count=Count('food_items', distinct=True, filter=Q(food_items__servings_available__gt=0)),
            review_count=Count('food_items__reviews', distinct=True),
            avg_rating=Avg('food_items__reviews__rating'),
        )
    )
    return render(request, 'core/chef_profile.html', {'chefs': chefs})


def food_details(request, item_id):
    food_item = get_object_or_404(FoodItem.objects.select_related('chef'), id=item_id)
    reviews = food_item.reviews.select_related('customer').all()[:50]
    from django.db.models import Avg
    avg_rating = food_item.reviews.aggregate(Avg('rating'))['rating__avg'] or 0
    review_count = food_item.reviews.count()

    if request.method == 'POST' and request.user.is_authenticated:
        if _user_role(request.user) != 'customer':
            messages.warning(request, 'Only customers can leave reviews.')
        else:
            rating = request.POST.get('rating')
            text = request.POST.get('review_text', '').strip()
            try:
                rating = int(rating)
                if 1 <= rating <= 5 and text:
                    Review.objects.get_or_create(
                        food_item=food_item,
                        customer=request.user,
                        defaults={'rating': rating, 'text': text}
                    )
                    messages.success(request, 'Thank you! Your review has been added.')
                else:
                    messages.error(request, 'Please select a rating (1-5) and write a review.')
            except (ValueError, TypeError):
                messages.error(request, 'Invalid rating.')
        return redirect('core:food_details', item_id=item_id)

    return render(request, 'core/food_details.html', {
        'food_item': food_item,
        'reviews': reviews,
        'avg_rating': round(float(avg_rating), 1),
        'review_count': review_count,
        'is_available': (food_item.servings_available or 0) > 0,
    })


@login_required(login_url='core:login')
def chef_dashboard(request):
    if _user_role(request.user) != 'chef':
        messages.warning(request, 'Only chefs can access the Chef Dashboard.')
        return redirect('core:index')

    chef = request.user

    # POST: post food, update order status, reply to review
    if request.method == 'POST':
        action = request.POST.get('action')
        if action == 'post_food':
            name = request.POST.get('food_name', '').strip()
            category = request.POST.get('category', 'other')
            price = request.POST.get('price')
            description = request.POST.get('description', '').strip()
            servings = request.POST.get('servings_available', 10)
            availability = request.POST.get('availability', 'daily')
            image_url = request.POST.get('image_url', '').strip()
            is_veg = request.POST.get('is_vegetarian') == 'on'
            is_spicy = request.POST.get('is_spicy') == 'on'
            image_file = request.FILES.get('image')
            if name and price:
                try:
                    item = FoodItem(
                        chef=chef,
                        name=name,
                        category=category,
                        price=Decimal(price),
                        description=description,
                        servings_available=int(servings) if str(servings).isdigit() else 10,
                        availability=availability,
                        image_url=image_url,
                        is_vegetarian=is_veg,
                        is_spicy=is_spicy,
                    )
                    if image_file:
                        item.image = image_file
                    item.save()
                    messages.success(request, 'Food item posted! It will appear on the home page.')
                except Exception as e:
                    messages.error(request, f'Could not save: {e}')
            else:
                messages.error(request, 'Name and price are required.')
            return redirect('core:chef_dashboard')

        if action == 'order_status':
            order_id = request.POST.get('order_id')
            new_status = request.POST.get('status')
            if order_id and new_status:
                order_obj = Order.objects.filter(chef=chef, id=order_id).first()
                if order_obj and new_status in dict(Order.STATUS_CHOICES):
                    order_obj.status = new_status
                    order_obj.save()
                    # When marked delivered, reduce food item servings; remove from listings when 0
                    if new_status == 'delivered' and order_obj.food_item_id:
                        fi = order_obj.food_item
                        fi.servings_available = max(0, (fi.servings_available or 0) - order_obj.quantity)
                        fi.save()
                    messages.success(request, 'Order status updated.')
            return redirect('core:chef_dashboard')

        if action == 'review_reply':
            review_id = request.POST.get('review_id')
            reply = request.POST.get('chef_reply', '').strip()
            if review_id:
                review_obj = Review.objects.filter(food_item__chef=chef, id=review_id).first()
                if review_obj:
                    review_obj.chef_reply = reply
                    review_obj.save()
                    messages.success(request, 'Reply saved.')
            return redirect('core:chef_dashboard')

        if action == 'delete_food':
            food_item_id = request.POST.get('food_item_id')
            if food_item_id:
                item = FoodItem.objects.filter(chef=chef, id=food_item_id).first()
                if item:
                    item_name = item.name
                    item.delete()
                    messages.success(request, f'"{item_name}" has been removed.')
                else:
                    messages.error(request, 'Food item not found or you cannot delete it.')
            return redirect('core:chef_dashboard')

    # GET: dashboard data — only this chef's posted food items and related orders/reviews
    orders = Order.objects.filter(chef=chef).select_related('customer', 'food_item').order_by('-created_at')[:50]
    delivered_orders = Order.objects.filter(chef=chef, status='delivered').select_related('food_item').order_by('-created_at')[:30]
    reviews = Review.objects.filter(food_item__chef=chef).select_related('customer', 'food_item').order_by('-created_at')[:50]
    food_items = FoodItem.objects.filter(chef=chef, servings_available__gt=0)
    chef_food_items = FoodItem.objects.filter(chef=chef).order_by('-created_at')

    # Earnings: sum of total for delivered (or all non-cancelled) orders
    from django.db.models.functions import Coalesce
    delivered = Order.objects.filter(chef=chef, status='delivered')
    earnings_total = 0
    for o in delivered:
        earnings_total += _parse_total(o.total)
    this_month = delivered.filter(created_at__month=timezone.now().month, created_at__year=timezone.now().year)
    earnings_month = sum(_parse_total(o.total) for o in this_month)

    pending_count = Order.objects.filter(chef=chef).filter(status='pending').count()
    completed_count = Order.objects.filter(chef=chef).filter(status='delivered').count()
    from django.db.models import Avg
    avg_rating = Review.objects.filter(food_item__chef=chef).aggregate(Avg('rating'))['rating__avg'] or 0

    return render(request, 'core/chef_dashboard.html', {
        'orders': orders,
        'delivered_orders': delivered_orders,
        'reviews': reviews,
        'food_items': food_items,
        'chef_food_items': chef_food_items,
        'pending_count': pending_count,
        'completed_count': completed_count,
        'earnings_total': int(earnings_total),
        'earnings_month': int(earnings_month),
        'avg_rating': round(float(avg_rating), 1),
    })


def logout_view(request):
    auth_logout(request)
    messages.success(request, 'You have been logged out.')
    return redirect('core:index')
