# ALO Yoga RAG Demo — Chat UI

A Next.js chat interface for the ALO Yoga RAG system, built with [assistant-ui](https://www.assistant-ui.com/).

## Prerequisites

- Node.js 18+
- The Python backend server running at `http://localhost:8000`

## Setup

1. Install dependencies:
   ```bash
   cd alo-rag/demo
   npm install
   ```

2. Start the Python backend (from the `alo-rag/` directory):
   ```bash
   cd alo-rag
   python -m uvicorn server:app --host 0.0.0.0 --port 8000
   ```

3. Start the Next.js dev server:
   ```bash
   cd alo-rag/demo
   npm run dev
   ```

4. Open [http://localhost:3000](http://localhost:3000)

## Features

- Real-time streaming chat with the ALO RAG pipeline
- Customer profile selector for personalized queries
- Suggested prompts for common ALO Yoga questions
- Markdown rendering for formatted responses
