# AI-Gedreven Locatie-App voor de Turkse Diaspora

[cite_start]This project is a lightweight, legal, and cost-efficient application that automatically discovers, validates, and displays Turkish-oriented businesses and community hotspots in the Netherlands[cite: 3].

## Project Structure

This is a monorepo containing the following parts:

-   [cite_start]`/Backend`: The Python FastAPI application[cite: 135].
-   [cite_start]`/Frontend`: The React (Vite/Next.js) application[cite: 144].
-   [cite_start]`/Infra`: Infrastructure as Code, such as Supabase migrations[cite: 152, 153].
-   [cite_start]`/Docs`: Project documentation and planning files[cite: 151].

## Getting Started

### Prerequisites

-   Python 3.10+
-   Node.js 18+
-   Docker (optional)

### Backend Setup

```bash
cd Backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
# (More instructions to come)