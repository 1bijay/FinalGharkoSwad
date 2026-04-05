"""
Cosine similarity-based food recommendations using order history, reviews, and item features.

LAST UPDATED (algorithm): Recommendation logic uses cosine similarity between:
- User preference vector (from orders weighted by quantity + reviews weighted by rating)
- Item feature vectors (category, price, rating, review_count, order_count, is_vegetarian, is_spicy).
Fallback when user has no history: sort by avg_rating, then order_count, then review_count.
"""
import math
from django.db.models import Avg, Count, Sum
from django.db.models.functions import Coalesce

from .models import FoodItem, Order, Review


# Category encoding for item vector (match FoodItem.CATEGORY_CHOICES order)
CATEGORY_KEYS = ['rice', 'veg', 'non_veg', 'sweets_mithai', 'breads', 'sweets_desserts', 'pickles_sides', 'curries', 'soups', 'snacks', 'nepali', 'indian', 'other']


def _category_index(category):
    try:
        return CATEGORY_KEYS.index(category) if category in CATEGORY_KEYS else len(CATEGORY_KEYS) - 1
    except (ValueError, TypeError):
        return len(CATEGORY_KEYS) - 1


def _norm(vec):
    s = sum(x * x for x in vec)
    return math.sqrt(s) if s > 0 else 1e-10


def cosine_similarity(vec_a, vec_b):
    """Return cosine similarity between two vectors (0 to 1)."""
    if len(vec_a) != len(vec_b):
        return 0.0
    dot = sum(a * b for a, b in zip(vec_a, vec_b))
    na, nb = _norm(vec_a), _norm(vec_b)
    if na == 0 or nb == 0:
        return 0.0
    sim = dot / (na * nb)
    return max(0.0, min(1.0, sim))  # clamp to [0, 1] for possible float noise


def get_item_vector(item, order_count=0, avg_rating=0.0, review_count=0):
    """
    Build a feature vector for a food item for cosine similarity.
    Uses: category (one-hot-ish as single index normalized), price (log-normalized),
    rating, review_count, order_count, is_vegetarian, is_spicy.
    """
    cat_idx = _category_index(getattr(item, 'category', 'other'))
    # Normalize category as 7-dim: one hot style
    cat_vec = [1.0 if i == cat_idx else 0.0 for i in range(len(CATEGORY_KEYS))]
    price = float(getattr(item, 'price', 0) or 0)
    price_norm = math.log1p(price) / math.log1p(500) if price >= 0 else 0  # cap effect
    rating = float(avg_rating or 0) / 5.0
    rev_norm = math.log1p(int(review_count or 0)) / 4.0  # soft cap
    ord_norm = math.log1p(int(order_count or 0)) / 4.0
    veg = 1.0 if getattr(item, 'is_vegetarian', True) else 0.0
    spicy = 1.0 if getattr(item, 'is_spicy', False) else 0.0
    return cat_vec + [price_norm, rating, rev_norm, ord_norm, veg, spicy]


def get_user_preference_vector(user, item_vectors_map, order_counts, review_ratings):
    """
    Build a single preference vector for the user from items they ordered or reviewed.
    Weight by order count and review rating so stronger interactions count more.
    """
    if not user or not user.is_authenticated:
        return None
    weighted_sum = None
    total_weight = 0.0
    # Orders: weight by quantity
    orders = Order.objects.filter(customer=user, food_item_id__isnull=False).values('food_item_id', 'quantity')
    for o in orders:
        fid = o['food_item_id']
        qty = o.get('quantity') or 1
        if fid in item_vectors_map:
            vec = item_vectors_map[fid]
            w = float(qty)
            if weighted_sum is None:
                weighted_sum = [x * w for x in vec]
            else:
                weighted_sum = [weighted_sum[i] + vec[i] * w for i in range(len(vec))]
            total_weight += w
    # Reviews: weight by rating (1-5)
    reviews = Review.objects.filter(customer=user).values('food_item_id', 'rating')
    for r in reviews:
        fid = r['food_item_id']
        rating = r.get('rating') or 3
        if fid in item_vectors_map:
            vec = item_vectors_map[fid]
            w = float(rating) / 5.0
            if weighted_sum is None:
                weighted_sum = [x * w for x in vec]
            else:
                weighted_sum = [weighted_sum[i] + vec[i] * w for i in range(len(vec))]
            total_weight += w
    if weighted_sum is None or total_weight <= 0:
        return None
    return [x / total_weight for x in weighted_sum]


def get_recommended_food_items(user, exclude_item_ids=None, exclude_chef_id=None, top_n=24):
    """
    Return a list of FoodItem IDs recommended for the user using cosine similarity.
    - If user is logged in and has orders/reviews: recommend items similar to their preference.
    - Otherwise: fall back to popular/high-rated items (same order as before, no cosine).
    - exclude_item_ids: don't recommend these (e.g. already ordered).
    - exclude_chef_id: don't recommend items from this chef (e.g. when user is chef, exclude own).
    """
    from django.db.models import Avg, Count, Sum
    exclude_item_ids = set(exclude_item_ids or [])
    exclude_chef_id = exclude_chef_id or (user.id if user and getattr(user, 'user_type', None) == 'chef' else None)

    # All available items with aggregates
    qs = (
        FoodItem.objects.filter(servings_available__gt=0)
        .annotate(
            avg_rating=Coalesce(Avg('reviews__rating'), 0.0),
            review_count=Count('reviews'),
            order_count=Coalesce(Sum('orders__quantity'), 0),
        )
    )
    if exclude_chef_id:
        qs = qs.exclude(chef_id=exclude_chef_id)
    items = list(qs)
    if not items:
        return []

    # Build item vectors and id -> vector map
    item_vectors_map = {}
    for item in items:
        vec = get_item_vector(
            item,
            order_count=getattr(item, 'order_count', 0) or 0,
            avg_rating=getattr(item, 'avg_rating', 0) or 0,
            review_count=getattr(item, 'review_count', 0) or 0,
        )
        item_vectors_map[item.id] = vec

    # User preference from orders + reviews
    pref = get_user_preference_vector(user, item_vectors_map, None, None)

    if pref is not None:
        # Score each item by cosine similarity to user preference
        scored = []
        for item in items:
            if item.id in exclude_item_ids:
                continue
            sim = cosine_similarity(pref, item_vectors_map[item.id])
            scored.append((sim, item.id))
        scored.sort(key=lambda x: -x[0])
        return [item_id for _, item_id in scored[:top_n]]
    else:
        # Fallback: sort by rating then order count then review count
        def fallback_key(item):
            return (
                -(float(getattr(item, 'avg_rating', 0) or 0)),
                -(int(getattr(item, 'order_count', 0) or 0)),
                -(int(getattr(item, 'review_count', 0) or 0)),
            )
        sorted_items = sorted(items, key=fallback_key)
        out = []
        for item in sorted_items:
            if item.id in exclude_item_ids:
                continue
            out.append(item.id)
            if len(out) >= top_n:
                break
        return out
