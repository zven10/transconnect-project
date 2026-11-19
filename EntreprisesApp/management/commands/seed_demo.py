from datetime import timedelta
from decimal import Decimal

from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from EntreprisesApp.models import Entreprise, Utilisateur
from ExpeditionsApp.models import Expedition
from OffresApp.models import Offre
from VehiculesApp.models import Vehicule


class Command(BaseCommand):
    help = "Jeu de données de démonstration TransConnect (idempotent)."

    @transaction.atomic
    def handle(self, *args, **options):
        if Expedition.objects.exists():
            self.stdout.write(self.style.WARNING(
                'Des expéditions existent déjà : seed ignoré (base non vide).'
            ))
            return

        def utilisateur(username, prenom, nom, tel):
            user = Utilisateur(
                username=username, email=f'{username}@gmail.com',
                first_name=prenom, last_name=nom, telephone=tel,
            )
            user.set_password('demo12345')
            user.save()
            return user

        chargeur = Entreprise.objects.create(
            raison_sociale='Sotupa Distribution', matricule_fiscal='1234567AAM000',
            type_entreprise=Entreprise.TYPE_CHARGEUR,
            adresse='12 Avenue Habib Bourguiba, 1000 Tunis',
            utilisateur=utilisateur('sotupa.demo', 'Amira', 'Ben Salah', '22111222'),
        )
        transp_a = Entreprise.objects.create(
            raison_sociale='TransSahel Logistique', matricule_fiscal='7654321/B/A/M/000',
            type_entreprise=Entreprise.TYPE_TRANSPORTEUR,
            adresse='Zone industrielle Sidi Abdelhamid, 4061 Sousse',
            utilisateur=utilisateur('transsahel.demo', 'Karim', 'Trabelsi', '98222333'),
        )
        transp_b = Entreprise.objects.create(
            raison_sociale='Cap Bon Transport', matricule_fiscal='1112223-C-B-M-000',
            type_entreprise=Entreprise.TYPE_TRANSPORTEUR,
            adresse='Route de Tunis km 3, 8000 Nabeul',
            utilisateur=utilisateur('capbon.demo', 'Sami', 'Jebali', '55333444'),
        )
        Entreprise.objects.create(
            raison_sociale='Djerba Express (sans flotte)', matricule_fiscal='3334445DAM000',
            type_entreprise=Entreprise.TYPE_TRANSPORTEUR,
            adresse='Rue de la République, 4180 Houmt Souk Djerba',
        )

        v_a = Vehicule.objects.create(
            immatriculation='123 TU 4567', type_vehicule=Vehicule.CAMION_PORTEUR,
            capacite_kg=12_000, entreprise=transp_a,
        )
        v_b = Vehicule.objects.create(
            immatriculation='210 TU 8899', type_vehicule=Vehicule.SEMI_REMORQUE,
            capacite_kg=25_000, entreprise=transp_b,
        )
        Vehicule.objects.create(
            immatriculation='98 TU 1020', type_vehicule=Vehicule.CAMIONNETTE,
            capacite_kg=1_200, entreprise=transp_a,
        )

        aujourd_hui = timezone.now().date()
        exp1 = Expedition.objects.create(
            ville_depart='Tunis', ville_arrivee='Sfax', poids_kg=Decimal('1200'),
            date_souhaitee=aujourd_hui + timedelta(days=10), entreprise=chargeur,
            description="Expédition de démonstration (statut 'publiee') créée par seed_demo.",
        )
        exp2 = Expedition.objects.create(
            ville_depart='Sousse', ville_arrivee='Gabès', poids_kg=Decimal('8000'),
            date_souhaitee=aujourd_hui + timedelta(days=15), entreprise=chargeur,
            description='Palettes de matériaux de construction.',
        )
        Expedition.objects.create(
            ville_depart='Bizerte', ville_arrivee='Monastir', poids_kg=Decimal('3000'),
            date_souhaitee=aujourd_hui - timedelta(days=2), entreprise=chargeur,
            statut=Expedition.EN_COURS, description='Livraison en cours (test de clôture).',
        )

        Offre.objects.create(expedition=exp1, transporteur=transp_a, vehicule=v_a,
                             prix=Decimal('850'), delai_jours=2)
        Offre.objects.create(expedition=exp1, transporteur=transp_b, vehicule=v_b,
                             prix=Decimal('790'), delai_jours=3)
        Offre.objects.create(expedition=exp2, transporteur=transp_a, vehicule=v_a,
                             prix=Decimal('1900'), delai_jours=4)

        self.stdout.write(self.style.SUCCESS(
            f'Seed OK : expéditions {exp1.reference} et {exp2.reference} créées '
            f'(+ 1 expédition en cours, 4 entreprises, 3 véhicules, 3 offres).'
        ))
