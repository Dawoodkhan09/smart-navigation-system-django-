"""
URL configuration for campus_navigation project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path
from django.views.generic import TemplateView

urlpatterns = [
    path('admin/', admin.site.urls),

    # Served from the root urlconf (not static/) so /sw.js's default
    # service-worker scope is the whole site, not just /static/campus/js/.
    path('manifest.webmanifest', TemplateView.as_view(
        template_name='campus/app/manifest.webmanifest', content_type='application/manifest+json',
    ), name='pwa-manifest'),
    path('sw.js', TemplateView.as_view(
        template_name='campus/app/sw.js', content_type='application/javascript',
    ), name='pwa-service-worker'),

    # Android TWA (Trusted Web Activity) verification - see
    # settings.ANDROID_PACKAGE_NAME/ANDROID_SHA256_FINGERPRINT and the
    # README's "Android app (PWABuilder)" section.
    path('.well-known/assetlinks.json', TemplateView.as_view(
        template_name='campus/app/assetlinks.json', content_type='application/json',
        extra_context={
            'package_name': settings.ANDROID_PACKAGE_NAME,
            'fingerprint': settings.ANDROID_SHA256_FINGERPRINT,
        },
    ), name='android-asset-links'),

    path('', include('campus.urls')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
