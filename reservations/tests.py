# reservations/tests.py - Tests unitaires pour les réservations

from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.utils import timezone
from django.core.exceptions import ValidationError
from datetime import date, timedelta
from decimal import Decimal

from .models import (
    Reservation, Paiement, TypePaiement, EvaluationReservation, Disponibilite
)
from .forms import ReservationForm, PaiementForm, EvaluationReservationForm
from home.models import Ville, CategorieMaison, Maison

User = get_user_model()


class ReservationModelTest(TestCase):
    """Tests pour le modèle Reservation"""
    
    def setUp(self):
        """Configuration des données de test"""
        # Créer une ville
        self.ville = Ville.objects.create(
            nom="Douala",
            code_postal="00237",
            departement="Littoral"
        )
        
        # Créer une catégorie
        self.categorie = CategorieMaison.objects.create(
            nom="Appartement",
            description="Appartement moderne"
        )
        
        # Créer un gestionnaire
        self.gestionnaire = User.objects.create_user(
            username="gestionnaire",
            email="gestionnaire@test.com",
            password="testpass123",
            role="GESTIONNAIRE"
        )
        
        # Créer un client
        self.client_user = User.objects.create_user(
            username="client",
            email="client@test.com",
            password="testpass123",
            role="CLIENT"
        )
        
        # Créer une maison
        self.maison = Maison.objects.create(
            nom="Belle Maison",
            numero="M001",
            description="Une belle maison",
            adresse="123 Rue Test",
            ville=self.ville,
            categorie=self.categorie,
            gestionnaire=self.gestionnaire,
            capacite_personnes=4,
            nombre_chambres=2,
            nombre_salles_bain=1,
            superficie=80,
            prix_par_nuit=Decimal('50000'),
            disponible=True
        )
    
    def test_creation_reservation(self):
        """Test de création d'une réservation"""
        reservation = Reservation.objects.create(
            client=self.client_user,
            maison=self.maison,
            date_debut=date.today() + timedelta(days=7),
            date_fin=date.today() + timedelta(days=10),
            nombre_personnes=2,
            prix_par_nuit=self.maison.prix_par_nuit
        )
        
        self.assertEqual(reservation.nombre_nuits, 3)
        self.assertEqual(reservation.statut, 'en_attente')
        self.assertTrue(reservation.numero.startswith('REV-'))
        self.assertEqual(reservation.sous_total, Decimal('150000'))  # 3 nuits * 50000
    
    def test_validation_dates(self):
        """Test de validation des dates"""
        # Date de début dans le passé
        with self.assertRaises(ValidationError):
            reservation = Reservation(
                client=self.client_user,
                maison=self.maison,
                date_debut=date.today() - timedelta(days=1),
                date_fin=date.today() + timedelta(days=2),
                nombre_personnes=2
            )
            reservation.full_clean()
        
        # Date de fin avant date de début
        with self.assertRaises(ValidationError):
            reservation = Reservation(
                client=self.client_user,
                maison=self.maison,
                date_debut=date.today() + timedelta(days=5),
                date_fin=date.today() + timedelta(days=3),
                nombre_personnes=2
            )
            reservation.full_clean()
    
    def test_validation_capacite(self):
        """Test de validation de la capacité"""
        with self.assertRaises(ValidationError):
            reservation = Reservation(
                client=self.client_user,
                maison=self.maison,
                date_debut=date.today() + timedelta(days=7),
                date_fin=date.today() + timedelta(days=10),
                nombre_personnes=6  # Dépasse la capacité de 4
            )
            reservation.full_clean()
    
    def test_verification_disponibilite(self):
        """Test de vérification de disponibilité"""
        # Créer une première réservation
        reservation1 = Reservation.objects.create(
            client=self.client_user,
            maison=self.maison,
            date_debut=date.today() + timedelta(days=7),
            date_fin=date.today() + timedelta(days=10),
            nombre_personnes=2,
            statut='confirmee'
        )
        
        # Vérifier qu'une réservation en conflit n'est pas possible
        disponible = Reservation.objects.verifier_disponibilite(
            self.maison,
            date.today() + timedelta(days=8),
            date.today() + timedelta(days=12)
        )
        self.assertFalse(disponible)
        
        # Vérifier qu'une réservation sans conflit est possible
        disponible = Reservation.objects.verifier_disponibilite(
            self.maison,
            date.today() + timedelta(days=15),
            date.today() + timedelta(days=18)
        )
        self.assertTrue(disponible)
    
    def test_calcul_prix(self):
        """Test du calcul des prix"""
        reservation = Reservation.objects.create(
            client=self.client_user,
            maison=self.maison,
            date_debut=date.today() + timedelta(days=7),
            date_fin=date.today() + timedelta(days=10),
            nombre_personnes=2,
            prix_par_nuit=Decimal('60000'),
            frais_service=Decimal('9000'),
            reduction_montant=Decimal('10000')
        )
        
        # Sous-total = 3 nuits * 60000 = 180000
        # Après réduction = 180000 - 10000 = 170000
        # Total = 170000 + 9000 = 179000
        self.assertEqual(reservation.sous_total, Decimal('170000'))
        self.assertEqual(reservation.prix_total, Decimal('179000'))
    
    def test_proprietes_calculees(self):
        """Test des propriétés calculées"""
        reservation = Reservation.objects.create(
            client=self.client_user,
            maison=self.maison,
            date_debut=date.today() + timedelta(days=7),
            date_fin=date.today() + timedelta(days=10),
            nombre_personnes=2,
            prix_par_nuit=Decimal('50000')
        )
        
        self.assertEqual(reservation.duree_sejour, 3)
        self.assertTrue(reservation.est_modifiable)
        self.assertTrue(reservation.est_annulable)
        self.assertEqual(reservation.temps_avant_arrivee, 7)
        self.assertFalse(reservation.est_en_cours)
    
    def test_actions_reservation(self):
        """Test des actions sur les réservations"""
        reservation = Reservation.objects.create(
            client=self.client_user,
            maison=self.maison,
            date_debut=date.today() + timedelta(days=7),
            date_fin=date.today() + timedelta(days=10),
            nombre_personnes=2
        )
        
        # Confirmer la réservation
        self.assertTrue(reservation.confirmer())
        self.assertEqual(reservation.statut, 'confirmee')
        
        # Annuler la réservation
        self.assertTrue(reservation.annuler("Test d'annulation"))
        self.assertEqual(reservation.statut, 'annulee')
        self.assertIsNotNone(reservation.date_annulation)


class TypePaiementModelTest(TestCase):
    """Tests pour le modèle TypePaiement"""
    
    def test_calcul_frais(self):
        """Test du calcul des frais"""
        type_paiement = TypePaiement.objects.create(
            nom="Carte bancaire",
            frais_pourcentage=Decimal('2.5'),
            frais_fixe=Decimal('500'),
            actif=True
        )
        
        montant = Decimal('100000')
        frais = type_paiement.calculer_frais(montant)
        # 2.5% de 100000 = 2500 + 500 = 3000
        self.assertEqual(frais, Decimal('3000'))


class PaiementModelTest(TestCase):
    """Tests pour le modèle Paiement"""
    
    def setUp(self):
        """Configuration des données de test"""
        self.ville = Ville.objects.create(nom="Douala", code_postal="00237", departement="Littoral")
        self.gestionnaire = User.objects.create_user(username="gestionnaire", email="gest@test.com", role="GESTIONNAIRE")
        self.client_user = User.objects.create_user(username="client", email="client@test.com", role="CLIENT")
        
        self.maison = Maison.objects.create(
            nom="Test Maison", numero="M001", adresse="Test", ville=self.ville,
            gestionnaire=self.gestionnaire, capacite_personnes=4, nombre_chambres=2,
            nombre_salles_bain=1, superficie=80, prix_par_nuit=Decimal('50000')
        )
        
        self.reservation = Reservation.objects.create(
            client=self.client_user, maison=self.maison,
            date_debut=date.today() + timedelta(days=7),
            date_fin=date.today() + timedelta(days=10),
            nombre_personnes=2, prix_par_nuit=Decimal('50000')
        )
        
        self.type_paiement = TypePaiement.objects.create(
            nom="Test Payment", frais_pourcentage=Decimal('2'), actif=True
        )
    
    def test_creation_paiement(self):
        """Test de création d'un paiement"""
        paiement = Paiement.objects.create(
            reservation=self.reservation,
            type_paiement=self.type_paiement,
            montant=Decimal('100000')
        )
        
        self.assertTrue(paiement.numero_transaction.startswith('PAY-'))
        self.assertEqual(paiement.statut, 'en_attente')
        self.assertEqual(paiement.frais, Decimal('2000'))  # 2% de 100000
        self.assertEqual(paiement.montant_net, Decimal('98000'))
    
    def test_validation_paiement(self):
        """Test de validation d'un paiement"""
        paiement = Paiement.objects.create(
            reservation=self.reservation,
            type_paiement=self.type_paiement,
            montant=Decimal('100000')
        )
        
        paiement.valider(reference_externe="TEST_REF", notes="Test validation")
        
        self.assertEqual(paiement.statut, 'valide')
        self.assertEqual(paiement.reference_externe, "TEST_REF")
        self.assertIsNotNone(paiement.date_validation)


class ReservationFormTest(TestCase):
    """Tests pour les formulaires de réservation"""
    
    def setUp(self):
        """Configuration des données de test"""
        self.ville = Ville.objects.create(nom="Douala", code_postal="00237", departement="Littoral")
        self.gestionnaire = User.objects.create_user(username="gestionnaire", email="gest@test.com", role="GESTIONNAIRE")
        self.client_user = User.objects.create_user(username="client", email="client@test.com", role="CLIENT")
        
        self.maison = Maison.objects.create(
            nom="Test Maison", numero="M001", adresse="Test", ville=self.ville,
            gestionnaire=self.gestionnaire, capacite_personnes=4, nombre_chambres=2,
            nombre_salles_bain=1, superficie=80, prix_par_nuit=Decimal('50000'),
            disponible=True
        )
    
    def test_formulaire_reservation_valide(self):
        """Test d'un formulaire de réservation valide"""
        form_data = {
            'date_debut': date.today() + timedelta(days=7),
            'date_fin': date.today() + timedelta(days=10),
            'nombre_personnes': 2,
            'heure_arrivee': '15:00',
            'heure_depart': '11:00',
            'mode_paiement': 'integral',
            'commentaire_client': 'Test',
            'contact_urgence_nom': 'Contact Test',
            'contact_urgence_telephone': '123456789'
        }
        
        form = ReservationForm(data=form_data, user=self.client_user, maison=self.maison)
        self.assertTrue(form.is_valid())
    
    def test_formulaire_reservation_invalide(self):
        """Test d'un formulaire de réservation invalide"""
        # Dates invalides
        form_data = {
            'date_debut': date.today() + timedelta(days=10),
            'date_fin': date.today() + timedelta(days=7),  # Date fin avant début
            'nombre_personnes': 2,
            'contact_urgence_nom': 'Contact Test',
            'contact_urgence_telephone': '123456789'
        }
        
        form = ReservationForm(data=form_data, user=self.client_user, maison=self.maison)
        self.assertFalse(form.is_valid())
        
        # Nombre de personnes dépassant la capacité
        form_data.update({
            'date_debut': date.today() + timedelta(days=7),
            'date_fin': date.today() + timedelta(days=10),
            'nombre_personnes': 6  # Dépasse la capacité de 4
        })
        
        form = ReservationForm(data=form_data, user=self.client_user, maison=self.maison)
        self.assertFalse(form.is_valid())


class ReservationViewTest(TestCase):
    """Tests pour les vues de réservation"""
    
    def setUp(self):
        """Configuration des données de test"""
        self.client = Client()
        
        self.ville = Ville.objects.create(nom="Douala", code_postal="00237", departement="Littoral")
        self.gestionnaire = User.objects.create_user(
            username="gestionnaire", email="gest@test.com", 
            password="testpass123", role="GESTIONNAIRE"
        )
        self.client_user = User.objects.create_user(
            username="client", email="client@test.com", 
            password="testpass123", role="CLIENT"
        )
        
        self.maison = Maison.objects.create(
            nom="Test Maison", numero="M001", adresse="Test", ville=self.ville,
            gestionnaire=self.gestionnaire, capacite_personnes=4, nombre_chambres=2,
            nombre_salles_bain=1, superficie=80, prix_par_nuit=Decimal('50000'),
            disponible=True, slug="test-maison"
        )
    
    def test_recherche_disponibilite_view(self):
        """Test de la vue de recherche de disponibilité"""
        response = self.client.get(reverse('reservations:recherche_disponibilite'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'recherche')
    
    def test_reserver_maison_view_get(self):
        """Test de la vue de réservation (GET)"""
        self.client.login(username='client', password='testpass123')
        response = self.client.get(
            reverse('reservations:reserver_maison', kwargs={'maison_slug': self.maison.slug})
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.maison.nom)
    
    def test_reserver_maison_view_post(self):
        """Test de la vue de réservation (POST)"""
        self.client.login(username='client', password='testpass123')
        
        data = {
            'date_debut': date.today() + timedelta(days=7),
            'date_fin': date.today() + timedelta(days=10),
            'nombre_personnes': 2,
            'heure_arrivee': '15:00',
            'heure_depart': '11:00',
            'mode_paiement': 'integral',
            'contact_urgence_nom': 'Contact Test',
            'contact_urgence_telephone': '123456789'
        }
        
        response = self.client.post(
            reverse('reservations:reserver_maison', kwargs={'maison_slug': self.maison.slug}),
            data
        )
        
        # Vérifier qu'une réservation a été créée
        self.assertTrue(Reservation.objects.exists())
        reservation = Reservation.objects.first()
        self.assertEqual(reservation.client, self.client_user)
        self.assertEqual(reservation.maison, self.maison)
    
    def test_mes_reservations_view(self):
        """Test de la vue mes réservations"""
        self.client.login(username='client', password='testpass123')
        
        # Créer une réservation
        Reservation.objects.create(
            client=self.client_user, maison=self.maison,
            date_debut=date.today() + timedelta(days=7),
            date_fin=date.today() + timedelta(days=10),
            nombre_personnes=2
        )
        
        response = self.client.get(reverse('reservations:mes_reservations'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'REV-')  # Numéro de réservation
    
    def test_acces_non_autorise(self):
        """Test d'accès non autorisé aux vues protégées"""
        # Sans connexion
        response = self.client.get(reverse('reservations:mes_reservations'))
        self.assertEqual(response.status_code, 302)  # Redirection vers login
        
        # Client tentant d'accéder aux vues gestionnaire
        self.client.login(username='client', password='testpass123')
        response = self.client.get(reverse('reservations:dashboard_gestionnaire'))
        self.assertEqual(response.status_code, 302)  # Redirection


class DisponibiliteModelTest(TestCase):
    """Tests pour le modèle Disponibilite"""
    
    def setUp(self):
        """Configuration des données de test"""
        self.ville = Ville.objects.create(nom="Douala", code_postal="00237", departement="Littoral")
        self.gestionnaire = User.objects.create_user(username="gestionnaire", email="gest@test.com", role="GESTIONNAIRE")
        
        self.maison = Maison.objects.create(
            nom="Test Maison", numero="M001", adresse="Test", ville=self.ville,
            gestionnaire=self.gestionnaire, capacite_personnes=4, nombre_chambres=2,
            nombre_salles_bain=1, superficie=80, prix_par_nuit=Decimal('50000')
        )
    
    def test_creation_disponibilite(self):
        """Test de création d'une disponibilité"""
        disponibilite = Disponibilite.objects.create(
            maison=self.maison,
            date=date.today() + timedelta(days=7),
            disponible=False,
            raison_indisponibilite="Maintenance"
        )
        
        self.assertEqual(disponibilite.maison, self.maison)
        self.assertFalse(disponibilite.disponible)
        self.assertEqual(disponibilite.raison_indisponibilite, "Maintenance")
    
    def test_prix_effectif(self):
        """Test du prix effectif"""
        # Sans prix spécial
        disponibilite = Disponibilite.objects.create(
            maison=self.maison,
            date=date.today() + timedelta(days=7)
        )
        self.assertEqual(disponibilite.prix_effectif, self.maison.prix_par_nuit)
        
        # Avec prix spécial
        disponibilite.prix_special = Decimal('60000')
        disponibilite.save()
        self.assertEqual(disponibilite.prix_effectif, Decimal('60000'))
    
    def test_bloquer_periode(self):
        """Test de blocage d'une période"""
        date_debut = date.today() + timedelta(days=7)
        date_fin = date.today() + timedelta(days=10)
        
        Disponibilite.objects.bloquer_periode(self.maison, date_debut, date_fin, "Test")
        
        # Vérifier que les disponibilités ont été créées
        disponibilites = Disponibilite.objects.filter(
            maison=self.maison,
            date__gte=date_debut,
            date__lte=date_fin
        )
        
        self.assertEqual(disponibilites.count(), 4)  # 4 jours
        for dispo in disponibilites:
            self.assertFalse(dispo.disponible)
            self.assertEqual(dispo.raison_indisponibilite, "Test")


class EvaluationReservationModelTest(TestCase):
    """Tests pour le modèle EvaluationReservation"""
    
    def setUp(self):
        """Configuration des données de test"""
        self.ville = Ville.objects.create(nom="Douala", code_postal="00237", departement="Littoral")
        self.gestionnaire = User.objects.create_user(username="gestionnaire", email="gest@test.com", role="GESTIONNAIRE")
        self.client_user = User.objects.create_user(username="client", email="client@test.com", role="CLIENT")
        
        self.maison = Maison.objects.create(
            nom="Test Maison", numero="M001", adresse="Test", ville=self.ville,
            gestionnaire=self.gestionnaire, capacite_personnes=4, nombre_chambres=2,
            nombre_salles_bain=1, superficie=80, prix_par_nuit=Decimal('50000')
        )
        
        self.reservation = Reservation.objects.create(
            client=self.client_user, maison=self.maison,
            date_debut=date.today() - timedelta(days=10),
            date_fin=date.today() - timedelta(days=7),
            nombre_personnes=2, statut='terminee'
        )
    
    def test_creation_evaluation(self):
        """Test de création d'une évaluation"""
        evaluation = EvaluationReservation.objects.create(
            reservation=self.reservation,
            note_globale=4,
            note_proprete=5,
            note_equipements=4,
            note_emplacement=4,
            note_rapport_qualite_prix=3,
            commentaire="Très bon séjour !",
            recommande=True,
            reviendrait=True
        )
        
        self.assertEqual(evaluation.reservation, self.reservation)
        self.assertEqual(evaluation.note_globale, 4)
        self.assertTrue(evaluation.recommande)
        self.assertTrue(evaluation.approuve)  # Par défaut
    
    def test_note_moyenne(self):
        """Test du calcul de la note moyenne"""
        evaluation = EvaluationReservation.objects.create(
            reservation=self.reservation,
            note_globale=4,
            note_proprete=5,
            note_equipements=4,
            note_emplacement=3,
            note_rapport_qualite_prix=4,
            commentaire="Test",
            recommande=True,
            reviendrait=True
        )
        
        # Moyenne = (4+5+4+3+4)/5 = 4.0
        self.assertEqual(evaluation.note_moyenne, 4.0)


class IntegrationTest(TestCase):
    """Tests d'intégration pour le workflow complet"""
    
    def setUp(self):
        """Configuration des données de test"""
        self.client = Client()
        
        self.ville = Ville.objects.create(nom="Douala", code_postal="00237", departement="Littoral")
        self.gestionnaire = User.objects.create_user(
            username="gestionnaire", email="gest@test.com", 
            password="testpass123", role="GESTIONNAIRE"
        )
        self.client_user = User.objects.create_user(
            username="client", email="client@test.com", 
            password="testpass123", role="CLIENT"
        )
        
        self.maison = Maison.objects.create(
            nom="Test Maison", numero="M001", adresse="Test", ville=self.ville,
            gestionnaire=self.gestionnaire, capacite_personnes=4, nombre_chambres=2,
            nombre_salles_bain=1, superficie=80, prix_par_nuit=Decimal('50000'),
            disponible=True, slug="test-maison"
        )
        
        self.type_paiement = TypePaiement.objects.create(
            nom="Test Payment", frais_pourcentage=Decimal('2'), actif=True
        )
    
    def test_workflow_complet_reservation(self):
        """Test du workflow complet d'une réservation"""
        
        # 1. Client se connecte et fait une réservation
        self.client.login(username='client', password='testpass123')
        
        data = {
            'date_debut': date.today() + timedelta(days=7),
            'date_fin': date.today() + timedelta(days=10),
            'nombre_personnes': 2,
            'mode_paiement': 'acompte',
            'contact_urgence_nom': 'Contact Test',
            'contact_urgence_telephone': '123456789'
        }
        
        response = self.client.post(
            reverse('reservations:reserver_maison', kwargs={'maison_slug': self.maison.slug}),
            data
        )
        
        # Vérifier que la réservation a été créée
        reservation = Reservation.objects.first()
        self.assertIsNotNone(reservation)
        self.assertEqual(reservation.statut, 'en_attente')
        
        # 2. Gestionnaire confirme la réservation
        self.client.logout()
        self.client.login(username='gestionnaire', password='testpass123')
        
        reservation.confirmer()
        self.assertEqual(reservation.statut, 'confirmee')
        
        # 3. Client effectue un paiement
        paiement = Paiement.objects.create(
            reservation=reservation,
            type_paiement=self.type_paiement,
            montant=reservation.montant_acompte
        )
        
        # 4. Gestionnaire valide le paiement
        paiement.valider()
        self.assertEqual(paiement.statut, 'valide')
        
        # 5. Séjour terminé
        reservation.statut = 'terminee'
        reservation.save()
        
        # 6. Client laisse une évaluation
        self.client.logout()
        self.client.login(username='client', password='testpass123')
        
        evaluation = EvaluationReservation.objects.create(
            reservation=reservation,
            note_globale=4,
            note_proprete=5,
            note_equipements=4,
            note_emplacement=4,
            note_rapport_qualite_prix=3,
            commentaire="Excellent séjour !",
            recommande=True,
            reviendrait=True
        )
        
        self.assertIsNotNone(evaluation)
        self.assertEqual(evaluation.note_globale, 4)
        
        # Vérifier que tout le workflow s'est bien déroulé
        final_reservation = Reservation.objects.get(pk=reservation.pk)
        final_paiement = Paiement.objects.get(pk=paiement.pk)
        
        self.assertEqual(final_reservation.statut, 'terminee')
        self.assertEqual(final_paiement.statut, 'valide')
        self.assertTrue(hasattr(final_reservation, 'evaluation'))