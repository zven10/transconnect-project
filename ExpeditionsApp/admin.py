from django.contrib import admin, messages
from django.core.exceptions import ValidationError
from django.utils import timezone
from django.utils.html import format_html

from OffresApp.models import Offre

from .models import Expedition

COULEURS_STATUT_EXPEDITION = {
    Expedition.PUBLIEE: '#337AB7',
    Expedition.ATTRIBUEE: '#F0AD4E',
    Expedition.EN_COURS: '#5BC0DE',
    Expedition.LIVREE: '#5CB85C',
    Expedition.ANNULEE: '#777777',
}


class EnRetardFilter(admin.SimpleListFilter):
    title = 'en retard'
    parameter_name = 'en_retard'

    def lookups(self, request, model_admin):
        return [('oui', 'Oui'), ('non', 'Non')]

    def queryset(self, request, queryset):
        aujourd_hui = timezone.now().date()
        if self.value() == 'oui':
            return queryset.filter(statut=Expedition.PUBLIEE, date_souhaitee__lt=aujourd_hui)
        if self.value() == 'non':
            return queryset.exclude(statut=Expedition.PUBLIEE, date_souhaitee__lt=aujourd_hui)
        return queryset


class OffreInline(admin.StackedInline):
    model = Offre
    extra = 0
    fk_name = 'expedition'
    fields = ('transporteur', 'vehicule', 'prix', 'delai_jours', 'statut')
    readonly_fields = ('transporteur', 'vehicule', 'prix', 'delai_jours', 'statut')
    show_change_link = True
    can_delete = False

    def has_add_permission(self, request, obj=None):
        return False


@admin.register(Expedition)
class ExpeditionAdmin(admin.ModelAdmin):
    list_display = ('reference', 'entreprise', 'ville_depart', 'ville_arrivee',
                    'statut', 'statut_colore', 'date_souhaitee')
    list_filter = ('statut', 'ville_depart', EnRetardFilter)
    search_fields = ('reference', 'entreprise__raison_sociale', 'ville_depart', 'ville_arrivee')
    list_editable = ('statut',)
    ordering = ('-created_at',)
    date_hierarchy = 'date_souhaitee'
    list_per_page = 25
    autocomplete_fields = ('entreprise',)
    readonly_fields = ('reference', 'created_at', 'updated_at')
    fieldsets = (
        ('Identification', {'fields': ('reference', 'entreprise', 'statut')}),
        ('Trajet & chargement', {'fields': ('ville_depart', 'ville_arrivee', 'poids_kg',
                                            'date_souhaitee', 'description')}),
        ('Suivi', {'fields': ('created_at', 'updated_at')}),
    )
    inlines = [OffreInline]
    actions = ['cloturer_expeditions']

    @admin.display(description='Badge', ordering='statut')
    def statut_colore(self, obj):
        return format_html(
            '<span style="color:white;background:{};padding:3px 8px;border-radius:4px;">{}</span>',
            COULEURS_STATUT_EXPEDITION.get(obj.statut, '#999'),
            obj.get_statut_display(),
        )

    @admin.action(description='Clôturer les expéditions sélectionnées')
    def cloturer_expeditions(self, request, queryset):
        """Passe les expéditions « en cours » à « livrée » — boucle + full_clean() + save()."""
        traitees, erreurs = 0, []
        ignorees = queryset.exclude(statut=Expedition.EN_COURS).count()
        for expedition in queryset.filter(statut=Expedition.EN_COURS):
            expedition.statut = Expedition.LIVREE
            try:
                expedition.full_clean()
                expedition.save()
                traitees += 1
            except ValidationError as e:
                erreurs.append(f'{expedition.reference} : {"; ".join(e.messages)}')

        if traitees:
            self.message_user(request, f'{traitees} expédition(s) clôturée(s).', messages.SUCCESS)
        if ignorees:
            self.message_user(
                request,
                f"{ignorees} expédition(s) ignorée(s) : seules les expéditions « en cours » sont clôturées.",
                messages.WARNING,
            )
        for erreur in erreurs:
            self.message_user(request, erreur, messages.ERROR)
