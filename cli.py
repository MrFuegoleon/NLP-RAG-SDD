"""
CLI tool to manage the backend and frontend services of the RAG project.
Provides commands to start the Flask API server, launch the frontend development server,
send test prompts directly to the backend, and run both backend and frontend together.
"""

import typer
import subprocess
from pathlib import Path

cli = typer.Typer(help="CLI to manage backend and frontend services")


@cli.command()
def serve():
    """
    Start the Flask backend by running app.py.
    Use this command to launch the API server.
    """
    typer.echo("Starting Flask backend (app.py)...")
    subprocess.run(["python", "app.py"])


@cli.command()
def front(path: str = "front"):
    """
    Start the frontend development server.
    Specify the folder containing the frontend project.
    """
    project_path = Path(path).resolve()
    if not project_path.exists():
        typer.echo(f"Frontend directory not found: {project_path}")
        raise typer.Exit(1)
    typer.echo(f"Starting frontend in: {project_path}")
    subprocess.run(["npm", "install"], cwd=project_path)
    subprocess.run(["npm", "run", "dev"], cwd=project_path)


@cli.command()
def ask(prompt: str, api_key: str):
    """
    Send a prompt to the running backend server.
    This command helps to test the API directly from the CLI.
    """
    import requests

    try:
        response = requests.post(
            "http://127.0.0.1:5000/", data={"prompt": prompt, "api_key": api_key}
        )
        typer.echo(response.json())
    except Exception as e:
        typer.echo(f"Request failed: {e}")


@cli.command()
def dev(front_path: str = "front"):
    """
    Start both backend and frontend in one command.
    Backend runs in the background while frontend is active.
    """
    typer.echo("Starting backend...")
    backend_proc = subprocess.Popen(["python", "app.py"])

    project_path = Path(front_path).resolve()
    if not project_path.exists():
        typer.echo(f"Frontend directory not found: {project_path}")
        backend_proc.terminate()
        raise typer.Exit(1)

    typer.echo(f"Starting frontend in {project_path}...")
    try:
        subprocess.run(["npm", "install"], cwd=project_path)
        subprocess.run(["npm", "run", "dev"], cwd=project_path)
    finally:
        typer.echo("Shutting down backend...")
        backend_proc.terminate()


if __name__ == "__main__":
    cli()
