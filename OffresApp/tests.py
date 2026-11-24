from datetime import timedelta
from decimal import Decimal

from django.core.exceptions import ValidationError
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from EntreprisesApp.models import Entreprise, Utilisateur
from ExpeditionsApp.models import Expedition
from VehiculesApp.models import Vehicule

from .models import Offre


class OffreBaseTestCase(TestCase):
    @classmethod
    def setUpTestData(cls):
        def compte(username):
            return Utilisateur.objects.create_user(username, f'{username}@gmail.com', 'x12345678')

        cls.user_chargeur, cls.user_t1, cls.user_t2 = compte('chargeur'), compte('t1'), compte('t2')
        cls.chargeur = Entreprise.objects.create(
            raison_sociale='Chargeur', matricule_fiscal='5555555AAM000', type_entreprise='chargeur',
            adresse='Avenue de Carthage 20, 1000 Tunis', utilisateur=cls.user_chargeur,
        )
        cls.t1 = Entreprise.objects.create(
            raison_sociale='T1', matricule_fiscal='6666666AAM000', type_entreprise='transporteur',
            adresse='Zone industrielle Charguia, 2035 Tunis', utilisateur=cls.user_t1,
        )
        cls.t2 = Entreprise.objects.create(
            raison_sociale='T2', matricule_fiscal='7777777AAM000', type_entreprise='transporteur',
            adresse='Route de Gabès km 4, 3000 Sfax', utilisateur=cls.user_t2,
        )

    def setUp(self):
        self.v1 = Vehicule.objects.create(immatriculation='10 TU 1', type_vehicule='camion_porteur',
                                          capacite_kg=10_000, entreprise=self.t1)
        self.v2 = Vehicule.objects.create(immatriculation='20 TU 2', type_vehicule='semi_remorque',
                                          capacite_kg=25_000, entreprise=self.t2)
        self.exp = Expedition.objects.create(
            ville_depart='Tunis', ville_arrivee='Sfax', poids_kg=Decimal('2000'),
            date_souhaitee=timezone.now().date() + timedelta(days=5), entreprise=self.chargeur,
        )

    def offre(self, transporteur=None, vehicule=None, **kwargs):
        return Offre.objects.create(
            expedition=kwargs.pop('expedition', self.exp), transporteur=transporteur or self.t1,
            vehicule=vehicule or self.v1, prix=kwargs.pop('prix', Decimal('500')),
            delai_jours=kwargs.pop('delai_jours', 2), **kwargs,
        )


class ReglesMetierTests(OffreBaseTestCase):
    def test_validateurs_prix_et_delai(self):
        with self.assertRaises(ValidationError):
            self.offre(prix=Decimal('0'))
        with self.assertRaises(ValidationError):
            self.offre(delai_jours=0)

    def test_regle1_transporteur_uniquement(self):
        with self.assertRaises(ValidationError):
            self.offre(transporteur=self.chargeur)

    def test_regle2_vehicule_meme_entreprise(self):
        with self.assertRaises(ValidationError):
            self.offre(transporteur=self.t1, vehicule=self.v2)

    def test_regle3_expedition_publiee(self):
        self.exp.statut = Expedition.ANNULEE
        self.exp.save()
        with self.assertRaises(ValidationError):
            self.offre()

    def test_regle4_pas_de_doublon_proposee(self):
        self.offre()
        with self.assertRaises(ValidationError):
            self.offre()

    def test_regle5_cascade_acceptation(self):
        o1 = self.offre()
        o2 = self.offre(transporteur=self.t2, vehicule=self.v2)
        o1.statut = Offre.ACCEPTEE
        o1.save()
        self.exp.refresh_from_db()
        o2.refresh_from_db()
        self.v1.refresh_from_db()
        self.assertEqual(self.exp.statut, Expedition.ATTRIBUEE)
        self.assertEqual(o2.statut, Offre.REFUSEE)
        self.assertFalse(self.v1.disponible)

    def test_regle5_piege_update(self):
        """.update() contourne save() : la cascade ne se déclenche pas (atelier Admin §VII)."""
        o1 = self.offre()
        o2 = self.offre(transporteur=self.t2, vehicule=self.v2)
        Offre.objects.filter(pk=o1.pk).update(statut=Offre.ACCEPTEE)
        self.exp.refresh_from_db()
        o2.refresh_from_db()
        self.assertEqual(self.exp.statut, Expedition.PUBLIEE)
        self.assertEqual(o2.statut, Offre.PROPOSEE)

    def test_regle6_vehicule_indisponible(self):
        self.v1.disponible = False
        self.v1.save()
        with self.assertRaises(ValidationError):
            self.offre()

    def test_regle7_compatibilite_poids(self):
        lourde = Expedition.objects.create(
            ville_depart='Tunis', ville_arrivee='Gabès', poids_kg=Decimal('15000'),
            date_souhaitee=timezone.now().date(), entreprise=self.chargeur,
        )
        with self.assertRaises(ValidationError):
            self.offre(expedition=lourde)  # camion porteur de 10 t
        self.offre(expedition=lourde, transporteur=self.t2, vehicule=self.v2)  # semi OK


class OffreVuesTests(OffreBaseTestCase):
    def setUp(self):
        super().setUp()
        self.client.force_login(self.user_t1)

    def test_creation_mass_assignment_corrige(self):
        url = reverse('offres:ajouter')
        r = self.client.post(url, {
            'expedition': self.exp.pk, 'vehicule': self.v1.pk, 'prix': '700', 'delai_jours': 3,
            'statut': 'acceptee', 'transporteur': self.t2.pk,  # tentatives d'injection
        })
        self.assertRedirects(r, reverse('expeditions:detail', args=[self.exp.reference]))
        offre = Offre.objects.get()
        self.assertEqual(offre.statut, Offre.PROPOSEE)
        self.assertEqual(offre.transporteur, self.t1)
        self.exp.refresh_from_db()
        self.assertEqual(self.exp.statut, Expedition.PUBLIEE)

    def test_creation_doublon_affiche_erreur_pas_500(self):
        self.offre()
        url = reverse('offres:ajouter')
        r = self.client.post(url, {'expedition': self.exp.pk, 'vehicule': self.v1.pk,
                                   'prix': '650', 'delai_jours': 2})
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, 'déjà une offre proposée')
        self.assertEqual(Offre.objects.count(), 1)

    def test_vehicule_d_un_autre_transporteur_refuse(self):
        url = reverse('offres:ajouter')
        r = self.client.post(url, {'expedition': self.exp.pk, 'vehicule': self.v2.pk,
                                   'prix': '650', 'delai_jours': 2})
        self.assertEqual(r.status_code, 200)
        self.assertFalse(Offre.objects.exists())

    def test_creation_reservee_aux_transporteurs(self):
        url = reverse('offres:ajouter')
        self.client.force_login(self.user_chargeur)
        self.assertEqual(self.client.get(url).status_code, 403)
        self.client.logout()
        self.assertRedirects(self.client.get(url), f"{reverse('login')}?next={url}")

    def test_accepter_reserve_au_chargeur_proprietaire(self):
        o1 = self.offre()
        # Un transporteur (même connecté) ne peut pas accepter : l'offre est introuvable pour lui
        self.assertEqual(self.client.post(reverse('offres:accepter', args=[o1.pk])).status_code, 404)
        o1.refresh_from_db()
        self.assertEqual(o1.statut, Offre.PROPOSEE)

    def test_offre_d_un_autre_transporteur_404(self):
        o2 = self.offre(transporteur=self.t2, vehicule=self.v2)
        for nom in ('offres:modifier', 'offres:supprimer'):
            self.assertEqual(self.client.get(reverse(nom, args=[o2.pk])).status_code, 404, nom)
        self.assertEqual(self.client.post(reverse('offres:retirer', args=[o2.pk])).status_code, 404)
        o2.refresh_from_db()
        self.assertEqual(o2.statut, Offre.PROPOSEE)

    def test_modifier_son_offre(self):
        o1 = self.offre()
        r = self.client.post(reverse('offres:modifier', args=[o1.pk]), {'prix': '480', 'delai_jours': 1})
        self.assertRedirects(r, reverse('offres:detail', args=[o1.pk]))
        o1.refresh_from_db()
        self.assertEqual(o1.prix, Decimal('480'))

    def test_accepter_post_uniquement_et_cascade(self):
        o1 = self.offre()
        o2 = self.offre(transporteur=self.t2, vehicule=self.v2)
        self.client.force_login(self.user_chargeur)
        self.assertEqual(self.client.get(reverse('offres:accepter', args=[o1.pk])).status_code, 405)
        self.client.post(reverse('offres:accepter', args=[o1.pk]))
        o2.refresh_from_db()
        self.exp.refresh_from_db()
        self.assertEqual(o2.statut, Offre.REFUSEE)
        self.assertEqual(self.exp.statut, Expedition.ATTRIBUEE)

    def test_pages_principales(self):
        o = self.offre()
        for url in [reverse('accueil'), reverse('offres:liste'), reverse('offres:detail', args=[o.pk]),
                    reverse('entreprises:liste'), reverse('entreprises:detail', args=[self.t1.pk]),
                    reverse('entreprises:detail', args=[self.chargeur.pk]),
                    reverse('vehicules:liste'), reverse('vehicules:mes'), reverse('offres:ajouter')]:
            self.assertEqual(self.client.get(url).status_code, 200, url)


class HealthCheckTests(OffreBaseTestCase):
    def test_detecte_incoherence_update(self):
        admin = Utilisateur.objects.create_superuser('root', 'root@gmail.com', 'x12345678')
        self.client.force_login(admin)
        o1 = self.offre()
        Offre.objects.filter(pk=o1.pk).update(statut=Offre.ACCEPTEE)
        r = self.client.get(reverse('admin:health_check'))
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, 'Offre acceptée sur une expédition non attribuée')
        self.assertContains(r, self.exp.reference)
        self.assertContains(r, 'Incohérence de disponibilité')

    def test_reserve_au_staff(self):
        r = self.client.get(reverse('admin:health_check'))
        self.assertEqual(r.status_code, 302)
