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
        def compte(username):
            return Utilisateur.objects.create_user(username, f'{username}@gmail.com', 'x12345678')

        cls.user_chargeur = compte('chargeur1')
        cls.user_chargeur2 = compte('chargeur2')
        cls.user_transporteur = compte('transp1')
        cls.chargeur = Entreprise.objects.create(
            raison_sociale='Chargeur SA', matricule_fiscal='3333333AAM000', type_entreprise='chargeur',
            adresse='Rue Charles de Gaulle, 1000 Tunis', utilisateur=cls.user_chargeur,
        )
        cls.chargeur2 = Entreprise.objects.create(
            raison_sociale='Autre Chargeur', matricule_fiscal='3333334AAM000', type_entreprise='chargeur',
            adresse='Avenue de la Liberté 40, 1002 Tunis', utilisateur=cls.user_chargeur2,
        )
        cls.transporteur = Entreprise.objects.create(
            raison_sociale='Transp SA', matricule_fiscal='4444444AAM000', type_entreprise='transporteur',
            adresse='Route de Sousse km 5, 2033 Megrine', utilisateur=cls.user_transporteur,
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
        url = reverse('expeditions:ajouter')
        self.client.force_login(self.user_chargeur)
        r = self.client.post(url, {
            'ville_depart': 'Bizerte', 'ville_arrivee': 'Gabès', 'poids_kg': '1000',
            'date_souhaitee': (timezone.now().date() + timedelta(days=5)).isoformat(),
            'description': '', 'entreprise': self.transporteur.pk, 'statut': 'livree',
        })
        exp = Expedition.objects.get(ville_depart='Bizerte')
        self.assertRedirects(r, reverse('expeditions:detail', args=[exp.reference]))
        self.assertEqual(exp.entreprise, self.chargeur)  # champ injecté ignoré
        self.assertEqual(exp.statut, Expedition.PUBLIEE)  # champ injecté ignoré
        # Un transporteur connecté ne peut pas publier (UserPassesTestMixin → 403)
        self.client.force_login(self.user_transporteur)
        self.assertEqual(self.client.get(url).status_code, 403)

    def test_formulaire_sans_champ_entreprise(self):
        self.client.force_login(self.user_chargeur)
        form = self.client.get(reverse('expeditions:ajouter')).context['form']
        self.assertEqual(list(form.fields),
                         ['ville_depart', 'ville_arrivee', 'poids_kg', 'date_souhaitee', 'description'])

    def test_suppression_anonyme_redirige_avec_next(self):
        exp = self._exp()
        url = reverse('expeditions:supprimer', args=[exp.reference])
        r = self.client.get(url)
        self.assertRedirects(r, f"{reverse('login')}?next={url}")
        # Après connexion, retour sur la page de confirmation
        r = self.client.post(reverse('login'), {'username': 'chargeur1', 'password': 'x12345678', 'next': url},
                             follow=True)
        self.assertEqual(r.redirect_chain[-1][0], url)
        self.assertContains(r, exp.reference)

    def test_chargeur_ne_touche_qu_a_ses_expeditions(self):
        exp = self._exp()  # appartient à self.chargeur
        self.client.force_login(self.user_chargeur2)
        modifier = reverse('expeditions:modifier', args=[exp.reference])
        supprimer = reverse('expeditions:supprimer', args=[exp.reference])
        self.assertEqual(self.client.get(modifier).status_code, 404)
        self.assertEqual(self.client.post(supprimer).status_code, 404)
        self.assertTrue(Expedition.objects.filter(pk=exp.pk).exists())
        self.client.force_login(self.user_chargeur)
        self.assertEqual(self.client.get(modifier).status_code, 200)
        self.client.post(supprimer)
        self.assertFalse(Expedition.objects.filter(pk=exp.pk).exists())

    def test_boutons_affiches_seulement_au_proprietaire(self):
        exp = self._exp()
        url = reverse('expeditions:detail', args=[exp.reference])
        lien_modifier = reverse('expeditions:modifier', args=[exp.reference])
        self.assertNotContains(self.client.get(url), lien_modifier)
        self.client.force_login(self.user_chargeur2)
        self.assertNotContains(self.client.get(url), lien_modifier)
        self.client.force_login(self.user_chargeur)
        self.assertContains(self.client.get(url), lien_modifier)

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
