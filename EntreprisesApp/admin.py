from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import Utilisateur, entreprise

@admin.register(Utilisateur)
class UtilisateurAdmin(UserAdmin):
  list_display = ('user_id', 'username', 'email', 'role', 'is_staff')
  readonly_fields = ('user_id', 'created_at', 'updated_at')
  fieldsets = UserAdmin.fieldsets + (
      ('TransConnect Infos', {'fields': ('user_id', 'role', 'telephone')}),
  )


@admin.register(entreprise)
class EntrepriseAdmin(admin.ModelAdmin):
  list_display = (
      'raison_sociale',
      'matricule',
      'type_entreprise',
      'utilisateur',
  )
  search_fields = ('raison_sociale', 'matricule')
  list_filter = ('type_entreprise',)

  fieldsets = (
      (
          'Identité entreprise',
          {
              'fields': (
                  'raison_sociale',
                  'matricule',
                  'type_entreprise',
                  'adresse',
              )
          },
      ),
      ('Compte Utilisateur Associé', {'fields': ('utilisateur',)}),
      ('Suivi', {'fields': ('created_at', 'updated_at')}),
  )
  readonly_fields = ('created_at', 'updated_at')