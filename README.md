# 👨‍🍳 Yes Chef AI | Catering Estimation Engine

> **Live Demo:** [https://yes-chef-challenge.vercel.app](https://yes-chef-challenge.vercel.app)  
> **Status:** MVP Complete 🟢

**Yes Chef AI** is an intelligent agent designed to automate the complex process of catering estimation. It takes a high-level menu (via JSON or Natural Language), breaks dishes down into component ingredients, retrieves real-time pricing from a supplier catalog (Sysco), and handles edge cases where ingredients are unavailable by providing market estimates.

[Architecture Flow](https://www.mermaid.ai/d/6beea861-972e-49c1-9409-1c5c9e149751)

---

## 🚀 Key Features & Architecture

This project was built to solve the **"Stale Context"** and **"Resumability"** challenges inherent in long-running LLM processes.

### 1. 🧠 Retrieval Augmented Generation (RAG)

Instead of hallucinating prices, the Agent uses **Function Calling** to query a local `SyscoCatalog` search engine.

- **Algorithm:** Uses `RapidFuzz` with `partial_token_sort_ratio` to handle supplier naming inconsistencies (e.g., matching "Bacon" to "APPLEWOOD SMOKED BACON").
- **Fallback Logic:** Implements a 3-tier pricing strategy:
  1. ✅ **Sysco Catalog:** Exact match found.
  2. ⚠️ **Market Estimate:** Item missing (e.g., Wagyu Beef), AI estimates cost.
  3. ❌ **Not Available:** Impossible to price.

### 2. 🛡️ Fault Tolerance & Resumability

The system is designed to recover from crashes without losing progress.

- **State Persistence:** A lightweight JSON-based state manager (`job_state.json`) saves progress after every batch.
- **Crash Recovery:** If the backend is interrupted (e.g., server restart), it automatically detects the incomplete job and resumes from the exact item where it left off.

### 3. 📉 Context Compaction

To prevent the "Lost in the Middle" phenomenon and reduce token costs:

- The agent does **not** pass the full conversation history to the next batch.
- Instead, it summarizes "Learnings" (e.g., *"Sysco catalog lacks premium truffle oil"*) and passes only this compact summary forward.

### 4. 💬 Dual Mode Input

- **JSON Mode:** For structured, bulk processing.
- **Chat Mode:** Uses an NLP pipeline to parse unstructured requests (e.g., *"I need a wedding menu for 200 people..."*) into valid JSON before estimation.

---

## 🛠️ Technical Decisions (Trade-offs)

| Decision | Context & Rationale |
|----------|---------------------|
| **Singleton / Single-Tenant** | **Decision:** The backend uses a global `StateManager` (File-based).<br>**Why:** To demonstrate *Resumability* in the simplest way possible for the challenge. In a production SaaS, this would be replaced by Redis/PostgreSQL keyed by `session_id`. |
| **In-Memory Search** | **Decision:** Using `RapidFuzz` + `Pandas` instead of a Vector DB.<br>**Why:** For a catalog of ~600 items, in-memory fuzzy matching is orders of magnitude faster (µs vs ms) and reduces infrastructure complexity. |
| **Strict Typing** | **Decision:** Full Pydantic implementation.<br>**Why:** We inject JSON Schemas into the LLM prompt to guarantee that the output matches our backend models 100% of the time, preventing "malformed JSON" errors. |

---

## ⚡️ Quick Start (Makefile)

This project uses a `Makefile` to simplify setup and execution.

### Prerequisites

- Python 3.9+
- Node.js 18+
- OpenAI API Key

### 1. Initialization

```bash
make setup
```

### 2. Installation

```bash
make install
```

### 3. Configure Environment

Create a `.env` file in the `backend/` directory:

```env
OPENAI_API_KEY=sk-proj-your-key-here...
```

### 4. Run the App

**Terminal 1 (Backend):**

```bash
make run-backend
# Runs FastAPI on http://localhost:8000
```

**Terminal 2 (Frontend):**

```bash
make run-frontend
# Runs Next.js on http://localhost:3000
```

---

## 🧪 Testing & Diagnostics

```bash
make test
```

### What this tests:

- **Exact Matches:** Ensures "Butter" finds "BUTTER SALTED".
- **Fuzzy Logic:** Ensures "Applewood Bacon" finds "BACON, SMOKED, APPLEWOOD".
- **Sanity Checks:** Ensures no hallucinations for non-existent items (e.g., "Kryptonite").

---

## 📂 Project Structure

```
├── backend/
│   ├── src/
│   │   ├── agent.py
│   │   ├── catalog.py
│   │   ├── state.py
│   │   ├── models.py
│   │   └── main.py
│   ├── data/
│   │   └── sysco_catalog.csv
│   └── tests/
│
└── frontend/
    ├── src/app/page.tsx
    └── ...
```

---

## 🔮 Future Improvements (Roadmap)

If given more time, I would enhance the system in the following areas to move from MVP to Production-Grade:

1.  **Database Migration:** Replace the file-based `job_state.json` with **Redis** or **PostgreSQL**. This would allow multiple users (multi-tenancy) to generate quotes simultaneously without race conditions.
2.  **Vector Search:** While `RapidFuzz` is excellent for small catalogs (~600 items), scaling to 50k+ items would require a Vector Database (like **Pinecone** or **pgvector**) for semantic search capabilities (e.g., matching "spicy sausage" to "CHORIZO").
3.  **Unit Conversion Logic:** Improve the deterministic parsing of Sysco's `Unit of Measure` column (e.g., parsing "6/1 LB" vs "12/1 QT") to handle edge cases in case-to-unit price math more rigorously.
4.  **Feedback Loop:** Implement a UI feature for Estimators to correct the AI's choices. These corrections would be saved to fine-tune the prompt or update a "preferred ingredients" database.

---

## 👷‍♂️ Author

**Daniel Nava**  
Full Stack AI Engineer  

> "A resilient system is not one that never fails, but one that recovers gracefully."
