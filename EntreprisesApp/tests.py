from django.core.exceptions import ValidationError
from django.test import TestCase
from django.utils import timezone

from .models import Entreprise, Utilisateur


def creer_utilisateur(username, **kwargs):
    kwargs.setdefault('email', f'{username}@gmail.com')
    return Utilisateur.objects.create_user(username=username, password='x12345678', **kwargs)


class UtilisateurTests(TestCase):
    def test_user_id_format_AAuserNN_et_compteur(self):
        yy = f'{timezone.now():%y}'
        u1 = creer_utilisateur('alice')
        u2 = creer_utilisateur('bob')
        self.assertEqual(u1.user_id, f'{yy}user00')
        self.assertEqual(u2.user_id, f'{yy}user01')
        self.assertEqual(len(u1.user_id), 8)

    def test_email_gmail_obligatoire(self):
        user = Utilisateur(username='carl', email='carl@yahoo.fr')
        with self.assertRaises(ValidationError) as ctx:
            user.full_clean()
        self.assertIn('email', ctx.exception.message_dict)

    def test_superuser_role_admin(self):
        admin = Utilisateur.objects.create_superuser('root', 'root@gmail.com', 'x12345678')
        self.assertEqual(admin.role, Utilisateur.ROLE_ADMIN)

    def test_role_auto_assigne_par_entreprise(self):
        user = creer_utilisateur('dora')
        Entreprise.objects.create(
            raison_sociale='Dora Transport', matricule_fiscal='1234567AAM000',
            type_entreprise='transporteur', adresse='Avenue de la Liberté, 1002 Tunis', utilisateur=user,
        )
        user.refresh_from_db()
        self.assertEqual(user.role, 'transporteur')


class EntrepriseTests(TestCase):
    def _entreprise(self, **kwargs):
        data = dict(raison_sociale='ACME', matricule_fiscal='1234567AAM000',
                    type_entreprise='chargeur', adresse='Rue de Marseille 10, 1000 Tunis')
        data.update(kwargs)
        return Entreprise(**data)

    def test_formats_matricule_acceptes(self):
        for mf in ['1234567AAM000', '1234567/A/A/M/000', '1234567-a-b-p-001', '1234567 A D C 000']:
            self._entreprise(matricule_fiscal=mf).full_clean()

    def test_formats_matricule_refuses(self):
        for mf in ['123456AAM000', '1234567AXM000', '1234567AAZ000', '1234567AAM00']:
            with self.assertRaises(ValidationError, msg=mf):
                self._entreprise(matricule_fiscal=mf).full_clean()

    def test_adresse_minimum_20_caracteres(self):
        with self.assertRaises(ValidationError):
            self._entreprise(adresse='Tunis').full_clean()


# ---------------------------------------------------------------------------
# Atelier Authentification
# ---------------------------------------------------------------------------

from decimal import Decimal  # noqa: E402

from django.urls import reverse  # noqa: E402

MOT_DE_PASSE = 'Tc-Motdepasse-2026'


class ConnexionTests(TestCase):
    def setUp(self):
        self.user = creer_utilisateur('karim')

    def test_page_de_connexion(self):
        r = self.client.get(reverse('login'))
        self.assertContains(r, 'Se connecter')
        self.assertContains(r, reverse('inscription'))

    def test_connexion_redirige_vers_expeditions(self):
        r = self.client.post(reverse('login'), {'username': 'karim', 'password': 'x12345678'})
        self.assertRedirects(r, reverse('expeditions:liste'))

    def test_connexion_revient_sur_next(self):
        cible = reverse('vehicules:ajouter')
        r = self.client.post(reverse('login'), {'username': 'karim', 'password': 'x12345678', 'next': cible})
        self.assertRedirects(r, cible, fetch_redirect_response=False)

    def test_deconnexion_post_uniquement(self):
        self.client.force_login(self.user)
        self.assertEqual(self.client.get(reverse('logout')).status_code, 405)
        r = self.client.post(reverse('logout'))
        self.assertRedirects(r, reverse('expeditions:liste'))
        self.assertNotIn('_auth_user_id', self.client.session)

    def test_navigation_selon_connexion(self):
        r = self.client.get(reverse('expeditions:liste'))
        self.assertContains(r, 'Créer un compte')
        self.assertNotContains(r, 'Se déconnecter')
        self.client.force_login(self.user)
        r = self.client.get(reverse('expeditions:liste'))
        self.assertContains(r, 'Connecté : <strong>karim</strong>', html=False)
        self.assertContains(r, 'Se déconnecter')
        self.assertContains(r, 'Créer mon entreprise')  # compte sans entreprise

    def test_changement_mot_de_passe_template_du_projet(self):
        self.client.force_login(self.user)
        r = self.client.get(reverse('password_change'))
        self.assertTemplateUsed(r, 'registration/password_change_form.html')
        self.assertContains(r, 'Changer mon mot de passe')


class InscriptionTests(TestCase):
    def _donnees(self, **kwargs):
        data = {'username': 'nadia', 'email': 'nadia@gmail.com', 'telephone': '22123456',
                'password1': MOT_DE_PASSE, 'password2': MOT_DE_PASSE}
        data.update(kwargs)
        return data

    def test_inscription_cree_compte_et_ouvre_la_session(self):
        r = self.client.post(reverse('inscription'), self._donnees())
        self.assertRedirects(r, reverse('entreprises:ajouter'))
        user = Utilisateur.objects.get(username='nadia')
        self.assertRegex(user.user_id, r'^\d{2}user\d{2}$')
        self.assertNotEqual(user.password, MOT_DE_PASSE)          # haché
        self.assertTrue(user.check_password(MOT_DE_PASSE))
        self.assertEqual(self.client.session['_auth_user_id'], user.pk)  # login()

    def test_champs_sensibles_ignores(self):
        self.client.post(reverse('inscription'), self._donnees(
            role='admin', is_staff='on', is_superuser='on',
        ))
        user = Utilisateur.objects.get(username='nadia')
        self.assertFalse(user.is_staff)
        self.assertFalse(user.is_superuser)
        self.assertNotEqual(user.role, Utilisateur.ROLE_ADMIN)

    def test_email_hors_gmail_refuse(self):
        r = self.client.post(reverse('inscription'), self._donnees(email='nadia@yahoo.fr'))
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, 'gmail.com')
        self.assertFalse(Utilisateur.objects.exists())

    def test_mots_de_passe_differents(self):
        r = self.client.post(reverse('inscription'), self._donnees(password2='autre-chose-123'))
        self.assertEqual(r.status_code, 200)
        self.assertFalse(Utilisateur.objects.exists())


class EntrepriseCompteTests(TestCase):
    def setUp(self):
        self.user = creer_utilisateur('sami')
        self.autre = creer_utilisateur('hela')
        self.entreprise_autre = Entreprise.objects.create(
            raison_sociale='Hela SA', matricule_fiscal='9999999AAM000', type_entreprise='chargeur',
            adresse='Rue de Rome 15, 1000 Tunis centre', utilisateur=self.autre,
        )

    def _donnees(self):
        return {'raison_sociale': 'Sami Transport', 'matricule_fiscal': '1234567AAM000',
                'type_entreprise': 'transporteur', 'adresse': 'Route de Bizerte km 7, 2080 Ariana'}

    def test_creation_reservee_aux_connectes(self):
        r = self.client.get(reverse('entreprises:ajouter'))
        self.assertRedirects(r, f"{reverse('login')}?next={reverse('entreprises:ajouter')}")

    def test_entreprise_rattachee_au_compte_connecte(self):
        self.client.force_login(self.user)
        data = self._donnees()
        data['utilisateur'] = self.autre.pk  # tentative d'injection
        r = self.client.post(reverse('entreprises:ajouter'), data)
        self.assertRedirects(r, reverse('expeditions:liste'))
        entreprise = Entreprise.objects.get(raison_sociale='Sami Transport')
        self.assertEqual(entreprise.utilisateur, self.user)
        self.user.refresh_from_db()
        self.assertEqual(self.user.role, 'transporteur')

    def test_une_seule_entreprise_par_compte(self):
        self.client.force_login(self.autre)
        r = self.client.get(reverse('entreprises:ajouter'))
        self.assertRedirects(r, reverse('entreprises:detail', args=[self.entreprise_autre.pk]))

    def test_modifier_l_entreprise_d_un_autre_404(self):
        self.client.force_login(self.user)
        Entreprise.objects.create(utilisateur=self.user, **self._donnees())
        for nom in ('entreprises:modifier', 'entreprises:supprimer'):
            r = self.client.get(reverse(nom, args=[self.entreprise_autre.pk]))
            self.assertEqual(r.status_code, 404, nom)


class ParcoursCompletTests(TestCase):
    """AA4 : inscription → entreprise → véhicule → offre → déconnexion."""

    def test_parcours_transporteur(self):
        from ExpeditionsApp.models import Expedition
        from OffresApp.models import Offre
        from VehiculesApp.models import Vehicule

        chargeur = Entreprise.objects.create(
            raison_sociale='Chargeur', matricule_fiscal='5555555AAM000', type_entreprise='chargeur',
            adresse='Avenue de Carthage 20, 1000 Tunis',
        )
        exp = Expedition.objects.create(
            ville_depart='Tunis', ville_arrivee='Sfax', poids_kg=Decimal('900'),
            date_souhaitee=timezone.now().date(), entreprise=chargeur,
        )
        c = self.client
        r = c.post(reverse('inscription'), {
            'username': 'ali', 'email': 'ali@gmail.com', 'telephone': '',
            'password1': MOT_DE_PASSE, 'password2': MOT_DE_PASSE,
        })
        self.assertRedirects(r, reverse('entreprises:ajouter'))
        c.post(reverse('entreprises:ajouter'), {
            'raison_sociale': 'Ali Logistique', 'matricule_fiscal': '7777777BAM000',
            'type_entreprise': 'transporteur', 'adresse': 'Zone industrielle, 3000 Sfax',
        })
        c.post(reverse('vehicules:ajouter'), {
            'immatriculation': '55 TU 555', 'type_vehicule': 'fourgon', 'capacite_kg': 3000, 'disponible': 'on',
        })
        vehicule = Vehicule.objects.get(immatriculation='55 TU 555')
        self.assertEqual(vehicule.entreprise.raison_sociale, 'Ali Logistique')
        r = c.post(reverse('offres:ajouter'), {
            'expedition': exp.pk, 'vehicule': vehicule.pk, 'prix': '450', 'delai_jours': 2,
        })
        self.assertRedirects(r, reverse('expeditions:detail', args=[exp.reference]))
        self.assertEqual(Offre.objects.get().transporteur.raison_sociale, 'Ali Logistique')
        c.post(reverse('logout'))
        self.assertEqual(c.get(reverse('offres:ajouter')).status_code, 302)
