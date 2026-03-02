import os
import socket
import sys
from urllib.parse import urlparse

def test_db_connection():
    # Priority: SUPABASE_DATABASE_URL -> DATABASE_URL -> POSTGRES_HOST
    db_url = os.getenv("SUPABASE_DATABASE_URL") or os.getenv("DATABASE_URL")
    
    if db_url:
        try:
            parsed = urlparse(db_url)
            host = parsed.hostname
            port = parsed.port or 5432
        except Exception as e:
            print(f"❌ Error parsing DB URL: {e}")
            sys.exit(1)
    else:
        host = os.getenv("POSTGRES_HOST")
        port = int(os.getenv("POSTGRES_PORT", "5432"))

    if not host:
        print("⚠️ No database host configured. Skipping connection test.")
        return

    print(f"🔍 Testing connection to {host}:{port}...")
    
    try:
        # 5 second timeout
        socket.setdefaulttimeout(5)
        socket.socket(socket.AF_INET, socket.SOCK_STREAM).connect((host, port))
        print(f"✅ Successfully established TCP connection to {host}:{port}")
    except socket.timeout:
        print(f"❌ Connection to {host}:{port} timed out. Verify IP allow-list in Supabase.")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Failed to connect to {host}:{port}: {e}")
        sys.exit(1)

if __name__ == "__main__":
    test_db_connection()
