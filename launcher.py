#!/usr/bin/env python3
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
