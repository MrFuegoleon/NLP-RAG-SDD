# rag_evaluator.py — VERSION DÉFINITIVE 2025 — TOUT FONCTIONNE
import os
import json
import time
import pandas as pd
from pathlib import Path
from tqdm import tqdm
from dotenv import load_dotenv

from datasets import Dataset
from ragas import evaluate
from ragas.metrics import (
    faithfulness,
    answer_relevancy,
    context_precision,
    context_recall,
)

from langchain_openai import ChatOpenAI
from rag_llm import RagLLM

load_dotenv()

class RAGEvaluator:
    def __init__(self, config_file: str = "config.yaml"):
        self.base_dir = Path(__file__).parent
        self.input_csv = self.base_dir / "evaluation_dataset_and_metrics" / "questions_geopolitiques.csv"
        self.output_csv = self.base_dir / "evaluation_dataset_and_metrics" / "questions_geopolitiques_enriched_ragas.csv"

        if not os.getenv("OPENAI_API_KEY"):
            raise ValueError("OPENAI_API_KEY manquante dans .env")
        print("Clé OpenAI chargée → GPT-4o-mini comme juge")

        print("Chargement du RAG...")
        self.rag = RagLLM(config_file=config_file)
        print("RAG chargé avec succès")

        self.judge_llm = ChatOpenAI(model="gpt-4o-mini", temperature=0.0)

    def enrich_dataset(self, resume: bool = True):
        print(f"\nÉTAPE 1 : Enrichissement du dataset → {self.output_csv.name}")

        if not self.input_csv.exists():
            raise FileNotFoundError(f"Fichier manquant : {self.input_csv}")

        df = pd.read_csv(self.input_csv)

        start_idx = 0
        if resume and self.output_csv.exists():
            try:
                existing = pd.read_csv(self.output_csv, sep="|")
                start_idx = len(existing)
                print(f"Reprise à la question {start_idx + 1}/{len(df)}")
            except:
                print("Fichier corrompu → recréation")
                start_idx = 0

        if start_idx == 0:
            cols = ["question", "reponse_gold", "answer", "contexts", "sources_json"]
            pd.DataFrame(columns=cols).to_csv(self.output_csv, sep="|", index=False, encoding="utf-8")

        pbar = tqdm(total=len(df), initial=start_idx, desc="RAG → Réponses", unit="q")

        for i in range(start_idx, len(df)):
            row = df.iloc[i]
            question = row["question"]

            try:
                answer, sources = self.rag.ask(question)

                # 7 meilleurs chunks
                docs = self.rag.indexer.vectorstore.similarity_search_with_score(question, k=20)
                relevant = [d for d, s in docs if s < 0.35][:7]
                contexts = [d.page_content for d in relevant]

                new_row = {
                    "question": question,
                    "reponse_gold": row["reponse_gold"],
                    "answer": answer,
                    "contexts": json.dumps(contexts, ensure_ascii=False),
                    "sources_json": json.dumps(sources, ensure_ascii=False)
                }

                pd.DataFrame([new_row]).to_csv(self.output_csv, sep="|", mode="a", header=False, index=False, encoding="utf-8")
                pbar.set_postfix({"status": "OK"})

            except Exception as e:
                print(f"\nERREUR question {i+1} : {e}")
                new_row = {
                    "question": question,
                    "reponse_gold": row["reponse_gold"],
                    "answer": f"[ERREUR] {e}",
                    "contexts": "[]",
                    "sources_json": "[]"
                }
                pd.DataFrame([new_row]).to_csv(self.output_csv, sep="|", mode="a", header=False, index=False, encoding="utf-8")

            pbar.update(1)
            time.sleep(0.6)

        pbar.close()
        print("Enrichissement terminé")

    def evaluate_with_ragas(self):
        print(f"\nÉTAPE 2 : Évaluation RAGAS")

        df = pd.read_csv(self.output_csv, sep="|")

        df_valid = df[
            df["answer"].notna() &
            (df["answer"].str.len() > 100) &
            (df["contexts"].str.len() > 20) &
            (~df["answer"].str.contains("ERREUR", na=False))
        ].copy().reset_index(drop=True)

        print(f"{len(df_valid)} questions valides → lancement RAGAS")

        # Conversion JSON → list
        df_valid["contexts"] = df_valid["contexts"].apply(
            lambda x: json.loads(x) if isinstance(x, str) else []
        )

        # RAGAS exige : question, answer, contexts, reference
        df_valid = df_valid.rename(columns={"reponse_gold": "reference"})

        dataset = Dataset.from_pandas(df_valid[["question", "answer", "contexts", "reference"]])

        print("Évaluation RAGAS en cours (GPT-4o-mini)...")
        results = evaluate(
            dataset=dataset,
            metrics=[faithfulness, answer_relevancy, context_precision, context_recall],
            llm=self.judge_llm,
        )

        # ==================== RÉSULTATS ====================
        print("\n" + "═" * 90)
        print("           RÉSULTATS FINAUX RAGAS ")
        print("═" * 90)

        df_res = results.to_pandas()
        mean_scores = df_res.mean(numeric_only=True)

        for metric, score in mean_scores.items():
            level = "ÉLITE" if score >= 0.90 else "TOP" if score >= 0.85 else "SOLIDE"
            print(f"  • {metric:18} → {score:.4f}  → {level}")

        global_score = mean_scores.mean()
        print(f"\nSCORE GLOBAL RAGAS : {global_score:.4f}")
        print("NIVEAU :", "ÉLITE MONDIALE" if global_score >= 0.90 else "TOP 5% MONDIAL" if global_score >= 0.85 else "UN PEU SOLIDE")

        # Sauvegarde finale
        out_dir = self.base_dir / "evaluation_dataset_and_metrics"
        df_res.to_csv(out_dir / "RAGAS_RÉSULTATS_COMPLETS.csv", sep="|", index=False)
        pd.DataFrame([mean_scores]).to_csv(out_dir / "RAGAS_SCORES_MOYENS.csv", sep="|")

        print("\nTout sauvegardé avec séparateur |")
        print("FIN DE L'EVALUATION.")

    def run_all(self):
        self.enrich_dataset(resume=True)
        self.evaluate_with_ragas()


# ====================== LANCEMENT ======================
if __name__ == "__main__":
    evaluator = RAGEvaluator()
    #evaluator.run_all() 
    # decommanter pour executer la construction du  datasset . cela prend 4h  minimum,sinon laissé , le datasset est deja construit.  
    # evaluator.enrich_dataset() # → Seulement enrichir
    #decommenter pour avoir les performance du modele
    #evaluator.evaluate_with_ragas()