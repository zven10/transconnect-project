from django.contrib import admin
from django.utils import timezone
from fastapi.exceptions import ValidationException
from flask import request_started
from numpy.ma.core import append
from pyexpat.errors import messages

from .models import Expedition
from django.core.exceptions import ValidationError


class EnRetardFilter(admin.SimpleListFilter):
    title = 'en retard'
    parameter_name = 'en_retard'

    def lookups(self, request, model_admin):
        return [('oui', 'Oui'), ('non', 'Non')]

    def queryset(self, request, queryset):
        if self.value() == 'oui':
            return super().queryset.filter(
                statut='en cours',
                date_souhaitee__lt=timezone.now().date()
            )
        if self.value() == 'non':
            return queryset.exclude(
                statut='en cours',
                date_souhaitee__lt=timezone.now().date()
            )
        return queryset


@admin.register(Expedition)
class ExpeditionAdmin(admin.ModelAdmin):
    list_filter = ('statut', 'ville_depart', EnRetardFilter)
    list_display = ('reference', 'ville_depart', 'statut')
    @admin.action(description="Colture des expeiditions selectionnees")
    def make_it_livers(self,req, queryset):
        liste_ignore=queryset.exclude(statut='en cours',flat=True).count()
        c=0
        errors=[]
        liste=queryset.filter(statut='en cours',flat=True)
        for exp in liste:
            exp.statut='livre'
            try:
                exp.save()
                c=+1
            except ValidationError as e:
                 errors.append(f"{exp.reference} : erreur lors de la sauvegarde de l'expedition {e.messages}")
        if c:
            self.message_user(req,f"{c} expeiditions ont ete colture ",messages.SUCCESS)
            if liste_ignore:
                self.message_user(request_started,e,messages.WARNING)
            for e in errors:
                self.message_user(request_started,e,messages.ERROR)
    action=['make_it_livers']
admin.site.register(Expedition,ExpeditionAdmin)