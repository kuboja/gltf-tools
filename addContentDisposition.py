# pip install azure-storage-blob
from azure.storage.blob import BlobServiceClient
from urllib.parse import quote

# Nastavte připojovací řetězec a název kontejneru
CONNECTION_STRING = ""
CONTAINER_NAME = "production"
FOLDER_PATH = "venly/models/"  # Například "my-folder/"

# Inicializace klienta blob služby
blob_service_client = BlobServiceClient.from_connection_string(CONNECTION_STRING)
container_client = blob_service_client.get_container_client(CONTAINER_NAME)

def set_content_disposition_for_blobs():
    try:
        # Procházejte všechny bloby ve specifikované složce
        blobs = container_client.list_blobs(name_starts_with=FOLDER_PATH)
        for blob in blobs:
            blob_client = container_client.get_blob_client(blob.name)
            
            # Získání stávajících metadat a hlaviček
            blob_properties = blob_client.get_blob_properties()
            current_disposition = blob_properties.content_settings.content_disposition

            # Přeskočení, pokud Content-Disposition již existuje
            if current_disposition:
                print(f"Skipping blob (Content-Disposition already set): {blob.name}")
                continue

            # Vytvořte Content-Disposition hodnotu
            file_name = blob.name.split('/')[-1]  # Extrahování názvu souboru
            content_disposition = f"attachment; filename=\"{quote(file_name)}\""
            
            new_headers = blob_properties.content_settings
            new_headers.content_disposition = content_disposition
            
            # Aktualizace hlaviček blobu
            blob_client.set_http_headers(content_settings=new_headers)
            print(f"Updated Content-Disposition for blob: {blob.name}")

    except Exception as e:
        print(f"An error occurred: {e}")

if __name__ == "__main__":
    set_content_disposition_for_blobs()