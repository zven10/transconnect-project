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
