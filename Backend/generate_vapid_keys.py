#!/usr/bin/env python3
"""
Generate VAPID keys for Web Push notifications.
This script generates a new VAPID key pair and displays them in the correct format.
"""

from py_vapid import Vapid01
import base64

def main():
    print("=" * 70)
    print("VAPID KEY GENERATOR")
    print("=" * 70)
    print("\nGenerating new VAPID keys...\n")
    
    try:
        # Create a new VAPID instance (this generates new keys automatically)
        vapid = Vapid01()
        
        # Get the keys in PEM format
        private_key_pem = vapid.private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption()
        )
        
        public_key_pem = vapid.public_key.public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo
        )
        
        # Convert to the format needed for Web Push (base64 URL-safe, no padding)
        # For private key: extract the raw bytes and encode
        from cryptography.hazmat.primitives import serialization
        private_key_raw = vapid.private_key.private_bytes(
            encoding=serialization.Encoding.DER,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption()
        )
        
        # For public key: extract the raw bytes (uncompressed point format)
        public_key_raw = vapid.public_key.public_bytes(
            encoding=serialization.Encoding.X962,
            format=serialization.PublicFormat.UncompressedPoint
        )
        
        # Convert to base64 URL-safe format (what Web Push API expects)
        # Note: This is old code, the code below uses a better approach
        private_key_b64 = base64.urlsafe_b64encode(private_key_raw).decode('utf-8').rstrip('=')
        # Keep the 0x04 prefix (uncompressed point indicator) - Web Push API expects it
        public_key_b64 = base64.urlsafe_b64encode(public_key_raw).decode('utf-8').rstrip('=')
        
        # Actually, let's use the simpler approach - py-vapid has a method for this
        # Get the keys in the format that pywebpush expects
        private_key = vapid.private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption()
        ).decode('utf-8')
        
        # For public key, we need the base64 URL-safe format
        # py-vapid stores keys in a specific format, let's extract them correctly
        public_key_bytes = vapid.public_key.public_bytes(
            encoding=serialization.Encoding.X962,
            format=serialization.PublicFormat.UncompressedPoint
        )
        # Keep the 0x04 prefix (uncompressed point indicator) - Web Push API expects it
        # The frontend will handle both formats (with and without prefix) for backwards compatibility
        public_key_b64 = base64.urlsafe_b64encode(public_key_bytes).decode('utf-8').rstrip('=')
        
        print("✅ Keys generated successfully!\n")
        print("=" * 70)
        print("PUBLIC KEY (use in Frontend AND Backend):")
        print("=" * 70)
        print(public_key_b64)
        print("\n" + "=" * 70)
        print("PRIVATE KEY (use ONLY in Backend):")
        print("=" * 70)
        print(private_key)
        print("\n" + "=" * 70)
        print("⚠️  IMPORTANT:")
        print("   - Public Key: Add to Render as VITE_VAPID_PUBLIC_KEY (Frontend)")
        print("   - Public Key: Add to Render as VAPID_PUBLIC_KEY (Backend)")
        print("   - Private Key: Add to Render as VAPID_PRIVATE_KEY (Backend ONLY)")
        print("   - Keep these keys secure and never commit them to git!")
        print("=" * 70)
        
    except Exception as e:
        print(f"\n❌ Error generating keys: {e}")
        print("\nTrying alternative method...\n")
        
        # Alternative: use pywebpush's method
        try:
            from pywebpush import webpush
            import json
            
            # This is a workaround - pywebpush doesn't have a direct key generator
            # But we can use cryptography directly
            from cryptography.hazmat.primitives.asymmetric import ec
            from cryptography.hazmat.primitives import serialization
            
            # Generate new EC key pair
            private_key_obj = ec.generate_private_key(ec.SECP256R1())
            public_key_obj = private_key_obj.public_key()
            
            # Get private key in PEM format (what pywebpush expects)
            private_key_pem = private_key_obj.private_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PrivateFormat.PKCS8,
                encryption_algorithm=serialization.NoEncryption()
            ).decode('utf-8')
            
            # Get public key in uncompressed point format, then convert to base64
            public_key_bytes = public_key_obj.public_bytes(
                encoding=serialization.Encoding.X962,
                format=serialization.PublicFormat.UncompressedPoint
            )
            # Keep the 0x04 prefix (uncompressed point indicator) - Web Push API expects it
            public_key_b64 = base64.urlsafe_b64encode(public_key_bytes).decode('utf-8').rstrip('=')
            
            print("✅ Keys generated successfully (alternative method)!\n")
            print("=" * 70)
            print("PUBLIC KEY (use in Frontend AND Backend):")
            print("=" * 70)
            print(public_key_b64)
            print("\n" + "=" * 70)
            print("PRIVATE KEY (use ONLY in Backend):")
            print("=" * 70)
            print(private_key_pem)
            print("\n" + "=" * 70)
            print("⚠️  IMPORTANT:")
            print("   - Public Key: Add to Render as VITE_VAPID_PUBLIC_KEY (Frontend)")
            print("   - Public Key: Add to Render as VAPID_PUBLIC_KEY (Backend)")
            print("   - Private Key: Add to Render as VAPID_PRIVATE_KEY (Backend ONLY)")
            print("   - Keep these keys secure and never commit them to git!")
            print("=" * 70)
            
        except Exception as e2:
            print(f"\n❌ Alternative method also failed: {e2}")
            print("\nPlease try using the web-push npm tool instead:")
            print("  npm install -g web-push")
            print("  web-push generate-vapid-keys")
            return 1
    
    return 0

if __name__ == "__main__":
    from cryptography.hazmat.primitives import serialization
    from cryptography.hazmat.primitives.asymmetric import ec
    exit(main())

