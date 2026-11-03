# Ahmedabad Municipal Corporation (AMC) — Municipal Operations & Knowledge Copilot
> **SSIP 2.0 (Smart Solution & Innovation Platform) • SEVA FIRST**

An AI-powered municipal knowledge retrieval, policy comparison, and document management system built for municipal administrative efficiency, citizen grievance resolution, and regulatory compliance.

---

## 🏛️ Overview

Municipal administrative circulars, resolutions, tenders, and operational guidelines are voluminous, distributed, and frequently revised. The **Municipal Knowledge Copilot** provides:

1. **Context-Aware Municipal Q&A (RAG):** Natural-language grievance response and regulatory lookup powered by local Ollama LLMs (`qwen2.5:3b`) with interactive, verified document citations (`[S1]`, `[S2]`).
2. **Multi-Format Ingestion:** Ingest and chunk PDFs, Microsoft Word (`.docx`), and text (`.txt`) circulars with page-level metadata.
3. **Policy Version Diff & Amendment Analysis:** Deep semantic comparison of circulars and policy amendments across 12 structured dimensions (SLAs, timelines, penalties, operational mandates).
4. **AI Document Summarizer:** Structured, 5-point executive summaries preserving operational deadlines, departmental responsibilities, and procedural requirements.
5. **Role-Based Access Control (RBAC):**
   - **Admin (Commissioner):** Full administrative control (document ingestion, repository pruning, audit log compliance management).
   - **Department Officer:** Departmental operational access (policy comparison, document summarization, read-only audit review).
   - **Desk Assistant:** Frontline citizen inquiry resolution and document lookups with executive summarization.
6. **Administrative Governance & Audit Trail:** SQLite-backed audit recording logging every query, responding officer role, source citations, latency, and compliance status.

---

## 🛠️ Tech Stack

- **Backend:** Python 3.12, FastAPI, Uvicorn
- **Vector Database:** ChromaDB (`all-MiniLM-L6-v2` embeddings via `sentence-transformers`)
- **LLM Engine:** Local Ollama (`qwen2.5:3b`) with 30-minute memory keep-alive
- **Document Parsing:** PyMuPDF (`fitz`) with OCR fallback, `python-docx`
- **Frontend:** React 19, Vite, Lucide Icons
- **Design Aesthetic:** Flat, minimalist government knowledge system (Cosmic Latte / Ivory Paper, Deep Petrol, Charcoal Ink, Heritage Green, Terracotta Bronze)

---

## 🚀 Quick Start (One-Click Launch on Windows)

1. **Ensure Ollama is running** with `qwen2.5:3b`:
   ```bash
   ollama run qwen2.5:3b
   ```

2. **Double-click `run_copilot.bat`** in the project root:
   - Starts the FastAPI backend at `http://127.0.0.1:8000`
   - Starts the React frontend at `http://127.0.0.1:5173`
   - Automatically opens your default browser

---

## 📦 Manual Installation & Setup

### 1. Prerequisites
- Python 3.10+
- Node.js 18+ & npm
- [Ollama](https://ollama.com/) with `qwen2.5:3b` pulled

### 2. Backend Setup
```bash
cd backend
python -m venv venv
.\venv\Scripts\activate      # On Windows (or 'source venv/bin/activate' on Linux/macOS)
pip install -r requirements.txt
python -m uvicorn main:app --host 127.0.0.1 --port 8000
```

### 3. Frontend Setup
```bash
cd frontend
npm install
npm run dev
```
Open `http://localhost:5173` in your browser.

---

## 🔒 Security & Privacy
- **100% Local Inference:** All documents, vector embeddings, and LLM inferences remain strictly on-premises; zero citizen or administrative data is transmitted to third-party cloud APIs.
- **Audit Compliance:** Every query asked by officers or assistants is recorded with timestamps, user roles, latency, and citations for administrative transparency.
