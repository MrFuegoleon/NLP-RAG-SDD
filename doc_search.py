"""from src import Chroma
"""
from Indexation import Indexation

class DocumentRetriever:
    def __init__(self, vector_store=None):
        self.vector_store = vector_store

    def retrieve_by_score_threshold(self, query: str, threshold: float = 0.68, k: int = 15):
        """
        Recherche les k documents les plus proches et filtre
        ceux dont la DISTANCE <= threshold.
        """
        if self.vector_store is None:
            raise ValueError("Vectorstore not loaded. Call load_vectorstore().")

        results = self.vector_store.similarity_search_with_score(query, k=k)

        """# DEBUG : afficher tous les scores
        print("\n--- SCORES BRUTS ---")
        for doc, score in results:
            print(f"SCORE={score:.3f} | {doc.metadata.get('document_name')} (page {doc.metadata.get('page')})")
        print("--------------------\n")"""

        filtered = [doc for doc, score in results if score <= threshold]

        # Si rien ne passe le seuil, on renvoie quand même les meilleurs
        if not filtered:
            print("Aucun document, on renvoie quand même les top-k (sans filtre).")
            filtered = [doc for doc, score in results]

        return filtered

    def retrieve_top_k(self, query: str, k: int = 5):
        """
        Search the top k documents similar to the question
        """
        if self.vector_store is None:
            raise ValueError("Vectorstore not loaded. Call load_vectorstore().")

        return self.vector_store.similarity_search(query, k=k)





if __name__=="__main__":
    indexer = Indexation("config.yaml")

    pdfs = [
        "9782340031159_extrait.pdf",
        "histoire_des_idees_geopolitiques-2.pdf",
        "Introduction-to-Geopolitics.pdf",
        "Lageopolitique.pdf",
        "pdf_quest_ce_que_la_geopolitique.pdf",
    ]


    indexer.load_and_split(pdfs)


    indexer.store()

    # Recharger (pour tester)
    vector_store = indexer.load_vectorstore()

    retriever = DocumentRetriever(vector_store=vector_store)


    #results = retriever.retrieve_top_k("Qu'est ce que la géopolitique", k=5)
    results = retriever.retrieve_by_score_threshold("Quelle est la théorie du Heartland de Mackinder?", threshold=0.8, k=10)


    for r in results:
        print("Source:", r.metadata["source"])
        print("Document:", r.metadata["document_name"])
        print("Page:", r.metadata["page"])
        print("Content:", r.page_content[:200], "...")
        print("-----")
