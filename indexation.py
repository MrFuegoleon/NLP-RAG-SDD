from pathlib import Path
import re
import yaml

from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_chroma import Chroma
from langchain_core.documents import Document


class Indexation:
    """Handles PDF loading, cleaning, splitting, and vectorstore indexing."""

    def __init__(self, config_file: str = "config.yaml"):
        base_dir = Path(__file__).resolve().parent
        config_path = base_dir / config_file
        if not config_path.exists():
            raise FileNotFoundError(f"Config not found: {config_path}")

        with open(config_path, "r", encoding="utf-8") as f:
            self.config = yaml.safe_load(f)

        self.pdf_directory = (base_dir / self.config["pdf_directory"]).resolve()
        self.vectorstore_directory = (
            base_dir / self.config["vectorstore_directory"]
        ).resolve()

        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=self.config["chunk_size"],
            chunk_overlap=self.config["chunk_overlap"],
            separators=self.config.get("separators", ["\n\n", "\n", " ", ""]),
            length_function=len,
        )

        self.embeddings = HuggingFaceEmbeddings(
            model_name=self.config["embedding_model"],
            model_kwargs={"device": self.config["device"]},
            encode_kwargs={"normalize_embeddings": self.config["normalize_embeddings"]},
        )

        self.vectorstore = None

    @staticmethod
    def _clean_text(text: str) -> str:
        """Cleans extracted PDF text aggressively but safely."""

        if not text or not text.strip():
            return ""

        text = re.sub(r"\n{3,}", "\n\n", text)
        text = re.sub(r"[ \t]+", " ", text)

        cleaned_lines = []
        for line in text.split("\n"):
            line = line.strip()
            if len(line) < 15:
                continue
            if line.isdigit():
                continue
            if line.lower().startswith(
                ("page", "copyright", "http", "www.", "fig.", "tab.")
            ):
                continue
            cleaned_lines.append(line)

        return "\n".join(cleaned_lines).strip()

    def load_and_split(self, pdf_names):
        """Loads PDF files, cleans pages, and splits text into chunks."""
        all_docs = []

        for pdf_name in pdf_names:
            pdf_path = (
                self.pdf_directory / pdf_name
                if not Path(pdf_name).is_absolute()
                else Path(pdf_name)
            )
            if not pdf_path.exists():
                print(f"PDF missing: {pdf_path}")
                continue

            loader = PyPDFLoader(str(pdf_path))
            pages = loader.load()

            for i, page in enumerate(pages):
                clean_text = self._clean_text(page.page_content)
                if not clean_text:
                    continue

                doc = Document(
                    page_content=clean_text,
                    metadata={
                        "source": str(pdf_path),
                        "document_name": pdf_path.stem,
                        "page": page.metadata.get("page", i + 1),
                    },
                )
                all_docs.append(doc)

        self.splits = self.text_splitter.split_documents(all_docs)
        return self.splits

    def store(self):
        """Persists the chunks into a Chroma vectorstore."""
        if not hasattr(self, "splits") or not self.splits:
            raise ValueError("No chunks to index. Run load_and_split() first.")

        self.vectorstore_directory.mkdir(parents=True, exist_ok=True)

        self.vectorstore = Chroma.from_documents(
            documents=self.splits,
            embedding=self.embeddings,
            persist_directory=str(self.vectorstore_directory),
        )
        return self.vectorstore

    def load_vectorstore(self):
        """Loads an existing Chroma vectorstore from disk."""
        if not self.vectorstore_directory.exists():
            raise FileNotFoundError(
                f"Vectorstore not found: {self.vectorstore_directory}"
            )

        self.vectorstore = Chroma(
            persist_directory=str(self.vectorstore_directory),
            embedding_function=self.embeddings,
        )
        return self.vectorstore

    def search(self, query: str, k: int = 6):
        """Performs a similarity search on the vectorstore."""
        if not self.vectorstore:
            self.load_vectorstore()
        return self.vectorstore.similarity_search(query, k=k)


if __name__ == "__main__":
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
    vector_store = indexer.load_vectorstore()
