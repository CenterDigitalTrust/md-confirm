import asyncio
import os

# Set environment variables from the user instructions
os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = "./firebase-key.json"
os.environ["GOOGLE_CLOUD_PROJECT"] = "gen-lang-client-0166064225"
os.environ["FIRESTORE_DATABASE_ID"] = "confirm"

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

from google.cloud import firestore

async def main():
    try:
        db = firestore.AsyncClient(
            project=os.getenv("GOOGLE_CLOUD_PROJECT"),
            database=os.getenv("FIRESTORE_DATABASE_ID", "confirm"),
        )
        doc_ref = db.collection("connection_test").document("ping")
        await doc_ref.set({"status": "ok", "timestamp": firestore.SERVER_TIMESTAMP})
        doc = await doc_ref.get()
        print("Write+Read successful:", doc.to_dict())
    except Exception as e:
        print(f"Error occurred: {type(e).__name__}: {str(e)}")

asyncio.run(main())
