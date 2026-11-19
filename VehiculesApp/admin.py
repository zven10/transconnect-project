from django.contrib import admin

from .models import Vehicule


@admin.register(Vehicule)
class VehiculeAdmin(admin.ModelAdmin):
    list_display = ('immatriculation', 'type_vehicule', 'capacite_kg', 'entreprise', 'disponible')
    list_filter = ('disponible', 'type_vehicule')
    search_fields = ('immatriculation', 'entreprise__raison_sociale')
    list_editable = ('disponible',)
    ordering = ('immatriculation',)
    date_hierarchy = 'created_at'
    list_per_page = 25
    autocomplete_fields = ('entreprise',)
    readonly_fields = ('created_at', 'updated_at')
    fieldsets = (
        ('Identification', {'fields': ('immatriculation', 'type_vehicule', 'entreprise')}),
        ('Capacité & disponibilité', {'fields': ('capacite_kg', 'disponible')}),
        ('Suivi', {'fields': ('created_at', 'updated_at')}),
    )
