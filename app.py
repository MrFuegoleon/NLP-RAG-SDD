import os
import sys
from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "")))

from rag_llm import RagLLM

app = Flask(__name__)
CORS(app)

DATA_FOLDER = "./data"
os.makedirs(DATA_FOLDER, exist_ok=True)

# Initialize the model once


@app.route("/", methods=["POST"])
def home():
    #  Validate API Key

    api_key = request.form.get("api_key").strip()
    print("API KEY", api_key)
    if not api_key:
        return jsonify({"error": "Please provide an API key!"}), 400

    nlp_model = RagLLM(config_file="config.yaml", api_key=api_key)

    # if not api_key:
    #     return jsonify({"error": "Please provide an API key!"}), 400

    #  Handle File Uploads
    incoming_files = request.files.getlist("files")

    # Check if we actually have valid files incoming
    has_valid_incoming = False
    if len(incoming_files) > 0 and incoming_files[0].filename != "":
        has_valid_incoming = True

    # Check existing files
    existing_files = [
        f
        for f in os.listdir(DATA_FOLDER)
        if os.path.isfile(os.path.join(DATA_FOLDER, f))
    ]

    if not existing_files and not has_valid_incoming:
        return (
            jsonify(
                {
                    "error": "Please attach at least one file because there is no context."
                }
            ),
            400,
        )

    saved_count = 0
    if has_valid_incoming:
        for file in incoming_files:
            if file.filename:
                file_path = os.path.join(DATA_FOLDER, file.filename)
                file.save(file_path)
                saved_count += 1

        try:
            nlp_model.process_new_files()
        except Exception as e:
            print(f"Indexing error: {e}")
            return jsonify({"error": "Failed to process/index uploaded files."}), 500

    prompt = request.form.get("prompt", "")
    if prompt.strip() == "":
        return jsonify({"error": "Prompt cannot be empty!"}), 400

    try:
        answer, sources = nlp_model.ask(prompt)

        return jsonify(
            {"message": answer, "sources": sources, "saved_files": saved_count}
        )
    except Exception as e:
        print(f"LLM Error: {e}")
        return jsonify({"error": str(e)}), 500


@app.route("/files", methods=["GET"])
def list_files():
    try:
        files = [
            {"name": f}
            for f in os.listdir(DATA_FOLDER)
            if os.path.isfile(os.path.join(DATA_FOLDER, f))
        ]
        return jsonify(files)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/files/<filename>", methods=["GET", "DELETE"])
def file_operations(filename):
    file_path = os.path.join(DATA_FOLDER, filename)

    if request.method == "GET":
        if os.path.exists(file_path):
            return send_from_directory(DATA_FOLDER, filename)
        return jsonify({"error": "File not found"}), 404

    if request.method == "DELETE":
        if os.path.exists(file_path):
            os.remove(file_path)
            return jsonify({"message": f"{filename} deleted"})
        return jsonify({"error": "File not found"}), 404


if __name__ == "__main__":
    app.run(debug=True, port=5000)
