from django.contrib import admin
from .models import Location, RouteQuery


@admin.register(Location)
class LocationAdmin(admin.ModelAdmin):
    list_display = ("formatted_address", "latitude", "longitude", "place_id", "created_at")
    search_fields = ("formatted_address", "address_input", "place_id")
    readonly_fields = ("address_hash", "created_at", "updated_at")
    ordering = ("-created_at",)


@admin.register(RouteQuery)
class RouteQueryAdmin(admin.ModelAdmin):
    list_display = ("origin", "destination", "distance_km", "created_at")
    readonly_fields = ("created_at",)
    ordering = ("-created_at",)
