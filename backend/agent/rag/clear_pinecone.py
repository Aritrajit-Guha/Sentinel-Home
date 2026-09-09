import os

from dotenv import load_dotenv
from pinecone import Pinecone


def main():

    # Load .env
    load_dotenv(override=True)

    pinecone_api_key = os.getenv("PINECONE_API_KEY")
    pinecone_index_name = os.getenv("PINECONE_INDEX")

    if not pinecone_api_key:
        raise ValueError("PINECONE_API_KEY is missing")

    if not pinecone_index_name:
        raise ValueError("PINECONE_INDEX is missing")

    # Connect to Pinecone
    pc = Pinecone(api_key=pinecone_api_key)

    index = pc.Index(pinecone_index_name)

    print(f"Index: {pinecone_index_name}")

    # Show current count
    stats = index.describe_index_stats()

    print(
        f"Current vector count: "
        f"{stats.get('total_vector_count', 0)}"
    )

    # Confirmation
    confirm = input(
        "\nType 'DELETE' to delete ALL records: "
    )

    if confirm != "DELETE":
        print("Deletion cancelled.")
        return

    # Delete all vectors
    index.delete(delete_all=True)

    print("\nAll records deleted successfully.")


if __name__ == "__main__":
    main()