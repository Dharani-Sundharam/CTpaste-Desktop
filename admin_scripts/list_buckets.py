import os
from google.cloud import storage

os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = r"c:\Users\Dharani Sundharam\Desktop\Programming\CTpaste\desktop_app\firebase_config.json"

def list_buckets():
    client = storage.Client(project="CTpaste-sync")
    buckets = client.list_buckets()
    print("Buckets found:")
    for b in buckets:
        print(f" - {b.name}")

if __name__ == "__main__":
    list_buckets()
