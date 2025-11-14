# NLP-RAG-SDD

## Installation

Here is a custom installer that will install Poetry in a new virtual environment and allow Poetry to manage its own environment if you don’t already have it installed.


**Linux, macOS, Windows (WSL)**

```bash
curl -sSL https://install.python-poetry.org | python3 -
```

**Windows (Powershell)**

```powershell
(Invoke-WebRequest -Uri https://install.python-poetry.org -UseBasicParsing).Content | py -
```
If you have installed Python through the Microsoft Store, replace py with python in the command above.

To install the defined dependencies for your project, just run the install command.

```
poetry install
```
