"""
Multiple linear regression to estimate portions to make per food item.
Uses: rating, review count, order history, price, category, and other features.

LAST UPDATED (algorithm): sklearn LinearRegression; target = orders (quantity) in last 7 days;
features = rating/5, log1p(review_count), log1p(price), is_vegetarian, is_spicy, log1p(orders_last_7), category.
Fallback when sklearn missing: suggested = max(1, actual_last_7_days + 1).
"""
import math
from datetime import timedelta
from django.db.models import Avg, Count, Sum
from django.utils import timezone

from .models import FoodItem, Order, Review


# Category encoding for regression (same as recommendations)
CATEGORY_KEYS = ['rice', 'veg', 'non_veg', 'sweets_mithai', 'breads', 'sweets_desserts', 'pickles_sides', 'curries', 'soups', 'snacks', 'nepali', 'indian', 'other']


def _category_index(category):
    try:
        return CATEGORY_KEYS.index(category) if category in CATEGORY_KEYS else len(CATEGORY_KEYS) - 1
    except (ValueError, TypeError):
        return len(CATEGORY_KEYS) - 1


def get_estimated_portions_for_chef(chef, days_back=14):
    """
    For each food item of this chef, compute features and predict suggested portions
    using multiple linear regression. Returns list of dicts: { item, suggested_portions, ... }.
    """
    try:
        from sklearn.linear_model import LinearRegression
        import numpy as np
    except ImportError:
        return _fallback_estimates(chef)

    now = timezone.now()
    start = now - timedelta(days=days_back)

    # All food items (we need global stats to build training data)
    all_items = list(
        FoodItem.objects.filter(chef=chef)
        .annotate(
            avg_rating=Avg('reviews__rating'),
            review_count=Count('reviews'),
        )
    )
    if not all_items:
        return []

    # Order counts per item in last 7 and 14 days (for target and features)
    orders_7 = Order.objects.filter(
        chef=chef,
        status__in=('pending', 'confirmed', 'preparing', 'delivered'),
        created_at__gte=now - timedelta(days=7),
    ).exclude(food_item_id__isnull=True).values('food_item_id').annotate(
        qty=Sum('quantity')
    )
    orders_14 = Order.objects.filter(
        chef=chef,
        status__in=('pending', 'confirmed', 'preparing', 'delivered'),
        created_at__gte=now - timedelta(days=14),
    ).exclude(food_item_id__isnull=True).values('food_item_id').annotate(
        qty=Sum('quantity')
    )
    qty_7 = {r['food_item_id']: r['qty'] or 0 for r in orders_7}
    qty_14 = {r['food_item_id']: r['qty'] or 0 for r in orders_14}

    # Build feature matrix and target for items that have some history
    X_rows = []
    y_list = []
    item_ids = []
    for item in all_items:
        fid = item.id
        rating = float(item.avg_rating or 0)
        rev_count = int(item.review_count or 0)
        price = float(item.price or 0)
        cat_idx = _category_index(item.category)
        veg = 1 if item.is_vegetarian else 0
        spicy = 1 if item.is_spicy else 0
        ord_7 = qty_7.get(fid, 0) or 0
        ord_14 = qty_14.get(fid, 0) or 0
        # Features: rating, review_count (log), price (log), category one-hot (7), veg, spicy, orders_last_7 (lag)
        feat = [
            rating / 5.0,
            math.log1p(rev_count),
            math.log1p(min(price, 2000)) / 10.0,
            veg,
            spicy,
            math.log1p(ord_7),  # lag feature: last 7 days demand
        ]
        # Add simple category encoding (one number)
        feat.append(cat_idx / max(len(CATEGORY_KEYS), 1))
        X_rows.append(feat)
        # Target: orders in last 7 days (we predict "next period" similar to last 7)
        y_list.append(max(0, ord_7))
        item_ids.append(fid)

    X = np.array(X_rows)
    y = np.array(y_list)

    # Fit linear regression (even if y is all zeros, model will predict near zero)
    model = LinearRegression()
    model.fit(X, y)

    # Predict for each item
    pred = model.predict(X)
    total_pred = 0.0
    results = []
    for i, item in enumerate(all_items):
        suggested = max(0, int(round(pred[i])))
        # Clamp to reasonable range; at least 1 if they have the item listed
        suggested = max(1, min(suggested, 99))
        total_pred += suggested
        actual_7 = qty_7.get(item.id, 0) or 0
        results.append({
            'item': item,
            'suggested_portions': suggested,
            'actual_last_7_days': actual_7,
            'avg_rating': float(item.avg_rating or 0),
            'review_count': int(item.review_count or 0),
        })
    total_actual_7 = sum(qty_7.get(it.id, 0) or 0 for it in all_items)
    return {
        'estimates': results,
        'total_suggested': int(total_pred),
        'total_actual_7': total_actual_7,
    }


def _fallback_estimates(chef):
    """When sklearn is not available or no data: use simple heuristic."""
    items = list(
        FoodItem.objects.filter(chef=chef).annotate(
            avg_rating=Avg('reviews__rating'),
            review_count=Count('reviews'),
        )
    )
    from django.utils import timezone
    from datetime import timedelta
    now = timezone.now()
    orders_7 = Order.objects.filter(
        chef=chef,
        status__in=('pending', 'confirmed', 'preparing', 'delivered'),
        created_at__gte=now - timedelta(days=7),
    ).exclude(food_item_id__isnull=True).values('food_item_id').annotate(
        qty=Sum('quantity')
    )
    qty_7 = {r['food_item_id']: r['qty'] or 0 for r in orders_7}
    results = []
    total = 0
    for item in items:
        actual_7 = qty_7.get(item.id, 0) or 0
        suggested = max(1, actual_7 + 1)  # at least last week + 1
        suggested = min(suggested, 99)
        total += suggested
        results.append({
            'item': item,
            'suggested_portions': suggested,
            'actual_last_7_days': actual_7,
            'avg_rating': float(item.avg_rating or 0),
            'review_count': int(item.review_count or 0),
        })
    return {
        'estimates': results,
        'total_suggested': total,
        'total_actual_7': sum(qty_7.values()) if qty_7 else 0,
    }
