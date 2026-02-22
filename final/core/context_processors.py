def user_profile(request):
    """Add user_profile to template context so we can check role (customer/chef)."""
    class ProfileRole:
        def __init__(self, role):
            self.role = role
    role = getattr(request.user, 'user_type', None) if request.user.is_authenticated else None
    return {'user_profile': ProfileRole(role) if role else None}
