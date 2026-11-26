def search_documents(query, collection, embedding_model):
    if collection.count() == 0:
        return {
            "query": query,
            "results_found": 0,
            "results": []
        }

    query_embedding = embedding_model.encode(query).tolist()

    results = collection.query(
        query_embeddings=[query_embedding],
        n_results=min(5, collection.count())
    )

    search_results = []

    if results["documents"] and results["documents"][0]:
        for i in range(len(results["documents"][0])):
            search_results.append({
                "text": results["documents"][0][i],
                "filename": results["metadatas"][0][i]["filename"],
                "page": results["metadatas"][0][i]["page"],
                "distance": results["distances"][0][i]
            })

    return {
        "query": query,
        "results_found": len(search_results),
        "results": search_results
    }


def get_debug_chunks(collection):
    data = collection.get(
        include=["documents", "metadatas"]
    )

    return {
        "total_chunks": len(data["documents"]),
        "chunks": [
            {
                "text": doc,
                "page": meta["page"],
                "filename": meta["filename"]
            }
            for doc, meta in zip(
                data["documents"],
                data["metadatas"]
            )
        ]
    }
