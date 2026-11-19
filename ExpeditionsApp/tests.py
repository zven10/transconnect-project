from datetime import timedelta
from decimal import Decimal

from django.core.exceptions import ValidationError
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from EntreprisesApp.models import Entreprise, Utilisateur

from .models import Expedition


class ExpeditionTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.chargeur = Entreprise.objects.create(
            raison_sociale='Chargeur SA', matricule_fiscal='3333333AAM000', type_entreprise='chargeur',
            adresse='Rue Charles de Gaulle, 1000 Tunis',
        )
        cls.transporteur = Entreprise.objects.create(
            raison_sociale='Transp SA', matricule_fiscal='4444444AAM000', type_entreprise='transporteur',
            adresse='Route de Sousse km 5, 2033 Megrine',
        )

    def _exp(self, **kwargs):
        data = dict(ville_depart='Tunis', ville_arrivee='Sfax', poids_kg=Decimal('500'),
                    date_souhaitee=timezone.now().date() + timedelta(days=3), entreprise=self.chargeur)
        data.update(kwargs)
        return Expedition.objects.create(**data)

    def test_reference_format_et_compteur(self):
        yy = f'{timezone.now():%y}'
        self.assertEqual(self._exp().reference, f'EXP-{yy}-00001')
        self.assertEqual(self._exp().reference, f'EXP-{yy}-00002')

    def test_statut_par_defaut_publiee(self):
        self.assertEqual(self._exp().statut, Expedition.PUBLIEE)

    def test_poids_nul_refuse(self):
        with self.assertRaises(ValidationError):
            self._exp(poids_kg=Decimal('0'))

    def test_entreprise_doit_etre_chargeur(self):
        with self.assertRaises(ValidationError):
            self._exp(entreprise=self.transporteur)

    def test_vues_liste_detail(self):
        exp = self._exp()
        self.assertContains(self.client.get(reverse('expeditions:liste')), exp.reference)
        self.assertContains(self.client.get(reverse('expeditions:detail', args=[exp.reference])), 'Sfax')
        self.assertEqual(self.client.get(reverse('expeditions:detail', args=['EXP-00-99999'])).status_code, 404)

    def test_creation_entreprise_fixee_cote_serveur(self):
        url = reverse('expeditions:ajouter', args=[self.chargeur.pk])
        r = self.client.post(url, {
            'ville_depart': 'Bizerte', 'ville_arrivee': 'Gabès', 'poids_kg': '1000',
            'date_souhaitee': (timezone.now().date() + timedelta(days=5)).isoformat(),
            'description': '', 'entreprise': self.transporteur.pk, 'statut': 'livree',
        })
        exp = Expedition.objects.get(ville_depart='Bizerte')
        self.assertRedirects(r, reverse('expeditions:detail', args=[exp.reference]))
        self.assertEqual(exp.entreprise, self.chargeur)  # champ injecté ignoré
        self.assertEqual(exp.statut, Expedition.PUBLIEE)  # champ injecté ignoré
        # Un transporteur ne peut pas publier
        self.assertEqual(self.client.get(reverse('expeditions:ajouter', args=[self.transporteur.pk])).status_code, 404)

    def test_action_admin_cloturer(self):
        admin = Utilisateur.objects.create_superuser('root', 'root@gmail.com', 'x12345678')
        self.client.force_login(admin)
        en_cours = self._exp(statut=Expedition.EN_COURS)
        publiee = self._exp()
        r = self.client.post(reverse('admin:ExpeditionsApp_expedition_changelist'), {
            'action': 'cloturer_expeditions', '_selected_action': [en_cours.pk, publiee.pk],
        }, follow=True)
        self.assertEqual(r.status_code, 200)
        en_cours.refresh_from_db()
        publiee.refresh_from_db()
        self.assertEqual(en_cours.statut, Expedition.LIVREE)
        self.assertEqual(publiee.statut, Expedition.PUBLIEE)
