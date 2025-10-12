# AI-Driven Location App for the Turkish Diaspora

[cite_start]This project is a lightweight, legal, and cost-efficient application that automatically discovers, validates, and displays Turkish-oriented businesses and community hotspots in the Netherlands[cite: 3].

## Project Structure

This is a monorepo containing the following parts:

* [cite_start]`/Backend`: The Python FastAPI application[cite: 135].
* [cite_start]`/Frontend`: The React (Vite/Next.js) application[cite: 144].
* [cite_start]`/Infra`: Infrastructure as Code, such as Supabase migrations[cite: 152, 153].
* [cite_start]`/Docs`: Project documentation and planning files[cite: 151].

## Getting Started

### Prerequisites

* Python 3.10+
* Node.js 18+
* Docker (optional)

### Backend Setup

1.  **Navigate to the Backend Directory**
    ```bash
    cd Backend
    ```

2.  **Create and Activate a Virtual Environment**
    ```bash
    python3 -m venv .venv
    source .venv/bin/activate
    ```
    *(On Windows, use `.venv\Scripts\activate`)*

3.  **Install Dependencies**
    ```bash
    pip install -r requirements.txt
    ```

4.  **Create Configuration File**
    Create a file named `.env` in the `/Backend` directory. For now, you can add the following line to it:
    ```env
    APP_VERSION="0.1.0-local"
    ```

5.  **Run the Server**
    ```bash
    uvicorn app.main:app --reload
    ```
    The API will now be running at `http://127.0.0.1:8000`. You can check its status by visiting the health endpoint at `http://127.0.0.1:8000/health`.

### Frontend Setup

*(The frontend application has not been initialized yet. These are placeholder instructions.)*

```bash
cd Frontend
npm install
npm run dev