import os
from google.cloud import storage

# Set the environment variable to use the service account
os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = r"c:\Users\Dharani Sundharam\Desktop\Programming\CTpaste\desktop_app\firebase_config.json"

def set_bucket_cors():
    bucket_name = "CTpaste-sync.firebasestorage.app"
    
    # Initialize the client
    client = storage.Client()
    
    try:
        bucket = client.get_bucket(bucket_name)
    except Exception as e:
        print(f"Failed to get bucket {bucket_name}: {e}")
        # Try without .firebasestorage.app just in case it is appspot.com
        bucket_name = "CTpaste-sync.appspot.com"
        try:
            bucket = client.get_bucket(bucket_name)
        except Exception as e2:
            print(f"Failed to get bucket {bucket_name} as well: {e2}")
            return
            
    print(f"Successfully loaded bucket: {bucket_name}")
    
    # Define CORS configuration
    cors_configuration = [
        {
            "origin": ["*"],  # Allow all origins (we can restrict this to the exact production URL later)
            "method": ["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH"],
            "responseHeader": ["Content-Type", "Authorization", "Content-Length", "User-Agent", "x-goog-resumable"],
            "maxAgeSeconds": 3600
        }
    ]
    
    # Apply the CORS configuration
    bucket.cors = cors_configuration
    try:
        bucket.patch()
        print(f"Successfully set CORS policies for {bucket.name}")
    except Exception as e:
        print(f"Failed to set CORS policy: {e}")

if __name__ == "__main__":
    set_bucket_cors()
