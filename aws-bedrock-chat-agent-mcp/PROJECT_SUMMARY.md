# Project Summary: Enterprise AI Foundation, MCP Server with SharePoint & Bedrock Integration

## Business Objective

The goal of this project is to bring AI-powered capabilities directly into the enterprise's existing chat interface (Amazon QuickSuite) without requiring users to leave their workflow or learn new tools.

Specifically, the project solves two concrete enterprise problems:

1. **Knowledge Access**: Enterprise knowledge is locked inside SharePoint: documents, policies, procedures, and lists spread across multiple sites and libraries. Employees waste time navigating SharePoint manually to find information. This project exposes that knowledge through a natural language chat interface, letting users ask questions and retrieve documents conversationally.

2. **Visual Content Generation**: Teams that need quick visual assets (presentations, mockups, concept visuals) previously had to rely on external tools or design teams. This project enables on-demand AI image generation directly from chat, with enterprise-grade content guardrails.

The underlying platform is built to be extensible. The same infrastructure can host additional AI tools in the future, making it a reusable foundation for enterprise AI capabilities.

---

## Enterprise Value

- **Productivity**: Employees can search SharePoint, retrieve document content, and generate images without leaving the chat interface. What previously took minutes of navigation now takes seconds.
- **Governance & Compliance**: Every request is logged to DynamoDB with full audit trails. Content is filtered through AWS Bedrock Guardrails before generation. PII is automatically anonymized or blocked.
- **Security**: No credentials are stored in the application. OAuth2 tokens for SharePoint are managed entirely by AWS Bedrock AgentCore Identity, which handles the full OAuth2 flow with Azure AD. IAM authorization protects the AgentCore Gateway.
- **Cost Efficiency**: The entire backend is serverless. AWS Bedrock AgentCore Runtime scales to zero when idle and scales automatically under load. There are no always-on servers to manage.
- **Extensibility**: The MCP (Model Context Protocol) server architecture makes it straightforward to add new tools. Any new enterprise integration becomes another registered MCP tool without changing the underlying infrastructure.

---

## Technologies Learned & Applied

### AWS Bedrock
AWS Bedrock is a fully managed service that provides access to foundation models from leading AI providers (Anthropic, Stability AI, Amazon Titan, etc.) via a single API. In this project, Bedrock is used to invoke image generation models (Stability AI SDXL and Amazon Titan Image Generator) without managing any model infrastructure.

Key learning: how to invoke Bedrock model APIs, handle base64-encoded image responses, and integrate model calls into a production Python service.

### AWS Bedrock AgentCore Runtime
AgentCore Runtime is a serverless container execution environment purpose-built for AI agent workloads. It runs the MCP server as a containerized Python application, handling auto-scaling, lifecycle management, and integration with the AgentCore Gateway.

Key learning: how to package a FastMCP server as a Docker container, push it to ECR, and configure AgentCore Runtime to serve it, including the stateless HTTP mode required for MCP protocol compatibility.

### AWS Bedrock AgentCore Gateway
The Gateway is the entry point for MCP protocol traffic. It handles AWS IAM authorization, routes requests to the correct Runtime, and exposes the MCP endpoint to Amazon QuickSuite Chat Agents.

Key learning: how to configure an AgentCore Gateway with custom JWT authorization (for QuickSuite integration) and wire it to a Runtime.

### AWS Bedrock AgentCore Identity (OAuth2 Credential Provider)
This is one of the most novel pieces of the project. AgentCore Identity manages OAuth2 credential flows on behalf of the application. Instead of storing Azure AD client secrets in the application, the MCP server delegates the entire OAuth2 flow to AWS, which obtains and refreshes tokens and injects them into tool function calls via a decorator pattern.

Key learning: how to register a Microsoft OAuth2 credential provider in AgentCore, configure the callback URL in Azure AD, and use the `@get_access_token_decorator` pattern to inject tokens into SharePoint tool functions without any credential storage in application code.

### AWS Bedrock Guardrails
Guardrails provide content filtering and PII handling for AI model interactions. In this project, every image generation prompt is validated against a guardrail before being sent to Bedrock. The guardrail blocks violent, sexual, hateful, and harmful content, and anonymizes or blocks PII in prompts.

Key learning: how to configure guardrail policies (content filters + PII handling), call the `apply_guardrail` API, and interpret the response to decide whether to proceed or block a request.

### Model Context Protocol (MCP)
MCP is an open protocol that standardizes how AI agents discover and invoke tools. The FastMCP Python library is used to build the MCP server, register tools, and handle the JSON-RPC protocol. Amazon QuickSuite Chat Agents natively support MCP, which is what connects the chat interface to the backend tools.

Key learning: how to structure an MCP server with FastMCP, register async tool functions with typed parameters, manage shared application context (clients, config) via lifespan, and run the server in stateless HTTP mode for AgentCore compatibility.

### Microsoft Graph API & SharePoint Online
The Microsoft Graph API is the unified REST API for Microsoft 365 services. In this project it is used to interact with SharePoint Online: retrieving site metadata, listing document libraries, searching content, listing folder contents, and downloading document files for text extraction.

Key learning: how to construct Graph API endpoints for SharePoint sites and drives, handle pagination, parse SharePoint site URLs into domain/path components, and extract text from Office documents (PDF, Word, Excel, PowerPoint) using Python libraries.

### Amazon QuickSuite Chat Agents
Amazon QuickSuite is AWS's business intelligence and analytics platform. Its Chat Agents feature allows users to interact with AI agents via natural language. In this project, a QuickSuite Chat Agent is configured to connect to the AgentCore Gateway, making all MCP tools available to users through the QuickSuite chat interface.

Key learning: how to configure a QuickSuite Chat Agent to use an AgentCore-hosted MCP server, and how the agent interprets user intent to select and invoke the correct MCP tool.

### Amazon Q Business (q-business module)
The `q-business` module provisions an Amazon Q Business application with SharePoint as a data source. Q Business indexes SharePoint content and makes it searchable via its own AI-powered interface. This is a complementary approach to the MCP server: the MCP server provides real-time, on-demand SharePoint access, while Q Business provides indexed, semantic search across large SharePoint corpora.

Key learning: how to configure Q Business data sources for SharePoint with OAuth2 certificate authentication, set up identity crawling for document-level access control, and manage sync schedules.

### Infrastructure as Code (Terraform)
The entire AWS infrastructure (AgentCore Runtime, Gateway, ECR, S3, DynamoDB, CloudWatch, Secrets Manager, VPC, IAM) is provisioned with Terraform. The project uses both public Terraform modules and custom resource definitions.

---

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         USER LAYER                                          │
│                                                                             │
│   ┌─────────────────────────────────────────────────────────────────────┐   │
│   │          Amazon QuickSuite Chat Interface (Browser)                 │   │
│   │   User types natural language: "Show me files in Marketing folder"  │   │
│   └─────────────────────────────────────────────────────────────────────┘   │
└──────────────────────────────────┬──────────────────────────────────────────┘
                                   │ HTTPS
                                   ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                      AWS QUICKSUITE LAYER                                   │
│                                                                             │
│   ┌─────────────────────────────────────────────────────────────────────┐   │
│   │              Amazon QuickSuite Chat Agent                           │   │
│   │   - Interprets user intent via LLM                                  │   │
│   │   - Selects appropriate MCP tool                                    │   │
│   │   - Formats tool parameters from natural language                   │   │
│   └─────────────────────────────────────────────────────────────────────┘   │
└──────────────────────────────────┬──────────────────────────────────────────┘
                                   │ MCP Protocol (JSON-RPC over HTTPS)
                                   ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                    AWS BEDROCK AGENTCORE LAYER                              │
│                                                                             │
│   ┌─────────────────────────────────────────────────────────────────────┐   │
│   │              AgentCore Gateway                                      │   │
│   │   - AWS IAM + Custom JWT Authorization                              │   │
│   │   - MCP protocol endpoint                                           │   │
│   │   - Routes to AgentCore Runtime                                     │   │
│   └──────────────────────────────┬──────────────────────────────────────┘   │
│                                  │                                          │
│   ┌──────────────────────────────▼──────────────────────────────────────┐   │
│   │              AgentCore Runtime (Serverless Container)               │   │
│   │                                                                     │   │
│   │   ┌─────────────────────────────────────────────────────────────┐   │   │
│   │   │                FastMCP Server (Python)                      │   │   │
│   │   │                                                             │   │   │
│   │   │   ┌─────────────────┐    ┌──────────────────────────────┐   │   │   │
│   │   │   │  Image Tools    │    │     SharePoint Tools         │   │   │   │
│   │   │   │                 │    │                              │   │   │   │
│   │   │   │ generate_image  │    │ get_sharepoint_site_info     │   │   │   │
│   │   │   └────────┬────────┘    │ list_document_libraries      │   │   │   │
│   │   │            │             │ search_sharepoint            │   │   │   │
│   │   │            │             │ get_sharepoint_list_items    │   │   │   │
│   │   │            │             │ get_sharepoint_document_     │   │   │   │
│   │   │            │             │   content                    │   │   │   │
│   │   │            │             │ list_sharepoint_folder_      │   │   │   │
│   │   │            │             │   contents                   │   │   │   │
│   │   │            │             └──────────────┬───────────────┘   │   │   │
│   │   └────────────┼────────────────────────────┼───────────────────┘   │   │
│   └────────────────┼────────────────────────────┼───────────────────────┘   │
│                    │                            │                           │
│   ┌────────────────▼──────────┐   ┌─────────────▼───────────────────────┐   │
│   │  AgentCore Identity       │   │  AgentCore Identity                 │   │
│   │  (not used for images)    │   │  OAuth2 Credential Provider         │   │
│   │                           │   │  - Manages Azure AD OAuth2 flow     │   │
│   │                           │   │  - Injects access tokens into tools │   │
│   └───────────────────────────┘   └─────────────────────────────────────┘   │
└──────────┬─────────────────────────────────────────┬────────────────────────┘
           │                                         │
           ▼                                         ▼
┌──────────────────────────┐           ┌─────────────────────────────────────┐
│    AWS SERVICES          │           │       MICROSOFT SERVICES            │
│                          │           │                                     │
│  ┌────────────────────┐  │           │  ┌─────────────────────────────┐    │
│  │  Amazon Bedrock    │  │           │  │  Azure Active Directory     │    │
│  │  (Image Gen Models)│  │           │  │  (OAuth2 Token Issuer)      │    │
│  │  - Stability AI    │  │           │  └──────────────┬──────────────┘    │
│  │  - Amazon Titan    │  │           │                 │                   │
│  └────────────────────┘  │           │  ┌──────────────▼──────────────┐    │
│                          │           │  │  Microsoft Graph API        │    │
│  ┌────────────────────┐  │           │  │  (REST API for M365)        │    │
│  │  Bedrock Guardrails│  │           │  └──────────────┬──────────────┘    │
│  │  - Content filters │  │           │                 │                   │
│  │  - PII handling    │  │           │  ┌──────────────▼──────────────┐    │
│  └────────────────────┘  │           │  │  SharePoint Online          │    │
│                          │           │  │  - Document Libraries       │    │
│  ┌────────────────────┐  │           │  │  - Lists & Items            │    │
│  │  Amazon S3         │  │           │  │  - Files & Folders          │    │
│  │  (Image Storage)   │  │           │  └─────────────────────────────┘    │
│  │  - Presigned URLs  │  │           └─────────────────────────────────────┘
│  └────────────────────┘  │
│                          │
│  ┌────────────────────┐  │
│  │  DynamoDB          │  │
│  │  (Audit Log)       │  │
│  └────────────────────┘  │
│                          │
│  ┌────────────────────┐  │
│  │  CloudWatch        │  │
│  │  (Logs & Metrics)  │  │
│  └────────────────────┘  │
│                          │
│  ┌────────────────────┐  │
│  │  Secrets Manager   │  │
│  │  (Config & Creds)  │  │
│  └────────────────────┘  │
│                          │
│  ┌────────────────────┐  │
│  │  Amazon ECR        │  │
│  │  (Container Image) │  │
│  └────────────────────┘  │
└──────────────────────────┘
```

---

## Workflow Diagram: SharePoint Query (Primary Flow)

This is the primary enterprise use case: a user asking a question that requires retrieving information from SharePoint.

```
USER                    QUICKSUITE              AGENTCORE               MCP SERVER              MICROSOFT
 │                          │                       │                       │                       │
 │  "Show me files in       │                       │                       │                       │
 │   the Marketing folder"  │                       │                       │                       │
 │────────────────────────▶ |                      │                       │                       │
 │                          │                       │                       │                       │
 │                          │  LLM interprets       │                       │                       │
 │                          │  intent → selects     │                       │                       │
 │                          │  list_sharepoint_     │                       │                       │
 │                          │  folder_contents      │                       │                       │
 │                          │                       │                       │                       │
 │                          │  MCP JSON-RPC call    │                       │                       │
 │                          │  (with JWT token)     │                       │                       │
 │                          │──────────────────────▶│                       │                       │
 │                          │                       │                       │                       │
 │                          │                       │  Validate JWT         │                       │
 │                          │                       │  (IAM AuthZ)          │                       │
 │                          │                       │                       │                       │
 │                          │                       │  Route to Runtime     │                       │
 │                          │                       │  (start container     │                       │
 │                          │                       │   if cold start)      │                       │
 │                          │                       │──────────────────────▶│                       │
 │                          │                       │                       │                       │
 │                          │                       │                       │  Load config from     │
 │                          │                       │                       │  Secrets Manager      │
 │                          │                       │                       │  (on startup only)    │
 │                          │                       │                       │                       │
 │                          │                       │                       │  Tool invoked:        │
 │                          │                       │                       │  list_sharepoint_     │
 │                          │                       │                       │  folder_contents()    │
 │                          │                       │                       │                       │
 │                          │                       │  Request OAuth2 token │                       │
 │                          │                       │◀──────────────────────│                       │
 │                          │                       │                       │                       │
 │                          │                       │  AgentCore Identity   │                       │
 │                          │                       │  initiates OAuth2     │                       │
 │                          │                       │  flow with Azure AD   │                       │
 │                          │                       │──────────────────────────────────────────────▶│
 │                          │                       │                       │                       │
 │                          │                       │                       │  Azure AD issues      │
 │                          │                       │                       │  access token         │
 │                          │                       │◀──────────────────────────────────────────────│
 │                          │                       │                       │                       │
 │                          │                       │  Token injected into  │                       │
 │                          │                       │  tool via decorator   │                       │
 │                          │                       │──────────────────────▶│                       │
 │                          │                       │                       │                       │
 │                          │                       │                       │  Call Graph API:      │
 │                          │                       │                       │  GET /sites/{id}/     │
 │                          │                       │                       │  drives/{id}/root:/   │
 │                          │                       │                       │  Marketing:/children  │
 │                          │                       │                       │──────────────────────▶│
 │                          │                       │                       │                       │
 │                          │                       │                       │  SharePoint returns   │
 │                          │                       │                       │  folder contents      │
 │                          │                       │                       │◀──────────────────────│
 │                          │                       │                       │                       │
 │                          │                       │                       │  Format response      │
 │                          │                       │                       │  Log to DynamoDB      │
 │                          │                       │                       │  Emit CloudWatch      │
 │                          │                       │                       │  metrics              │
 │                          │                       │                       │                       │
 │                          │                       │  MCP tool response    │                       │
 │                          │◀──────────────────────│◀──────────────────────│                       │
 │                          │                       │                       │                       │
 │                          │  LLM formats          │                       │                       │
 │                          │  response for user    │                       │                       │
 │                          │                       │                       │                       │
 │  "Here are the files      │                       │                       │                       │
 │   in Marketing:           │                       │                       │                       │
 │   1. Q1 Report.docx       │                       │                       │                       │
 │   2. Campaign Brief.pptx  │                       │                       │                       │
 │   ..."                    │                       │                       │                       │
 │◀──────────────────────────│                       │                       │                       │
```

---

## Workflow Diagram: Image Generation Flow

```
USER                    QUICKSUITE              AGENTCORE               MCP SERVER              AWS BEDROCK
 │                          │                       │                       │                       │
 │  "Generate an image of   │                       │                       │                       │
 │   a mountain at sunset"  │                       │                       │                       │
 │──────────────────────────▶                       │                       │                       │
 │                          │                       │                       │                       │
 │                          │  LLM selects          │                       │                       │
 │                          │  generate_image tool  │                       │                       │
 │                          │──────────────────────▶│                       │                       │
 │                          │                       │──────────────────────▶│                       │
 │                          │                       │                       │                       │
 │                          │                       │                       │  Validate prompt      │
 │                          │                       │                       │  via Guardrails API   │
 │                          │                       │                       │──────────────────────▶│
 │                          │                       │                       │                       │
 │                          │                       │                       │  Guardrail: APPROVED  │
 │                          │                       │                       │◀──────────────────────│
 │                          │                       │                       │                       │
 │                          │                       │                       │  Invoke Bedrock       │
 │                          │                       │                       │  (Stability AI SDXL)  │
 │                          │                       │                       │──────────────────────▶│
 │                          │                       │                       │                       │
 │                          │                       │                       │  Returns base64 PNG   │
 │                          │                       │                       │◀──────────────────────│
 │                          │                       │                       │                       │
 │                          │                       │                       │  Upload PNG to S3     │
 │                          │                       │                       │  Generate presigned   │
 │                          │                       │                       │  URL (1hr expiry)     │
 │                          │                       │                       │  Log to DynamoDB      │
 │                          │                       │                       │  Emit CloudWatch      │
 │                          │                       │                       │  metrics              │
 │                          │                       │                       │                       │
 │                          │◀──────────────────────│◀──────────────────────│                       │
 │                          │                       │                       │                       │
 │  [Image displayed]        │                       │                       │                       │
 │  "Image generated in      │                       │                       │                       │
 │   6.2s using Stability AI"│                       │                       │                       │
 │◀──────────────────────────│                       │                       │                       │
```

---

## Key Design Decisions

**Why MCP over a custom REST API?**
MCP is natively supported by Amazon QuickSuite Chat Agents. Using MCP means zero custom integration code on the QuickSuite side; the agent automatically discovers available tools and knows how to invoke them.

**Why AgentCore Runtime over Lambda or ECS?**
AgentCore Runtime is purpose-built for MCP server workloads. It handles the stateless HTTP mode required by MCP, integrates natively with AgentCore Gateway and Identity, and provides serverless scaling without the cold-start constraints of Lambda for long-running model calls.

**Why delegate OAuth2 to AgentCore Identity instead of managing tokens in the app?**
Storing Azure AD client secrets in application code or environment variables is a security risk. AgentCore Identity manages the full OAuth2 lifecycle (token acquisition, refresh, and session binding) without the application ever seeing or storing credentials. This is a zero-trust approach to third-party authentication.

**Why read-only SharePoint access?**
The initial scope is information retrieval. Read-only permissions (Sites.Read.All, Files.Read.All) minimize the blast radius of any security issue and satisfy enterprise governance requirements for AI-driven data access.
