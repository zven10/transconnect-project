"""Site d'administration TransConnect : image de marque + tableau de bord d'intégrité."""
from datetime import timedelta

from django.contrib import admin
from django.db.models import Count, Exists, OuterRef, Q
from django.template.response import TemplateResponse
from django.urls import path
from django.utils import timezone


class TransConnectAdminSite(admin.AdminSite):
    site_header = 'TransConnect — Administration'
    site_title = 'TransConnect Admin'
    index_title = 'Pilotage des opérations'

    def get_urls(self):
        urls = super().get_urls()
        custom = [
            path(
                'health-check/',
                self.admin_view(self.health_check_view),
                name='health_check',
            ),
        ]
        # Les routes custom doivent précéder le catch-all <app_label>/ de l'admin
        return custom + urls

    def health_check_view(self, request):
        context = {
            **self.each_context(request),
            'title': "Contrôle d'intégrité",
            'controles': executer_controles(),
            'genere_le': timezone.now(),
        }
        return TemplateResponse(request, 'admin/health_check.html', context)


def executer_controles():
    """Contrôles d'intégrité — uniquement des requêtes ORM (filter/annotate), aucun update()."""
    from EntreprisesApp.models import Entreprise
    from ExpeditionsApp.models import Expedition
    from OffresApp.models import Offre
    from VehiculesApp.models import Vehicule

    seuil_bloquee = timezone.now() - timedelta(days=7)

    offres_orphelines = (
        Offre.objects
        .filter(statut__in=[Offre.PROPOSEE, Offre.ACCEPTEE])
        .exclude(expedition__statut__in=[Expedition.PUBLIEE, Expedition.ATTRIBUEE])
        .select_related('expedition', 'transporteur')
    )

    expeditions_bloquees = (
        Expedition.objects
        .filter(statut=Expedition.PUBLIEE, created_at__lt=seuil_bloquee)
        .select_related('entreprise')
    )

    transporteurs_sans_flotte = (
        Entreprise.objects
        .filter(type_entreprise=Entreprise.TYPE_TRANSPORTEUR)
        .annotate(nb_vehicules=Count('vehicules'))
        .filter(nb_vehicules=0)
    )

    vehicules_incoherents = (
        Vehicule.objects
        .filter(disponible=True)
        .filter(
            Exists(
                Offre.objects.filter(
                    vehicule=OuterRef('pk'),
                    statut=Offre.ACCEPTEE,
                    expedition__statut__in=[Expedition.ATTRIBUEE, Expedition.EN_COURS],
                )
            )
        )
        .select_related('entreprise')
    )

    doublons = (
        Offre.objects
        .filter(statut=Offre.PROPOSEE)
        .values('transporteur__raison_sociale', 'expedition__reference')
        .annotate(nb=Count('id'))
        .filter(nb__gt=1)
    )

    # Expédition acceptée mais pas attribuée : trace typique d'un .update() (atelier Admin, §VII)
    acceptees_non_attribuees = (
        Expedition.objects
        .filter(statut=Expedition.PUBLIEE)
        .annotate(nb_acceptees=Count('offres', filter=Q(offres__statut=Offre.ACCEPTEE)))
        .filter(nb_acceptees__gt=0)
        .select_related('entreprise')
    )

    return [
        {
            'titre': 'Offres orphelines',
            'regle': 'Règles 3 et 5 — une offre active doit viser une expédition publiée/attribuée.',
            'colonnes': ['Offre', 'Expédition', 'Statut expédition', 'Transporteur'],
            'lignes': [
                [f'#{o.pk} ({o.get_statut_display()})', o.expedition.reference,
                 o.expedition.get_statut_display(), o.transporteur.raison_sociale]
                for o in offres_orphelines
            ],
        },
        {
            'titre': 'Expéditions bloquées (> 7 jours en « publiée »)',
            'regle': "Suivi opérationnel — aucune offre acceptée depuis plus d'une semaine.",
            'colonnes': ['Référence', 'Chargeur', 'Publiée le'],
            'lignes': [
                [e.reference, e.entreprise.raison_sociale, e.created_at.strftime('%d/%m/%Y')]
                for e in expeditions_bloquees
            ],
        },
        {
            'titre': 'Transporteurs sans flotte',
            'regle': 'Règles 2 et 6 — un transporteur sans véhicule ne peut proposer aucune offre.',
            'colonnes': ['Entreprise', 'Matricule fiscal'],
            'lignes': [[e.raison_sociale, e.matricule_fiscal] for e in transporteurs_sans_flotte],
        },
        {
            'titre': 'Incohérence de disponibilité',
            'regle': 'Règles 5 et 6 — un véhicule engagé sur une offre acceptée doit être indisponible.',
            'colonnes': ['Immatriculation', 'Entreprise'],
            'lignes': [[v.immatriculation, v.entreprise.raison_sociale] for v in vehicules_incoherents],
        },
        {
            'titre': 'Doublons de proposition',
            'regle': "Règle 4 — une entreprise n'a qu'une offre « proposée » par expédition.",
            'colonnes': ['Transporteur', 'Expédition', "Nombre d'offres"],
            'lignes': [
                [d['transporteur__raison_sociale'], d['expedition__reference'], d['nb']]
                for d in doublons
            ],
        },
        {
            'titre': 'Offre acceptée sur une expédition non attribuée',
            'regle': "Règle 5 — l'acceptation doit faire passer l'expédition à « attribuée ».",
            'colonnes': ['Référence', 'Chargeur', 'Offres acceptées'],
            'lignes': [
                [e.reference, e.entreprise.raison_sociale, e.nb_acceptees]
                for e in acceptees_non_attribuees
            ],
        },
    ]
