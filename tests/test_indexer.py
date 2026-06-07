from rag.indexer import index_all, client, COLLECTION_NAME

def test_index_documents():
    index_all()
    
    collection = client.get_or_create_collection(name=COLLECTION_NAME)
    count = collection.count()
    
    print(f"Total chunks indexados: {count}")
    assert count > 0