"""from src import Chroma"""

from indexation import Indexation


class DocumentRetriever:
    def __init__(self, vector_store=None):
        self.vector_store = vector_store

    def retrieve_by_score_threshold(
        self, query: str, threshold: float = 0.68, k: int = 15
    ):
        """
        Recherche les k documents les plus proches et filtre
        ceux dont la DISTANCE <= threshold.
        """
        if self.vector_store is None:
            raise ValueError("Vectorstore not loaded. Call load_vectorstore().")

        results = self.vector_store.similarity_search_with_score(query, k=k)

        filtered = [doc for doc, score in results if score <= threshold]

        # Si rien ne passe le seuil, on renvoie quand même les meilleurs
        if not filtered:
            print("Aucun document, on renvoie quand même les top-k (sans filtre).")
            filtered = [doc for doc, score in results]

        return filtered

    def retrieve_by_best_score(self, query: str, threshold: float = 0.7):
        """Search and filter by similarity threshold with adaptive fallback."""
        if self.vector_store is None:
            raise ValueError("Vectorstore not loaded. Call load_vectorstore().")

        results = self.vector_store.similarity_search_with_score(query)

        if not results:
            print("No results returned from vector store.")
            return []

        filtered = [doc for doc, score in results if score >= threshold]

        if not filtered:
            print(f"No documents found with threshold {threshold}.")
            best_score = max(score for _, score in results)
            adaptive_threshold = best_score * 0.8
            filtered = [doc for doc, score in results if score >= adaptive_threshold]
            print(
                f"Using adaptive threshold: {adaptive_threshold:.2f} "
                f"(80% of best score: {best_score:.2f})"
            )

        return filtered

    def retrieve_top_k(self, query: str, k: int = 5):
        """
        Search the top k documents similar to the question
        """
        if self.vector_store is None:
            raise ValueError("Vectorstore not loaded. Call load_vectorstore().")

        return self.vector_store.similarity_search(query, k=k)


