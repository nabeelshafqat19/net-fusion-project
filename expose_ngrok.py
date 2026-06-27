#!/usr/bin/env python3
"""
Script to expose NetFusion application to the internet using ngrok
"""

try:
    from pyngrok import ngrok
except ImportError:
    print("Installing pyngrok...")
    import subprocess
    import sys
    subprocess.check_call([sys.executable, "-m", "pip", "install", "pyngrok", "--quiet"])
    from pyngrok import ngrok

import time

# Set ngrok auth token (optional - for more stable tunnels)
# ngrok.set_auth_token("YOUR_AUTH_TOKEN_HERE")

print("=" * 60)
print("🚀 NetFusion Public Access via ngrok")
print("=" * 60)

try:
    # Create tunnel to localhost:8000
    public_url = ngrok.connect(8000, "http")
    print(f"\n✅ Tunnel created successfully!")
    print(f"\n📡 Public URL: {public_url}")
    print(f"\nYour application is now accessible at:")
    print(f"   {public_url}")
    print(f"\nLocal access still available at:")
    print(f"   http://localhost:8000")
    
    print("\n" + "=" * 60)
    print("Press Ctrl+C to stop the tunnel")
    print("=" * 60 + "\n")
    
    # Keep the tunnel running
    while True:
        time.sleep(1)
        
except KeyboardInterrupt:
    print("\n\n🛑 Stopping ngrok tunnel...")
    ngrok.kill()
    print("✓ Tunnel closed")
except Exception as e:
    print(f"\n❌ Error: {e}")
    print("\nTroubleshooting:")
    print("1. Make sure your FastAPI server is running on http://localhost:8000")
    print("2. If you see an auth error, sign up at https://ngrok.com and add your token")
    print("3. For free plan, tunnels expire after 8 hours")
