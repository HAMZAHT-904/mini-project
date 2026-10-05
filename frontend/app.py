import re
import requests
import streamlit as st

BACKEND_URL = "http://127.0.0.1:8000/explain"

st.set_page_config(page_title="GitHub Repository Code Explainer", page_icon="📘")
st.title("📘 GitHub Repository Code Explainer")
st.caption("Paste a public GitHub repo URL. A local LLM (Ollama) explains it in simple language.")

repo_url = st.text_input("GitHub URL", placeholder="https://github.com/username/repository")

if st.button("Explain Repository", type="primary"):
    if not repo_url.strip():
        st.warning("Please enter a GitHub repository URL.")
    else:
        try:
            with st.spinner("Cloning repo and asking the local LLM... this can take 1-3 minutes."):
                resp = requests.post(BACKEND_URL, json={"repo_url": repo_url}, timeout=420)

            if resp.status_code == 200:
                text = resp.json()["explanation"]
                # Split on "## " headings and show each section in an expander
                parts = re.split(r"(?m)^## ", text)
                if len(parts) > 1:
                    for part in parts[1:]:
                        title, _, body = part.partition("\n")
                        with st.expander(title.strip(), expanded=True):
                            st.markdown(body.strip())
                else:
                    st.markdown(text)
            else:
                detail = resp.json().get("detail", "Unknown error")
                if isinstance(detail, list):  # Pydantic validation error
                    detail = detail[0].get("msg", "Invalid input").replace("Value error, ", "")
                st.error(detail)

        except requests.exceptions.ConnectionError:
            st.error("Cannot reach the backend. Start it with: cd backend && uvicorn main:app --port 8000")
        except requests.exceptions.Timeout:
            st.error("The request timed out. Try a smaller repository or a smaller model.")
