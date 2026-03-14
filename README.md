# AI Playground 🧠⚡

A personal lab for experimenting with modern AI frameworks, workflows, and architectures.  
This repository contains explorations in **LangGraph**, **LangChain**, **MCP servers**, **Retrieval-Augmented Generation (RAG)**, and **AWS Bedrock** applications, along with other cutting-edge GenAI experiments.

---

## 🔍 Objectives
- Build a **hands-on portfolio** of GenAI projects.
- Experiment with **agentic workflows**, **vector databases**, and **multi-modal pipelines**.
- Learn by iterating quickly and documenting outcomes.
- Share insights and reusable code for the community.

---

## 📂 Projects

### 🏗️ [AWS Bedrock Chat Agent with MCP & SharePoint Integration](./aws-bedrock-chat-agent-mcp/)
An enterprise-grade AI infrastructure built on **AWS Bedrock AgentCore Runtime**, exposing a production-ready **MCP server** that powers Amazon QuickSuite Chat Agents with SharePoint document access and AI image generation, secured via OAuth2, Bedrock Guardrails, and AWS IAM.  
→ [Documentation](./aws-bedrock-chat-agent-mcp/DOCUMENTATION.md) · [Project Summary](./aws-bedrock-chat-agent-mcp/PROJECT_SUMMARY.md)

---

### 🤖 [Self-Correcting Multi-Agent System](./self-correcting-multi-agent-system/)
A **LangGraph-based multi-agent pipeline** where a Solver, Critic, and Judge agent collaborate in iterative refinement loops, significantly reducing hallucinations and improving answer accuracy compared to single-agent approaches.  
→ [README](./self-correcting-multi-agent-system/README.md)

---

### 🔌 [MCP Natural Language to Data Endpoints](./mcp-natural-language-to-data-endpoints/)
An **MCP server** that translates plain-English questions into optimized database queries across 20+ database types (SQL, NoSQL, Graph, GraphQL), powered by GPT-4 or Claude, with automatic schema introspection and caching.  
→ [README](./mcp-natural-language-to-data-endpoints/README.md) · [Project Summary](./mcp-natural-language-to-data-endpoints/PROJECT_SUMMARY.md)

---

### 📊 [Natural Language to GraphQL — Enterprise Solution](./nl-to-graphql-enterprise-solution/)
A **LangChain-based agentic system** that converts natural language queries into GraphQL, backed by a realistic relational database (watches retail domain), with context-aware chart generation and interactive Q&A.  
→ [README](./nl-to-graphql-enterprise-solution/README.md) · [Project Summary](./nl-to-graphql-enterprise-solution/PROJECT_SUMMARY.md)

---

### 🔗 [MCP Using LangChain](./mcp-using-langchain/)
A minimal working example of integrating **LangChain MCP adapters** with a multi-server MCP client, connecting a math tool server and a weather server to a ReAct agent via the MCP protocol.  
→ [Source](./mcp-using-langchain/client.py)

---

### 🧪 [LangGraph Experiments](./langgraph-experiments/)
A series of progressive **LangGraph** experiments covering foundational concepts: building a basic stateful chatbot, adding human-in-the-loop interrupts, and debugging/monitoring agent execution with LangSmith.

| Experiment | Description |
|---|---|
| [1 — Basic Chatbot](./langgraph-experiments/1-BasicChatbot/) | Stateful chatbot with message history using LangGraph |
| [2 — Human in the Loop](./langgraph-experiments/2-HumanInTheLoop/) | Interrupt-and-resume patterns for human approval steps |
| [3 — Debugging & Monitoring](./langgraph-experiments/3-DebuggingAndMonitoring/) | LangSmith tracing and agent state inspection |

---

### 📚 [RAG & GraphRAG Exploration](./rag-graphrag-exploration/)
A notebook comparing **standard RAG** (embed-and-retrieve over row summaries) with a **GraphRAG-style approach** that builds a knowledge graph over a relational schema for better multi-hop question answering.  
→ [Notebook](./rag-graphrag-exploration/rag-graphrag-on-relational-tables.ipynb)

---

### 🖼️ [MCP Image Generation with Bedrock Guardrails (Pre-exploration)](./aws-bedrock-chat-agent-mcp/pre-exploration-image-gen-mcp/)
The initial prototype of an **MCP server on AWS AgentCore Runtime** that generates images via AWS Bedrock (Stability AI / Titan), enforces content safety through Bedrock Guardrails, and stores results in S3 — the foundation that evolved into the full AgentCore project.  
→ [README](./aws-bedrock-chat-agent-mcp/pre-exploration-image-gen-mcp/README.md)

---

## 🛠️ Tech Stack

| Category | Technologies |
|---|---|
| AI / LLM | AWS Bedrock, OpenAI GPT-4, Anthropic Claude |
| Agentic Frameworks | LangGraph, LangChain, FastMCP |
| AWS Services | AgentCore Runtime/Gateway/Identity, Bedrock Guardrails, Q Business, QuickSuite, S3, DynamoDB, CloudWatch, Secrets Manager |
| Protocols | Model Context Protocol (MCP), Microsoft Graph API, OAuth2 |
| Infrastructure | Terraform, Docker, GitHub Actions, AWS ECR |
| Databases | PostgreSQL, MongoDB, Neo4j, DynamoDB, SQLite, GraphQL |

---

## 📁 Repository Structure

```text
ai-playground/
│
├── aws-bedrock-chat-agent-mcp/              # Enterprise AgentCore MCP server + SharePoint integration
├── self-correcting-multi-agent-system/      # Multi-agent solver/critic/judge pipeline
├── mcp-natural-language-to-data-endpoints/  # NL to multi-database MCP server
├── nl-to-graphql-enterprise-solution/       # NL to GraphQL agentic system
├── mcp-using-langchain/                     # LangChain MCP adapter examples
├── langgraph-experiments/                   # Progressive LangGraph learning experiments
├── rag-graphrag-exploration/                # RAG vs GraphRAG on relational data
└── docs/                                    # Notes and learnings
```
