from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from VehiculesApp.models import Vehicule

from .models import Entreprise, Utilisateur


@admin.register(Utilisateur)
class UtilisateurAdmin(UserAdmin):
    list_display = ('user_id', 'username', 'email', 'first_name', 'last_name', 'role', 'is_staff')
    list_filter = ('role', 'is_staff', 'is_active')
    search_fields = ('user_id', 'username', 'email', 'first_name', 'last_name')
    list_editable = ('role',)
    ordering = ('-created_at',)
    date_hierarchy = 'created_at'
    list_per_page = 25
    readonly_fields = ('user_id', 'created_at', 'updated_at', 'last_login', 'date_joined')
    fieldsets = (
        ('Identifiants', {'fields': ('user_id', 'username', 'password')}),
        ('Informations personnelles', {'fields': ('first_name', 'last_name', 'email', 'telephone', 'role')}),
        ('Permissions', {
            'classes': ('collapse',),
            'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions'),
        }),
        ('Suivi', {'fields': ('last_login', 'date_joined', 'created_at', 'updated_at')}),
    )
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('username', 'email', 'first_name', 'last_name', 'telephone',
                       'password1', 'password2'),
        }),
    )


class VehiculeInline(admin.TabularInline):
    model = Vehicule
    extra = 0
    fields = ('immatriculation', 'type_vehicule', 'capacite_kg', 'disponible')


@admin.register(Entreprise)
class EntrepriseAdmin(admin.ModelAdmin):
    list_display = ('raison_sociale', 'matricule_fiscal', 'type_entreprise', 'utilisateur', 'created_at')
    list_filter = ('type_entreprise',)
    search_fields = ('raison_sociale', 'matricule_fiscal')
    list_editable = ('type_entreprise',)
    ordering = ('raison_sociale',)
    date_hierarchy = 'created_at'
    list_per_page = 25
    autocomplete_fields = ('utilisateur',)
    readonly_fields = ('created_at', 'updated_at')
    fieldsets = (
        ('Identité entreprise', {'fields': ('raison_sociale', 'matricule_fiscal', 'type_entreprise', 'adresse')}),
        ('Compte utilisateur associé', {'fields': ('utilisateur',)}),
        ('Suivi', {'fields': ('created_at', 'updated_at')}),
    )
    inlines = [VehiculeInline]
