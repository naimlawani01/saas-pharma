# Guide d'Installation - Backend

## ✅ Solution pour Python 3.14

Le projet utilise maintenant des versions mises à jour des dépendances qui supportent Python 3.14 :
- `psycopg2-binary>=2.9.11` - wheels précompilés pour Python 3.14
- `pydantic>=2.9.0` - inclut `pydantic-core==2.41.5` avec wheels pour Python 3.14
- Autres dépendances mises à jour pour compatibilité

L'installation devrait fonctionner sans problème.

## Problèmes courants avec psycopg2-binary

Si vous rencontrez encore une erreur lors de l'installation de `psycopg2-binary` (erreur `pg_config not found`), voici plusieurs solutions :

### Solution 1 : Utiliser une version plus récente (Déjà appliquée)

Le projet utilise `psycopg2-binary>=2.9.11` qui a des wheels précompilés pour Python 3.14.

### Solution 2 : Installer PostgreSQL avec Homebrew (macOS)

Si vous avez toujours des problèmes, installez PostgreSQL :

```bash
brew install postgresql@15
# ou
brew install postgresql
```

Puis ajoutez au PATH :
```bash
export PATH="/opt/homebrew/opt/postgresql@15/bin:$PATH"
# ou pour la version standard
export PATH="/opt/homebrew/opt/postgresql/bin:$PATH"
```

### Solution 3 : Utiliser Python 3.11 ou 3.12

Si vous continuez à avoir des problèmes avec Python 3.14, utilisez Python 3.11 ou 3.12 qui sont mieux supportés.

## Installation normale

```bash
cd backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

## Vérification

Pour vérifier que tout fonctionne :

```bash
python -c "import psycopg; print('psycopg3 installé avec succès')"
```

## Note sur Python 3.14

Python 3.14 est très récent et certaines bibliothèques peuvent ne pas avoir encore de wheels précompilés. Il est recommandé d'utiliser Python 3.11 ou 3.12 pour une meilleure compatibilité.
