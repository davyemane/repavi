# 🏠 RepAvi - Setup de l'interface d'administration

## 📋 Vue d'ensemble

Vous avez maintenant **deux interfaces d'administration** :

1. **🎨 Administration personnalisée RepAvi** (`/repavi-admin/`) - Interface moderne avec Tailwind
2. **⚙️ Administration Django standard** (`/admin/`) - Interface de backup

## 🚀 Installation et configuration

### 1. Structure des fichiers à créer

```
repavi/
├── home/
│   ├── forms.py                 # ✅ Formulaires Django
│   ├── admin_views.py           # ✅ Vues d'administration
│   ├── admin_urls.py            # ✅ URLs d'administration
│   └── admin.py                 # ✅ Configuration admin standard
├── templates/
│   └── admin/
│       ├── base.html            # ✅ Template de base
│       ├── dashboard.html       # ✅ Tableau de bord
│       ├── confirm_delete.html  # ✅ Confirmation suppression
│       ├── maisons/
│       │   ├── list.html        # ✅ Liste des maisons
│       │   └── form.html        # ✅ Formulaire maison
│       ├── villes/
│       │   ├── list.html        # ✅ Liste des villes
│       │   └── form.html        # ✅ Formulaire ville
│       ├── categories/
│       │   ├── list.html        # ✅ Liste des catégories
│       │   └── form.html        # ✅ Formulaire catégorie
│       └── photos/
│           ├── list.html        # ✅ Liste des photos
│           └── form.html        # ✅ Formulaire photo
├── create_test_data.py          # ✅ Script de données de test
└── repavi/
    └── urls.py                  # ✅ URLs principales
```

### 2. Mise à jour des dépendances

```bash
pip install django-browser-reload
```

### 3. Configuration settings.py

Vérifiez que votre `settings.py` contient :

```python
INSTALLED_APPS = [
    # ... autres apps
    'tailwind',
    'theme',
    'django_browser_reload',  # Nouveau
    'home',
]

MIDDLEWARE = [
    # ... autres middleware
    'django_browser_reload.middleware.BrowserReloadMiddleware',  # Nouveau
    # ... reste du middleware
]

TAILWIND_APP_NAME = 'theme'
INTERNAL_IPS = ["127.0.0.1", "localhost"]
```

### 4. Créer les données de test

```bash
# Appliquer les migrations
python manage.py makemigrations
python manage.py migrate

# Créer les données de test
python manage.py shell < create_test_data.py
```

### 5. Démarrer l'application

```bash
# Terminal 1 : Tailwind
python manage.py tailwind start

# Terminal 2 : Django
python manage.py runserver
```

## 🎯 Accès aux interfaces

### Administration personnalisée RepAvi
- **URL** : `http://127.0.0.1:8000/repavi-admin/`
- **Design** : Interface moderne avec Tailwind CSS
- **Fonctionnalités** : 
  - Tableau de bord avec statistiques
  - Gestion des maisons avec aperçu photos
  - Gestion des villes et catégories
  - Upload et gestion des photos
  - Gestion des réservations
  - Filtres et recherche avancée

### Administration Django standard
- **URL** : `http://127.0.0.1:8000/admin/`
- **Design** : Interface Django standard
- **Usage** : Interface de backup et administration technique

### Identifiants par défaut
- **Username** : `admin`
- **Password** : `admin123`

## 🛠️ Fonctionnalités principales

### 📊 Tableau de bord
- Statistiques en temps réel
- Dernières maisons ajoutées
- Dernières réservations
- Actions rapides
- Maisons populaires

### 🏠 Gestion des maisons
- Liste avec filtres avancés
- Formulaire complet avec tous les champs
- Gestion des équipements (checkboxes)
- Auto-génération des slugs
- Statuts visuels (disponible/featured)

### 🖼️ Gestion des photos
- Upload avec aperçu
- Définition photo principale
- Ordre d'affichage
- Filtrage par maison
- Validation des formats

### 🏙️ Gestion des villes
- CRUD complet
- Compteur de maisons par ville
- Recherche intégrée

### 🏷️ Gestion des catégories
- Sélection de couleurs visuelles
- Aperçu des badges en temps réel
- Compteur de maisons par catégorie

## 🎨 Personnalisation

### Couleurs et thème
Les couleurs peuvent être modifiées dans `templates/admin/base.html` :

```css
.sidebar-link.active {
    background-color: #3b82f6; /* Bleu par défaut */
}
```

### Ajout de nouvelles vues
1. Créer la vue dans `admin_views.py`
2. Ajouter l'URL dans `admin_urls.py`
3. Créer le template correspondant
4. Ajouter le lien dans la sidebar (`base.html`)

## 🔒 Sécurité

L'accès est protégé par :
- `@login_required` - Utilisateur connecté requis
- `@user_passes_test(is_admin)` - Statut admin/staff requis

## 📱 Responsive

L'interface est entièrement responsive et fonctionne sur :
- 💻 Desktop
- 📱 Mobile
- 📋 Tablette

## 🚀 Production

Pour la production :
1. Changer `DEBUG = False`
2. Configurer `ALLOWED_HOSTS`
3. Utiliser un serveur web (Nginx + Gunicorn)
4. Configurer les fichiers statiques
5. Activer HTTPS

## 🆘 Dépannage

### Tailwind ne charge pas
```bash
python manage.py tailwind install
python manage.py tailwind start
```

### Erreurs de templates
Vérifiez que tous les fichiers templates sont créés dans la bonne structure.

### Erreurs d'importation
Vérifiez que `admin_views.py` et `admin_urls.py` sont bien créés.

## 🎉 Fonctionnalités bonus

- Auto-sauvegarde des formulaires
- Messages de confirmation
- Validation côté client
- Upload par drag & drop (photos)
- Aperçus en temps réel
- Raccourcis clavier
- Export de données (à venir)

---

**🎊 Votre interface d'administration RepAvi est maintenant prête !**

Accédez à `http://127.0.0.1:8000/repavi-admin/` pour commencer à gérer vos maisons, photos, villes et réservations avec une interface moderne et intuitive.