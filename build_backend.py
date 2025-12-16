#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script pour packager le backend FastAPI avec PyInstaller
"""

import os
import sys
import shutil
import subprocess
from pathlib import Path

# Configurer l'encodage UTF-8 pour Windows
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

BACKEND_DIR = Path(__file__).parent
DIST_DIR = BACKEND_DIR / "dist"
BUILD_DIR = BACKEND_DIR / "build"

def clean():
    """Nettoyer les dossiers de build précédents"""
    print("[CLEAN] Nettoyage...")
    for folder in [DIST_DIR, BUILD_DIR]:
        if folder.exists():
            shutil.rmtree(folder)
    
    for spec in BACKEND_DIR.glob("*.spec"):
        spec.unlink()
    
    launcher = BACKEND_DIR / "launcher.py"
    if launcher.exists():
        launcher.unlink()

def create_launcher():
    """Créer le script de lancement pour PyInstaller"""
    launcher_path = BACKEND_DIR / "launcher.py"
    
    launcher_code = '''#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Launcher for packaged FastAPI backend
"""

import os
import sys
import traceback

print("=" * 50)
print("PHARMACIE BACKEND - DEMARRAGE")
print("=" * 50)

try:
    # Set environment variables BEFORE imports
    if getattr(sys, 'frozen', False):
        BASE_DIR = os.path.dirname(sys.executable)
        print(f"Mode: PACKAGED")
    else:
        BASE_DIR = os.path.dirname(os.path.abspath(__file__))
        print(f"Mode: DEVELOPMENT")
    
    print(f"Base dir: {BASE_DIR}")
    
    # Create data directory
    DATA_DIR = os.path.join(BASE_DIR, 'data')
    os.makedirs(DATA_DIR, exist_ok=True)
    print(f"Data dir: {DATA_DIR}")
    
    # Configuration
    os.environ['DATABASE_URL'] = f'sqlite:///{DATA_DIR}/pharmacie.db'
    os.environ['SECRET_KEY'] = 'local-electron-secret-key-change-in-production'
    os.environ['ENVIRONMENT'] = 'production'
    os.environ['DEBUG'] = 'false'
    os.environ['BACKEND_CORS_ORIGINS'] = '["http://localhost:5173","http://localhost:8000","file://"]'
    
    print(f"Database URL: {os.environ['DATABASE_URL']}")
    
    print("Importing uvicorn...")
    import uvicorn
    print("OK")
    
    print("Importing app...")
    from app.main import app
    print("OK")
    
    print("=" * 50)
    print("Demarrage du serveur sur http://127.0.0.1:8000")
    print("=" * 50)
    
    uvicorn.run(
        app,
        host="127.0.0.1",
        port=8000,
        log_level="info"
    )
    
except Exception as e:
    print("=" * 50)
    print(f"ERROR: {e}")
    print("=" * 50)
    traceback.print_exc()
    input("Press Enter to close...")
    sys.exit(1)
'''
    
    with open(launcher_path, 'w', encoding='utf-8') as f:
        f.write(launcher_code)
    
    print(f"[OK] Launcher cree: {launcher_path}")
    return launcher_path

def build():
    """Builder avec PyInstaller"""
    print("[BUILD] Build avec PyInstaller...")
    
    launcher_path = create_launcher()
    
    # Options PyInstaller - plus simples et robustes
    pyinstaller_args = [
        'pyinstaller',
        '--onedir',
        '--name=pharmacie-backend',
        '--noconfirm',
        '--clean',
        '--console',  # Garder la console pour voir les erreurs
        # Imports cachés nécessaires
        '--hidden-import=uvicorn.logging',
        '--hidden-import=uvicorn.loops',
        '--hidden-import=uvicorn.loops.auto',
        '--hidden-import=uvicorn.protocols',
        '--hidden-import=uvicorn.protocols.http',
        '--hidden-import=uvicorn.protocols.http.auto',
        '--hidden-import=uvicorn.protocols.http.h11_impl',
        '--hidden-import=uvicorn.protocols.http.httptools_impl',
        '--hidden-import=uvicorn.protocols.websockets',
        '--hidden-import=uvicorn.protocols.websockets.auto',
        '--hidden-import=uvicorn.protocols.websockets.websockets_impl',
        '--hidden-import=uvicorn.protocols.websockets.wsproto_impl',
        '--hidden-import=uvicorn.lifespan',
        '--hidden-import=uvicorn.lifespan.on',
        '--hidden-import=uvicorn.lifespan.off',
        '--hidden-import=fastapi',
        '--hidden-import=starlette',
        '--hidden-import=starlette.responses',
        '--hidden-import=starlette.routing',
        '--hidden-import=starlette.middleware',
        '--hidden-import=starlette.middleware.cors',
        '--hidden-import=pydantic',
        '--hidden-import=pydantic_settings',
        '--hidden-import=pydantic.deprecated.decorator',
        '--hidden-import=sqlalchemy',
        '--hidden-import=sqlalchemy.dialects.sqlite',
        '--hidden-import=sqlalchemy.sql.default_comparator',
        '--hidden-import=email_validator',
        '--hidden-import=bcrypt',
        '--hidden-import=jose',
        '--hidden-import=jose.jwt',
        '--hidden-import=passlib',
        '--hidden-import=passlib.handlers',
        '--hidden-import=passlib.handlers.bcrypt',
        '--hidden-import=multipart',
        '--hidden-import=anyio',
        '--hidden-import=anyio._backends',
        '--hidden-import=anyio._backends._asyncio',
        '--hidden-import=httptools',
        '--hidden-import=dotenv',
        '--hidden-import=h11',
        '--hidden-import=click',
        # Collecter les données
        '--collect-all=uvicorn',
        '--collect-all=starlette',
        '--collect-all=fastapi',
        '--collect-all=pydantic',
        '--collect-all=email_validator',
        # Ajouter le dossier app
        '--add-data=app:app',
        str(launcher_path),
    ]
    
    print(f"Commande: pyinstaller ...")
    
    result = subprocess.run(
        pyinstaller_args,
        cwd=BACKEND_DIR,
    )
    
    if result.returncode != 0:
        print("[ERROR] Erreur lors du build")
        sys.exit(1)
    
    print("[OK] Build termine!")
    
    # Créer le dossier data dans dist
    data_dir = DIST_DIR / "pharmacie-backend" / "data"
    data_dir.mkdir(exist_ok=True)
    print(f"[OK] Dossier data cree: {data_dir}")

def main():
    print("=" * 60)
    print("BUILD DU BACKEND FASTAPI")
    print("=" * 60)
    
    clean()
    build()
    
    print("\n" + "=" * 60)
    print("[OK] BUILD TERMINE!")
    print("=" * 60)
    print(f"\n[INFO] Executable: {DIST_DIR / 'pharmacie-backend' / 'pharmacie-backend'}")
    print("\nPour tester:")
    print(f"  cd {DIST_DIR / 'pharmacie-backend'}")
    print("  ./pharmacie-backend")

if __name__ == "__main__":
    main()
