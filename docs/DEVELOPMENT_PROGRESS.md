# AdaptiveDocAI: Development Progress & Session Log

This document tracks implementation status, architectural milestones, and experimental baseline results.

---

## 📅 Milestone Tracker

| Phase | Milestone Description | Target Deliverable | Status |
| :--- | :--- | :--- | :--- |
| **Phase 0** | System Architecture & Design | Technical specification approved | ✅ **Completed** |
| **Phase 1** | Foundation & Core Application | Auth, DB models, storage, upload pipeline, Next.js frontend | 🔄 **In Progress** |
| **Phase 2** | Baseline A: Standard Text RAG | PyPDF chunking, dense vector retrieval, frozen evaluation | ⏳ Pending |
| **Phase 3** | Multimodal Document Ingestion | Docling parser, PyMuPDF crops, OCR, VLM descriptions, Baseline B | ⏳ Pending |
| **Phase 4** | Adaptive Retrieval Controller | Dynamic routing, multi-hop search, Baseline C | ⏳ Pending |
| **Phase 5** | Uncertainty Estimation Engine | Multi-factor (R, E, C, M) formulation, Platt calibration, abstention | ⏳ Pending |
| **Phase 6** | Grounded Generation & Citations | Bounding box mapping, verification, visual citation preview | ⏳ Pending |
| **Phase 7** | Research Experiments & Paper | DocVQA, ChartQA, MMLongBench evaluation & ablation analysis | ⏳ Pending |
| **Phase 8** | Production Hardening & CI/CD | OpenTelemetry, caching, Docker deployment, test coverage | ⏳ Pending |

---

## 📝 Phase 1 Task Breakdown

- [x] Architecture Specification approved by user
- [x] Root project layout (.gitignore, .env.example, Makefile, README.md)
- [x] Docker Compose multi-service definition
- [ ] Backend foundation:
  - [ ] Pydantic v2 Settings configuration (`app/core/config.py`)
  - [ ] Async SQLAlchemy engine & session factory (`app/core/database.py`)
  - [ ] Security utilities (bcrypt password hashing, JWT creation & validation) (`app/core/security.py`)
  - [ ] Database models: Organization, User, Document, DocumentPage, DocumentAsset, DocumentChunk, IngestionJob, Conversation, Message, RetrievalTrace
  - [ ] Pydantic schemas (Auth, Document, User, Chat)
  - [ ] Storage service (Local file system + S3/MinIO abstraction)
  - [ ] Auth endpoints (`/register`, `/login`, `/me`)
  - [ ] Document endpoints (`/upload`, `/`, `/{id}`, `/{id}/status`, `DELETE /{id}`)
  - [ ] Comprehensive unit and integration test suite with pytest
- [ ] Next.js Frontend foundation:
  - [ ] Next.js 14 project setup with TypeScript and Tailwind CSS
  - [ ] Auth state management (JWT storage, login, register views)
  - [ ] Document upload dropzone and document management table
  - [ ] Status indicators (Pending, Processing, Indexed, Failed)

