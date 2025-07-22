from pymongo import MongoClient
import os

def get_mongo_client():
    """
    Crea un cliente MongoDB usando variables de entorno.
    Usa 'mongo' como host por defecto (ideal en Docker con docker-compose).
    """
    host = os.getenv("MONGO_HOST", "mongo")  # por defecto "mongo"
    port = int(os.getenv("MONGO_PORT", 27017))
    return MongoClient(host=host, port=port)

def get_mongo_db():
    """
    Devuelve la base de datos definida en MONGO_DB (o 'project2' por default).
    """
    client = get_mongo_client()
    db_name = os.getenv("MONGO_DB", "project2")
    return client[db_name]

def clean_collection(db, collection_name, field_filters=None):
    """
    Elimina documentos con valores nulos/vacíos según los filtros.
    field_filters: dict -> { "field_name": [None, ""] }
    """
    col = db[collection_name]
    deleted = 0
    if field_filters:
        for field, values in field_filters.items():
            result = col.delete_many({field: {"$in": values}})
            deleted += result.deleted_count
    return deleted

def create_index_if_missing(collection, fields, unique=False):
    """
    Crea un índice compuesto o simple si no existe.
    fields: str o list de tuplas [("campo", 1)]
    """
    if isinstance(fields, str):
        fields = [(fields, 1)]
    return collection.create_index(fields, unique=unique)
