# GitHub Repository Code Explainer

Local GenAI app: GitHub URL -> GitPython clone -> file filtering -> Ollama (qwen2.5:3b) -> Streamlit.

## 1. Install prerequisites
- Git: https://git-scm.com
- Python 3.10+
- Ollama: https://ollama.com/download  (Linux: `curl -fsSL https://ollama.com/install.sh | sh`)

## 2. Download the model (Terminal)
```
ollama pull qwen2.5:3b
ollama run qwen2.5:3b      # test it, type /bye to exit
```
Check Ollama is running: open http://localhost:11434 ("Ollama is running").

## 3. Python setup (Terminal, inside github-code-explainer/)
```
python -m venv venv
venv\Scripts\activate          # Mac/Linux: source venv/bin/activate
pip install -r backend/requirements.txt
```

## 4. Run
Terminal 1 (backend):
```
cd backend
uvicorn main:app --port 8000
```
Terminal 2 (frontend, from project root, venv activated):
```
streamlit run frontend/app.py
```
Open http://localhost:8501 and try `https://github.com/pallets/click`.

## Troubleshooting
- "Cannot reach the backend": Terminal 1 is not running.
- "Ollama is not running": open the Ollama app or run `ollama serve`.
- "Model not installed": `ollama pull qwen2.5:3b`.
- Slow/timeouts: use `qwen2.5:1.5b` and change MODEL_NAME in backend/llm_service.py.
