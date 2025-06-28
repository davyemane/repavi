## **CAHIER TECHNIQUE – Plateforme Repavi Lodges**

### **Technologies utilisées**

* Backend : Django (Python)

* Frontend : Tailwind CSS

* Base de données : PostgreSQL ou SQLite (en local)

* Notifications : Prévu avec intégration future d’une API WhatsApp (Twilio ou WhatsApp Business)

* Génération de PDF : `WeasyPrint` ou `xhtml2pdf`

---

## **1\. UTILISATEURS ET RÔLES**

### **1.1. Client**

* Visite libre de la vitrine

* Consultation des appartements

* Localisation sur Google Maps

* Lien direct vers WhatsApp pour réservation

* Création de compte (optionnel mais recommandé)

* Historique des réservations

* Avis public sur les appartements (étoiles \+ commentaire)

### **1.2. Gestionnaire**

* Gestion des réservations

* Gestion des clients

* Gestion des appartements

* Gestion des meubles

* Consultation des statistiques simples

* Génération de fiches PDF

* Notifications automatiques (à développer)

### **1.3. Super Admin**

* Dispose de tous les droits du gestionnaire

* Peut créer/modifier les gestionnaires

* Accès aux statistiques globales

* Paramètres système (messages de rappel, délais, etc.)

---

## **2\. MODULES FONCTIONNELS À IMPLÉMENTER**

### **2.1. Gestion des Appartements**

* CRUD complet

* Champs : numéro, type, état (occupé/vide), images par pièce

* Lien avec meubles et réservations

### **2.2. Gestion des Meubles**

* CRUD complet

* Champs : nom, type, numéro de série, état (défectueux/bon), date d’entrée, appart associé

* Filtres : par période, appartement, état

### **2.3. Réservations**

* Création manuelle par le gestionnaire

* Historique visible par client

* Champs : client, appartement, date entrée/sortie, montant payé, type de paiement (avance/total), statut (à confirmer, confirmée, terminée)

* Impression fiche PDF

### **2.4. Gestion des Clients**

* Enregistrement manuel par gestionnaire

* Champs : nom, prénom, sexe, téléphone, email, nationalité

* Filtres : par période

### **2.5. Système d’Avis**

* Publics et visibles sur les pages des appartements

* Note (1 à 5 étoiles) \+ commentaire

* Modération par l’admin (optionnel)

### **2.6. Statistiques**

* Chiffre d’affaires par période (somme des paiements)

* Réservations par période

* Appartements disponibles / occupés

### **2.7. Notifications (Système à prévoir)**

* Rappels WhatsApp ou e-mail aux :

  * Gestionnaires : réservations proches de l’échéance ou terminées

  * Clients : rappel veille de location, fin de location

* Intégration future via API WhatsApp (Twilio ou WhatsApp Business)

### **2.8. Vitrine Publique**

* Page d’accueil

* Liste des appartements avec filtre (type, disponibilité)

* Détails appartement (images, meubles, localisation)

* Avis clients

* Boutons vers les réseaux sociaux

* Bouton WhatsApp avec lien prérempli

---

## **3\. ESPACE CLIENT**

* Authentification (email \+ mot de passe)

* Tableau de bord :

  * Historique des réservations

  * Statut des réservations

  * Possibilité de donner un avis après séjour

---

## **4\. ESPACE ADMIN**

* Accès sécurisé

* Tableau de bord (stats globales, derniers avis, réservations en cours)

* Gestion CRUD complète :

  * Clients

  * Appartements

  * Meubles

  * Réservations

* Export PDF :

  * Fiche de réservation

  * Rapport du chiffre d’affaires

---

## **5\. BASE DE DONNÉES – MODÈLES DJANGO (extraits principaux)**

### **`Client`**

class Client(models.Model):  
    nom \= models.CharField(max\_length=100)  
    prenom \= models.CharField(max\_length=100)  
    sexe \= models.CharField(choices=\[('H', 'Homme'), ('F', 'Femme')\], max\_length=1)  
    telephone \= models.CharField(max\_length=20)  
    email \= models.EmailField()  
    nationalite \= models.CharField(max\_length=100)

### **`Appartement`**

class Appartement(models.Model):  
    numero \= models.CharField(max\_length=10)  
    type \= models.CharField(max\_length=100)  
    etat \= models.CharField(choices=\[('libre', 'Libre'), ('occupe', 'Occupé')\], max\_length=10)

### **`Meuble`**

class Meuble(models.Model):  
    nom \= models.CharField(max\_length=100)  
    type \= models.CharField(max\_length=100)  
    numero\_serie \= models.CharField(max\_length=50)  
    date\_entree \= models.DateField()  
    etat \= models.CharField(choices=\[('bon', 'Bon état'), ('defectueux', 'Défectueux')\], max\_length=20)  
    appartement \= models.ForeignKey(Appartement, on\_delete=models.CASCADE)

### **`Reservation`**

class Reservation(models.Model):  
    client \= models.ForeignKey(Client, on\_delete=models.CASCADE)  
    appartement \= models.ForeignKey(Appartement, on\_delete=models.CASCADE)  
    date\_entree \= models.DateField()  
    date\_sortie \= models.DateField()  
    montant \= models.DecimalField(max\_digits=10, decimal\_places=2)  
    type\_paiement \= models.CharField(choices=\[('avance', 'Avance'), ('total', 'Total')\], max\_length=10)  
    statut \= models.CharField(choices=\[('en\_attente', 'En attente'), ('confirmee', 'Confirmée'), ('terminee', 'Terminée')\], max\_length=15)

---

## **6\. FONCTIONNALITÉS FUTURES**

* Intégration paiement mobile (Orange Money, MTN MoMo)

* Interface mobile avec Flutter ou autre

* Application mobile dédiée pour gestionnaire

