import os
import json
from pathlib import Path

import yaml
from openai import OpenAI
from indexation import Indexation
from doc_search import DocumentRetriever

from dotenv import load_dotenv


class RagLLM:
    """RAG + LLM pipeline using retriever context and OpenRouter API."""

    def __init__(self, config_file: str = "config.yaml", api_key: str = ""):
        if not api_key:
            raise ValueError("API key must be provided via the api_key parameter.")

        self.base_dir = Path(__file__).resolve().parent
        config_path = self.base_dir / config_file
        if not config_path.exists():
            raise FileNotFoundError(f"Config file not found: {config_path}")

        with open(config_path, "r", encoding="utf-8") as f:
            self.config = yaml.safe_load(f)

        llm_cfg = self.config.get("llm", {})
        self.model_name = llm_cfg.get("model", "nex-agi/deepseek-v3.1-nex-n1:free")
        self.history_size = llm_cfg.get("history_size", 5)
        self.temperature = llm_cfg.get("temperature", 0.2)
        self.max_tokens = llm_cfg.get("max_tokens", 2048)
        self.top_p = llm_cfg.get("top_p", 0.95)
        self.random_seed = llm_cfg.get("random_seed", None)
        self.enable_reasoning = llm_cfg.get("reasoning", False)

        self.api_key = api_key or os.getenv("OPENROUTER_API_KEY")

        retr_cfg = self.config.get("retriever", {})
        self.retr_k = retr_cfg.get("k", 20)
        self.retr_threshold = retr_cfg.get("threshold", 0.3)

        prompt_cfg = self.config.get("prompt", {})
        self.prompt_template = prompt_cfg.get("template", "{context}\n\n{question}")

        self.client = OpenAI(
            base_url="https://openrouter.ai/api/v1",
            api_key=self.api_key,
        )

        self.indexer = Indexation(config_file=config_file)
        vectorstore = self.indexer.load_vectorstore()
        self.retriever = DocumentRetriever(vector_store=vectorstore)

        self.history_path = self.base_dir / "history.json"
        self.history = self._load_history()

    def _load_history(self):
        """Load chat history from disk."""
        if self.history_path.exists():
            try:
                with open(self.history_path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                return []
        return []

    def _save_history(self):
        """Save chat history to disk."""
        with open(self.history_path, "w", encoding="utf-8") as f:
            json.dump(self.history, f, ensure_ascii=False, indent=2)

    def _update_history(self, question: str, answer: str):
        """Update history and trim to max history size."""
        self.history.append({"question": question, "answer": answer})
        if len(self.history) > self.history_size:
            self.history = self.history[-self.history_size :]
        self._save_history()

    def _format_history(self) -> str:
        """Format previous Q/A pairs for injection into the prompt."""
        if not self.history:
            return ""
        parts = []
        for item in self.history:
            parts.append(f"Q: {item['question']}\nR: {item['answer']}")
        return "Historique des échanges récents :\n" + "\n\n".join(parts)

    def _build_context_from_retriever(self, question: str):
        """Retrieve relevant context chunks from vectorstore."""
        docs = self.retriever.retrieve_by_score_threshold(
            query=question,
            threshold=self.retr_threshold,
            k=self.retr_k,
        )

        if not docs:
            return "Aucun contexte pertinent n'a été trouvé dans les documents.", []

        context = "\n\n".join(d.page_content for d in docs)
        return context, docs

    def _build_prompt(self, question: str, context: str) -> str:
        """Build the final prompt with context, history, and question."""
        history_text = self._format_history()
        prompt = self.prompt_template.format(
            question=question,
            context=context,
            history=history_text,
        )
        return prompt

    def _call_llm(self, prompt: str) -> str:
        """Call the LLM on OpenRouter with configured parameters."""
        messages = [{"role": "user", "content": prompt}]

        params = {
            "model": self.model_name,
            "messages": messages,
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
            "top_p": self.top_p,
            "stream": False,
        }

        if self.random_seed:
            params["seed"] = self.random_seed

        if self.enable_reasoning:
            params["reasoning"] = {"enabled": True}

        try:
            response = self.client.chat.completions.create(**params)
            return response.choices[0].message.content

        except Exception as e:
            if "rate limit" in str(e).lower():
                raise ValueError("OpenRouter quota exceeded.")
            elif "model not found" in str(e).lower():
                raise ValueError(f"Model '{self.model_name}' not found.")
            else:
                raise ValueError(f"LLM call error: {e}")

    def ask(self, question: str):
        """Run the full RAG pipeline and return answer and sources."""
        context, docs = self._build_context_from_retriever(question)
        prompt = self._build_prompt(question, context)
        answer = self._call_llm(prompt)
        self._update_history(question, answer)

        seen = set()
        sources = []
        if (
            answer
            != "Cette information n'est pas disponible dans les documents fournis."
        ):
            for d in docs:
                key = (d.metadata.get("document_name"), d.metadata.get("page"))
                if key in seen:
                    continue
                seen.add(key)
                sources.append(
                    {
                        "source": d.metadata.get("source"),
                        "document_name": key[0],
                        "page": key[1],
                    }
                )

        return answer, sources
