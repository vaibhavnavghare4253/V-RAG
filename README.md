# AdaptiveDocAI: Adaptive Multimodal RAG with Uncertainty Awareness

AdaptiveDocAI is a research-grade and production-ready intelligent document-question-answering platform. It dynamically retrieves evidence from multi-page PDFs containing text, tables, charts, figures, and scans, computes calibrated multi-factor uncertainty, and avoids hallucinations by selectively abstaining when document evidence is insufficient.

---

## 🎯 Dual Project Goals

1. **Research Outcome:** Scientifically evaluable comparative benchmarks against:
   - **Baseline A:** Standard Text-Only RAG
   - **Baseline B:** Fixed Multimodal RAG
   - **Baseline C:** Existing Adaptive RAG literature baseline
   - **Proposed:** Adaptive Multimodal RAG with Calibrated Uncertainty & Selective Abstention
2. **Software Engineering Outcome:** Robust production platform featuring multi-tenant isolation, JWT authentication, asynchronous document ingestion, vector and relational persistence, OpenAPI documentation, and a modern Next.js frontend.

---

## 🛠 Tech Stack

- **Frontend:** Next.js 14+ (App Router), React, TypeScript, Tailwind CSS, Lucide icons
- **Backend:** Python 3.11+, FastAPI, Pydantic v2, SQLAlchemy 2.0 (async), Alembic
- **Document Processing:** Docling, PyMuPDF, OCR (PaddleOCR / Tesseract)
- **Vector & Retrieval:** Qdrant (dense + sparse BM25 hybrid), BGE Reranker
- **Data Persistence:** PostgreSQL 16, MinIO / Local S3 Blob Storage, Redis
- **Background Tasks:** Celery + Redis
- **Evaluation:** DocVQA, ChartQA, MMLongBench-Doc, Custom Unanswerable Benchmarks

---

## 🚀 Quickstart

### Prerequisites
- Python 3.11+
- Node.js 18+ (LTS)
- Docker & Docker Compose (optional for local mock mode)

### 1. Configure Environment
```bash
cp .env.example .env
```

### 2. Run Backend
```bash
cd backend
python -m venv .venv
# On Windows:
.venv\Scripts\activate
# On Linux/macOS:
# source .venv/bin/activate

pip install -r requirements.txt -r requirements-dev.txt
uvicorn app.main:app --reload --port 8000
```
Interactive API documentation: `http://localhost:8000/docs`

### 3. Run Frontend
```bash
cd frontend
npm install
npm run dev
```
Web Interface: `http://localhost:3000`

---

## 🔬 Research & Development Tracking

Detailed progress and design logs are maintained in [DEVELOPMENT_PROGRESS.md](docs/DEVELOPMENT_PROGRESS.md).
