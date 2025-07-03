from pymongo import MongoClient
from pymongo.errors import CollectionInvalid
from core.config import Settings

MONGO_URI = Settings.DATABASE_URL
client = MongoClient(MONGO_URI)
db = client["bedrock"]


# Remove the required fields from the schema as we'll go forward to make it more flexible - fyxod
user_schema = {
    "$jsonSchema": {
        "bsonType": "object",
        "required": ["userId", "name", "email", "password", "is_active", "threads"],
        "properties": {
            "userId": {"bsonType": "string"},
            "name": {"bsonType": "string"},
            "email": {"bsonType": "string"},
            "password": {"bsonType": "string"},
            "is_active": {"bsonType": "bool"},
            "threads": {
                "bsonType": "object",
                "additionalProperties": {
                    "bsonType": "object",
                    "required": ["documents", "chats", "createdAt", "updatedAt"],
                    "properties": {
                        "documents": {
                            "bsonType": "array",
                            "items": {
                                "bsonType": "object",
                                "required": ["docId", "title", "type", "time_uploaded", "file_name"],
                                "properties": {
                                    "docId": {"bsonType": "string"},
                                    "title": {"bsonType": "string"},
                                    "type": {"bsonType": "string"},
                                    "file_name": {"bsonType": "string"},
                                    "time_uploaded": {"bsonType": "date"}
                                }
                            }
                        },
                        "chats": {
                            "bsonType": "array",
                            "items": {
                                "bsonType": "object",
                                "required": ["type", "message", "createdAt", "updatedAt"],
                                "properties": {
                                    "type": {"enum": ["agent", "user"]},
                                    "message": {"bsonType": "string"},
                                    "createdAt": {"bsonType": "date"},
                                    "updatedAt": {"bsonType": "date"}
                                }
                            }
                        },
                        "createdAt": {"bsonType": "date"},
                        "updatedAt": {"bsonType": "date"}
                    }
                }
            }
        }
    }
}

try:
    db.create_collection("users", validator=user_schema)
    print("Collection 'users' created with schema validation.")
except CollectionInvalid:
    print("Collection 'users' already exists.")
except Exception as e:
    print("Error creating collection:", e)
