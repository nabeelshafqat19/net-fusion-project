import os
from azure.storage.blob import BlobServiceClient

# ----------------- CONFIGURATION -----------------
connection_string = "BlobEndpoint=https://staticwebhostinghomepage.blob.core.windows.net/;QueueEndpoint=https://staticwebhostinghomepage.queue.core.windows.net/;FileEndpoint=https://staticwebhostinghomepage.file.core.windows.net/;TableEndpoint=https://staticwebhostinghomepage.table.core.windows.net/;SharedAccessSignature=sv=2026-02-06&ss=bfqt&srt=sco&sp=rwdlacupiytfx&se=2026-06-11T03:44:42Z&st=2026-06-10T19:29:42Z&spr=https&sig=96V7jWP6Jlnf1arDFzY%2BkoyrwHDkKlnq3I%2FVB%2FOiMks%3D"
container_name = "newfusionproject"
download_folder = r"C:\Users\TestMachine\Desktop\Net fusion"
# -------------------------------------------------

blob_service_client = BlobServiceClient.from_connection_string(
    connection_string
)

container_client = blob_service_client.get_container_client(
    container_name
)

def download_container(container_client, local_path):
    """
    Download all files and folders from an Azure Blob container.
    """

    os.makedirs(local_path, exist_ok=True)

    blobs = container_client.list_blobs()

    for blob in blobs:
        blob_name = blob.name

        # Create local file path preserving folder structure
        local_file_path = os.path.join(
            local_path,
            blob_name.replace("/", os.sep)
        )

        # Create parent directories if needed
        os.makedirs(
            os.path.dirname(local_file_path),
            exist_ok=True
        )

        print(f"Downloading {blob_name} -> {local_file_path}")

        with open(local_file_path, "wb") as file:
            download_stream = container_client.download_blob(blob_name)
            file.write(download_stream.readall())

    print("Download completed successfully!")

download_container(container_client, download_folder)