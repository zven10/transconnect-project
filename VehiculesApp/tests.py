from django.core.exceptions import ValidationError
from django.test import TestCase
from django.urls import reverse

from EntreprisesApp.models import Entreprise

from .models import Vehicule


class VehiculeTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.transporteur = Entreprise.objects.create(
            raison_sociale='T1', matricule_fiscal='1111111AAM000', type_entreprise='transporteur',
            adresse='Zone industrielle, 2000 Ben Arous',
        )
        cls.chargeur = Entreprise.objects.create(
            raison_sociale='C1', matricule_fiscal='2222222AAM000', type_entreprise='chargeur',
            adresse='Avenue Mohamed V, 1001 Tunis',
        )

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

    def test_crud_cbv(self):
        url = reverse('vehicules:ajouter')
        r = self.client.post(url, {'immatriculation': '9 TU 9', 'type_vehicule': 'fourgon',
                                   'capacite_kg': 3000, 'entreprise': self.transporteur.pk,
                                   'disponible': 'on'})
        self.assertRedirects(r, reverse('vehicules:liste'))
        v = Vehicule.objects.get(immatriculation='9 TU 9')
        self.assertContains(self.client.get(reverse('vehicules:detail', args=[v.pk])), '9 TU 9')
        # La suppression n'a lieu qu'en POST
        self.client.get(reverse('vehicules:supprimer', args=[v.pk]))
        self.assertTrue(Vehicule.objects.filter(pk=v.pk).exists())
        self.client.post(reverse('vehicules:supprimer', args=[v.pk]))
        self.assertFalse(Vehicule.objects.filter(pk=v.pk).exists())

    def test_formulaire_refuse_entreprise_chargeur(self):
        r = self.client.post(reverse('vehicules:ajouter'), {
            'immatriculation': '8 TU 8', 'type_vehicule': 'fourgon', 'capacite_kg': 3000,
            'entreprise': self.chargeur.pk,
        })
        self.assertEqual(r.status_code, 200)
        self.assertFalse(Vehicule.objects.filter(immatriculation='8 TU 8').exists())
