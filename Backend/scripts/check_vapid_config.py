#!/usr/bin/env python3
"""
Script om te controleren of VAPID keys correct zijn geconfigureerd.
"""

import os
import sys
from pathlib import Path

# Path setup
THIS_FILE = Path(__file__).resolve()
SCRIPTS_DIR = THIS_FILE.parent
BACKEND_DIR = SCRIPTS_DIR.parent

if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

print("\n" + "=" * 70)
print("VAPID CONFIGURATION CHECK".center(70))
print("=" * 70 + "\n")

# Check backend VAPID keys
backend_env = BACKEND_DIR / ".env"
if backend_env.exists():
    print("📁 Backend .env gevonden")
    with open(backend_env, "r") as f:
        content = f.read()
        has_private = "VAPID_PRIVATE_KEY" in content
        has_public = "VAPID_PUBLIC_KEY" in content
        
        print(f"   VAPID_PRIVATE_KEY: {'✅ Geconfigureerd' if has_private else '❌ Ontbreekt'}")
        print(f"   VAPID_PUBLIC_KEY:  {'✅ Geconfigureerd' if has_public else '❌ Ontbreekt'}")
else:
    print("❌ Backend .env niet gevonden")
    print(f"   Verwacht: {backend_env}")

# Check frontend VAPID key
frontend_dir = BACKEND_DIR.parent / "Frontend"
frontend_env_dev = frontend_dir / ".env.development"
frontend_env_prod = frontend_dir / ".env.production"

print(f"\n📁 Frontend environment files:")
if frontend_env_dev.exists():
    print(f"   .env.development: ✅ Gevonden")
    with open(frontend_env_dev, "r") as f:
        content = f.read()
        has_vapid = "VITE_VAPID_PUBLIC_KEY" in content
        print(f"   VITE_VAPID_PUBLIC_KEY: {'✅ Geconfigureerd' if has_vapid else '❌ Ontbreekt'}")
else:
    print(f"   .env.development: ❌ Niet gevonden")
    print(f"   Verwacht: {frontend_env_dev}")

if frontend_env_prod.exists():
    print(f"   .env.production: ✅ Gevonden")
    with open(frontend_env_prod, "r") as f:
        content = f.read()
        has_vapid = "VITE_VAPID_PUBLIC_KEY" in content
        print(f"   VITE_VAPID_PUBLIC_KEY: {'✅ Geconfigureerd' if has_vapid else '❌ Ontbreekt'}")
else:
    print(f"   .env.production: ⚠️  Niet gevonden (optioneel voor lokaal)")

print("\n" + "=" * 70)
print("AANBEVELINGEN".center(70))
print("=" * 70)

# Check if keys exist
backend_ok = backend_env.exists() and has_private and has_public
frontend_ok = (frontend_env_dev.exists() and "VITE_VAPID_PUBLIC_KEY" in open(frontend_env_dev).read()) if frontend_env_dev.exists() else False

if not backend_ok:
    print("\n❌ Backend VAPID keys ontbreken:")
    print("   1. Genereer keys met: python Backend/generate_vapid_keys.py")
    print("   2. Voeg toe aan Backend/.env:")
    print("      VAPID_PRIVATE_KEY=<private_key>")
    print("      VAPID_PUBLIC_KEY=<public_key>")

if not frontend_ok:
    print("\n❌ Frontend VAPID public key ontbreekt:")
    print("   1. Gebruik dezelfde PUBLIC key als in Backend/.env")
    print("   2. Voeg toe aan Frontend/.env.development:")
    print("      VITE_VAPID_PUBLIC_KEY=<public_key>")
    print("   3. Voor productie, voeg toe aan Render/GitHub Secrets:")
    print("      VITE_VAPID_PUBLIC_KEY=<public_key>")

if backend_ok and frontend_ok:
    print("\n✅ VAPID keys zijn correct geconfigureerd!")
    print("   → Je kunt nu push notifications testen")

print("\n" + "=" * 70 + "\n")


