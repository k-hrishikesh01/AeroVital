"""
URL configuration for AeroVital project.
"""

from django.contrib import admin
from django.urls import include, path

# Versioned API routes under /api/v1/
v1_patterns = [
    path("auth/", include("pilots.auth_urls")),
    path("pilots/", include("pilots.urls")),
    path("devices/", include("devices.urls")),
    path("missions/", include("missions.urls")),
    path("telemetry/", include("telemetry.urls")),
    path("intelligence/", include("intelligence.urls")),
    path("alerts/", include("alerts.urls")),
]

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/v1/", include((v1_patterns, "v1"))),

    # Top-level backward compatibility routes
    path("api/telemetry/", include("telemetry.urls")),
    path("api/intelligence/", include("intelligence.urls")),
    path("api/alerts/", include("alerts.urls")),
    path("api/missions/", include("missions.urls")),
    path("api/pilots/", include("pilots.urls")),
    path("api/devices/", include("devices.urls")),
]