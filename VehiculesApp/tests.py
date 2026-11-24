from django.core.exceptions import ValidationError
from django.test import TestCase
from django.urls import reverse

from EntreprisesApp.models import Entreprise, Utilisateur

from .models import Vehicule


def compte(username):
    return Utilisateur.objects.create_user(username, f'{username}@gmail.com', 'x12345678')


class VehiculeTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user_a = compte('transp_a')
        cls.user_b = compte('transp_b')
        cls.user_c = compte('chargeur_c')
        cls.transporteur = Entreprise.objects.create(
            raison_sociale='T1', matricule_fiscal='1111111AAM000', type_entreprise='transporteur',
            adresse='Zone industrielle, 2000 Ben Arous', utilisateur=cls.user_a,
        )
        cls.transporteur_b = Entreprise.objects.create(
            raison_sociale='T2', matricule_fiscal='8888888AAM000', type_entreprise='transporteur',
            adresse='Route de Gabès km 4, 3000 Sfax', utilisateur=cls.user_b,
        )
        cls.chargeur = Entreprise.objects.create(
            raison_sociale='C1', matricule_fiscal='2222222AAM000', type_entreprise='chargeur',
            adresse='Avenue Mohamed V, 1001 Tunis', utilisateur=cls.user_c,
        )

    # --- Modèle -----------------------------------------------------------
    def test_capacite_nulle_refusee(self):
        with self.assertRaises(ValidationError):
            Vehicule.objects.create(immatriculation='1 TU 1', type_vehicule='fourgon',
                                    capacite_kg=0, entreprise=self.transporteur)

    def test_entreprise_doit_etre_transporteur(self):
        with self.assertRaises(ValidationError):
            Vehicule.objects.create(immatriculation='2 TU 2', type_vehicule='fourgon',
                                    capacite_kg=1000, entreprise=self.chargeur)

    def test_capacite_coherente_avec_gabarit(self):
        with self.assertRaises(ValidationError):
            Vehicule.objects.create(immatriculation='3 TU 3', type_vehicule='camionnette',
                                    capacite_kg=5000, entreprise=self.transporteur)

    # --- Vues (atelier Authentification) ------------------------------------
    def test_crud_cbv_transporteur_connecte(self):
        self.client.force_login(self.user_a)
        r = self.client.post(reverse('vehicules:ajouter'), {
            'immatriculation': '9 TU 9', 'type_vehicule': 'fourgon', 'capacite_kg': 3000,
            'disponible': 'on', 'entreprise': self.transporteur_b.pk,  # tentative d'injection
        })
        self.assertRedirects(r, reverse('vehicules:mes'))
        v = Vehicule.objects.get(immatriculation='9 TU 9')
        self.assertEqual(v.entreprise, self.transporteur)  # fixée depuis request.user
        self.assertContains(self.client.get(reverse('vehicules:mes')), '9 TU 9')
        # La suppression n'a lieu qu'en POST
        self.client.get(reverse('vehicules:supprimer', args=[v.pk]))
        self.assertTrue(Vehicule.objects.filter(pk=v.pk).exists())
        self.client.post(reverse('vehicules:supprimer', args=[v.pk]))
        self.assertFalse(Vehicule.objects.filter(pk=v.pk).exists())

    def test_formulaire_sans_champ_entreprise(self):
        self.client.force_login(self.user_a)
        r = self.client.get(reverse('vehicules:ajouter'))
        self.assertNotIn('entreprise', r.context['form'].fields)

    def test_anonyme_redirige_vers_connexion(self):
        url = reverse('vehicules:ajouter')
        self.assertRedirects(self.client.get(url), f"{reverse('login')}?next={url}")

    def test_chargeur_interdit_403(self):
        self.client.force_login(self.user_c)
        self.assertEqual(self.client.get(reverse('vehicules:ajouter')).status_code, 403)
        self.assertEqual(self.client.get(reverse('vehicules:mes')).status_code, 403)

    def test_section_VII_vehicule_d_un_autre_transporteur(self):
        """Connecté ne veut pas dire autorisé : A ne trouve pas le véhicule de B (404)."""
        v_b = Vehicule.objects.create(immatriculation='7 TU 7', type_vehicule='fourgon',
                                      capacite_kg=2000, entreprise=self.transporteur_b)
        self.client.force_login(self.user_a)
        modifier = reverse('vehicules:modifier', args=[v_b.pk])
        supprimer = reverse('vehicules:supprimer', args=[v_b.pk])
        self.assertEqual(self.client.get(modifier).status_code, 404)
        self.assertEqual(self.client.post(modifier, {'immatriculation': '7 TU 7', 'type_vehicule': 'fourgon',
                                                     'capacite_kg': 3500}).status_code, 404)
        self.assertEqual(self.client.post(supprimer).status_code, 404)
        v_b.refresh_from_db()
        self.assertEqual(v_b.capacite_kg, 2000)
        self.assertNotContains(self.client.get(reverse('vehicules:mes')), '7 TU 7')
        # B, propriétaire, y a toujours accès
        self.client.force_login(self.user_b)
        self.assertEqual(self.client.get(modifier).status_code, 200)
