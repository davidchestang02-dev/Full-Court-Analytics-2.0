import os
import boto3
from pathlib import Path

ACCOUNT_ID = os.getenv("CLOUDFLARE_ACCOUNT_ID")
ACCESS_KEY = os.getenv("CLOUDFLARE_R2_ACCESS_KEY_ID")
SECRET_KEY = os.getenv("CLOUDFLARE_R2_SECRET_ACCESS_KEY")

BUCKET = "fca-bucket1"  # your bucket name

session = boto3.session.Session()

client = session.client(
    "s3",
    endpoint_url=f"https://{ACCOUNT_ID}.r2.cloudflarestorage.com",
    aws_access_key_id=ACCESS_KEY,
    aws_secret_access_key=SECRET_KEY,
)

def upload_file(local_path: Path, key: str):
    print(f"Uploading {local_path} → {key}")
    client.upload_file(str(local_path), BUCKET, key)

def main():
    base = Path("data")
    for path in base.rglob("*.json"):
        key = str(path).replace("\\", "/")
        upload_file(path, key)

if __name__ == "__main__":
    main()
