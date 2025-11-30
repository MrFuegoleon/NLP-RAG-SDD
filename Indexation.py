from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_chroma import Chroma
from langchain_core.documents import Document

from pathlib import Path
import yaml
import re

class Indexation:
    def __init__(self, config_file: str = "config.yaml"):
        base_dir = Path(__file__).resolve().parent
        config_path = base_dir / config_file
        if not config_path.exists():
            raise FileNotFoundError(f"Config non trouvée : {config_path}")

        with open(config_path, "r", encoding="utf-8") as f:
            self.config = yaml.safe_load(f)

        self.pdf_directory = (base_dir / self.config["pdf_directory"]).resolve()
        self.vectorstore_directory = (base_dir / self.config["vectorstore_directory"]).resolve()

        # Text splitter
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=self.config["chunk_size"],
            chunk_overlap=self.config["chunk_overlap"],
            separators=self.config.get("separators", ["\n\n", "\n", " ", ""]),
            length_function=len,
        )

        # Embeddings
        self.embeddings = HuggingFaceEmbeddings(
            model_name=self.config["embedding_model"],
            model_kwargs={'device': self.config["device"]},
            encode_kwargs={'normalize_embeddings': self.config["normalize_embeddings"]}
        )

        self.vectorstore = None

    @staticmethod
    def _clean_text(text: str) -> str:
        """Nettoyage agressif mais intelligent – appliqué une seule fois à l'indexation"""
        if not text or not text.strip():
            return ""
        
        # 1. Normalisation des sauts de ligne
        text = re.sub(r'\n{3,}', '\n\n', text)  # max 2 \n consécutifs
        text = re.sub(r'[ \t]+', ' ', text)     # espaces multiples → 1 seul
        
        # 2. Supprime les headers/footers typiques des PDFs
        lines = text.split('\n')
        cleaned_lines = []
        for line in lines:
            line = line.strip()
            # Supprime les lignes très courtes ou numériques (numéros de page, etc.)
            if len(line) < 15:
                continue
            if line.isdigit():
                continue
            if line.lower().startswith(("page", "copyright", "http", "www.", "fig.", "tab.")):
                continue
            cleaned_lines.append(line)
        
        text = '\n'.join(cleaned_lines)
        
        # 3. Supprime les espaces en début/fin
        return text.strip()

    def load_and_split(self, pdf_names):
        all_docs = []

        for pdf_name in pdf_names:
            pdf_path = self.pdf_directory / pdf_name if not Path(pdf_name).is_absolute() else Path(pdf_name)
            if not pdf_path.exists():
                print(f"PDF introuvable : {pdf_path}")
                continue

            print(f"Chargement : {pdf_path.name}")
            loader = PyPDFLoader(str(pdf_path))
            pages = loader.load()

            for i, page in enumerate(pages):
                raw_text = page.page_content

                # NETTOYAGE DÈS LE CHARGEMENT
                clean_text = self._clean_text(raw_text)
                if not clean_text:
                    continue

                # Créer un document propre
                doc = Document(
                    page_content=clean_text,
                    metadata={
                        "source": str(pdf_path),
                        "document_name": pdf_path.stem,
                        "page": page.metadata.get("page", i + 1),
                    }
                )
                all_docs.append(doc)

            print(f"  → {len(pages)} pages chargées et nettoyées")

        # Split avec texte déjà propre
        self.splits = self.text_splitter.split_documents(all_docs)
        print(f"Total chunks créés (après nettoyage) : {len(self.splits)}")
        return self.splits

    def store(self):
        if not hasattr(self, 'splits') or not self.splits:
            raise ValueError("Aucun chunk à indexer. Lance load_and_split() d'abord.")

        print(f"Sauvegarde du vectorstore → {self.vectorstore_directory}")
        self.vectorstore_directory.mkdir(parents=True, exist_ok=True)

        self.vectorstore = Chroma.from_documents(
            documents=self.splits,
            embedding=self.embeddings,
            persist_directory=str(self.vectorstore_directory)
        )
        print("Indexation terminée – embeddings propres et dédupliqués")
        return self.vectorstore

    def load_vectorstore(self):
        if not self.vectorstore_directory.exists():
            raise FileNotFoundError(f"Vectorstore non trouvé : {self.vectorstore_directory}")
        
        print(f"Chargement du vectorstore propre depuis : {self.vectorstore_directory}")
        self.vectorstore = Chroma(
            persist_directory=str(self.vectorstore_directory),
            embedding_function=self.embeddings
        )
        return self.vectorstore

    def search(self, query: str, k: int = 6):
        if not self.vectorstore:
            self.load_vectorstore()
        return self.vectorstore.similarity_search(query, k=k)