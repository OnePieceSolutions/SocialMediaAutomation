from django.shortcuts import redirect
from django.urls import reverse
from django.conf import settings
import re

class LoginRequiredMiddleware:
    """
    Middleware that redirects unauthenticated users to signin or signup page,
    except for authentication URLs and static/media files.
    """
    def __init__(self, get_response):
        self.get_response = get_response
        self.exempt_urls = [
            reverse('clientManagement:signin'),
            reverse('clientManagement:signup'),
        ]
        if hasattr(settings, 'LOGIN_EXEMPT_URLS'):
            self.exempt_urls += [re.compile(expr) for expr in settings.LOGIN_EXEMPT_URLS]

    def __call__(self, request):
        path = request.path_info
        if not request.user.is_authenticated:
            if path in self.exempt_urls or path.startswith(settings.STATIC_URL) or path.startswith(settings.MEDIA_URL):
                return self.get_response(request)
            return redirect('clientManagement:signin')
        return self.get_response(request)