from functools import wraps

from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied


def role_required(*roles):
    """Allow only logged-in users whose role is in ``roles``.

    Anonymous visitors are sent to the login page (via login_required).
    Logged-in users with the wrong role get a 403 Forbidden page, so a USER
    cannot open an ADMIN page by typing its URL (and the other way round).
    """

    def decorator(view_func):
        @login_required
        @wraps(view_func)
        def _wrapped(request, *args, **kwargs):
            if request.user.role not in roles:
                raise PermissionDenied
            return view_func(request, *args, **kwargs)

        return _wrapped

    return decorator
