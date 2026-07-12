# RAG PRS (Product Requirement System) - User & Developer Guide

Welcome to the **RAG PRS** system! This document provides quick instructions to set up, run, and test the system locally.

The system is separated into two decoupled components:
1. **Backend**: Python-based FastAPI server (handles AI analysis, RAG, and document ingestion).
2. **Frontend**: React-based UI powered by Vite (handles the user interface for submitting PDFs and viewing results).

---

## 1. Prerequisites

- **Python 3.10+**
- **Node.js 18+** (for running the frontend)
- **API Keys**: You will need an API key for the LLM inference. We recommend Cerebras for maximum speed.

---

## 2. Backend Setup & Running

The backend is built using FastAPI and runs on port `8000`.

### **Installation**
1. Navigate to the backend directory:
   ```bash
   cd backend
   ```
2. (Optional but recommended) Create and activate a virtual environment:
   ```bash
   python -m venv venv
   # On Windows
   venv\Scripts\activate
   # On Mac/Linux
   source venv/bin/activate
   ```
3. Install the Python dependencies:
   ```bash
   pip install -r requirements.txt
   ```

### **Configuration**
Create a `.env` file inside the `backend/` directory and add your API keys:
```env
CEREBRAS_API_KEY=your_cerebras_api_key_here
GROQ_API_KEY=your_groq_api_key_here  # (Optional fallback)
```

### **Starting the Server**
Run the server using Uvicorn:
```bash
python -m uvicorn app.main:app --port 8000
```
> **Tip:** For local development, add the `--reload` flag to automatically restart the server when code changes:
> `python -m uvicorn app.main:app --port 8000 --reload`

The backend API will be available at [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs) (Swagger UI).

---

## 3. Frontend Setup & Running

The frontend is a React application built with Vite, defaulting to port `5173`.

### **Installation**
1. Open a **new terminal window** and navigate to the frontend directory:
   ```bash
   cd frontend-react
   ```
2. Install the Node dependencies:
   ```bash
   npm install
   ```

### **Starting the Server**
Run the Vite development server:
```bash
npm run dev
```

The frontend will be available at [http://localhost:5173](http://localhost:5173).

---

## 4. How to Use the System

1. **Ensure both servers are running** (Backend on `8000`, Frontend on `5173`).
2. Open your browser and navigate to `http://localhost:5173`.
3. In the UI, use the file uploader to select a Product Requirement PDF (e.g. `raw_lan_switch_pdf.txt` or a `.pdf` file).
4. Select the standard you wish to test against (e.g., `IEC 62443`).
5. Click the "Assess" button.
6. The frontend will communicate with the backend API, extract text, route it through the RAG pipeline, hit the LLM (Cerebras), and display the Gap Analysis results on the screen!

---

## 5. Troubleshooting / Common Issues

- **DNS / Corporate VPN Blocks (Cerebras)**: If you are behind a corporate proxy (like Cisco Umbrella) that causes `getaddrinfo failed` or intercepts connections, the backend (`app/analysis/tier3_llm.py`) has a built-in DNS bypass patch for `api.cerebras.ai`. 
- **CORS Errors**: The backend is configured to allow origins `http://localhost:5173` and `http://127.0.0.1:5173`. Ensure your frontend is running on one of those ports.
- **Missing API Keys**: If the LLM throws a `401 Unauthorized` error, verify that your `.env` file is properly placed in the `backend/` folder and that the key is valid.

