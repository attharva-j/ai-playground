# AI Foundation - Complete Documentation

## Table of Contents

1. [Executive Summary](#executive-summary)
2. [Objective](#objective)
3. [Quick Start Guide](#quick-start-guide)
4. [Repository Structure](#repository-structure)
5. [Technical Architecture](#technical-architecture)
6. [Module Documentation](#module-documentation)
7. [Setup and Configuration](#setup-and-configuration)
8. [Deployment Guide](#deployment-guide)
9. [Using Amazon QuickSuite Chat Agents](#using-amazon-quicksuite-chat-agents)
10. [Features and Capabilities](#features-and-capabilities)
11. [Current Limitations](#current-limitations)
12. [Monitoring and Debugging](#monitoring-and-debugging)
13. [Maintenance and Updates](#maintenance-and-updates)
14. [Troubleshooting](#troubleshooting)
15. [Security and Compliance](#security-and-compliance)
16. [API Reference](#api-reference)

---

## Executive Summary

The AI Foundation is an enterprise-grade AI infrastructure built on AWS Bedrock AgentCore Runtime, providing a production-ready Model Context Protocol (MCP) Server that powers Amazon QuickSuite Chat Agents with advanced AI capabilities.

### Key Highlights

- **Multi-Service Integration**: Seamlessly integrates AWS Bedrock AI services with Microsoft SharePoint
- **Enterprise Security**: Built-in content filtering, PII handling, and OAuth2 authentication via AWS Credential Provider
- **Production-Ready**: Comprehensive logging, monitoring, audit trails, and error handling
- **Extensible Architecture**: Modular design supports easy addition of new tools and integrations
- **Zero-Trust Security**: AWS IAM authorization, encrypted secrets, and secure token management

### Current Capabilities

1. **AI Image Generation** - Generate images using Amazon Bedrock (Stability AI, Amazon Titan)
2. **SharePoint Integration** - Read-only access to SharePoint sites, documents, and lists
3. **Content Moderation** - Automatic filtering of inappropriate content and PII
4. **Audit Logging** - Complete audit trail in DynamoDB
5. **CloudWatch Monitoring** - Real-time logs and metrics

---

## Objective

### Primary Goals

1. **Enable AI-Powered Chat Agents**: Provide Amazon QuickSuite users with intelligent chat agents capable of generating images and accessing SharePoint content
2. **Enterprise Integration**: Bridge AWS AI services with Microsoft 365 ecosystem securely
3. **Governance and Compliance**: Ensure all AI interactions are logged, monitored, and compliant with content policies
4. **Scalability**: Support multiple concurrent users with serverless, auto-scaling infrastructure
5. **Extensibility**: Create a foundation for adding more AI tools and enterprise integrations

### Business Value

- **Productivity**: Users can generate visual content and access documents directly from chat
- **Security**: All operations are authenticated, authorized, and audited
- **Cost Efficiency**: Serverless architecture with pay-per-use pricing
- **Compliance**: Built-in guardrails prevent inappropriate content generation
- **User Experience**: Natural language interface for complex operations

---

## Quick Start Guide

### Prerequisites

- AWS Account with appropriate permissions
- Access to Amazon QuickSuite
- (Optional) Microsoft 365 tenant with SharePoint Online
- Terraform >= 1.5.0
- Python 3.12+
- Docker (for local testing)

### 5-Minute Setup

```bash
# 1. Clone repository
git clone <repository-url>
cd ai-foundation

# 2. Configure AWS credentials
aws configure

# 3. Deploy infrastructure
cd agentcore
terraform init
terraform apply -var-file=terraform.tfvars

# 4. Build and push container
cd src
docker build -t agentcore-mcp-server:latest .
aws ecr get-login-password --region us-east-1 | docker login --username AWS --password-stdin <account-id>.dkr.ecr.us-east-1.amazonaws.com
docker tag agentcore-mcp-server:latest <account-id>.dkr.ecr.us-east-1.amazonaws.com/ai-foundation-dev-agentcore:latest
docker push <account-id>.dkr.ecr.us-east-1.amazonaws.com/ai-foundation-dev-agentcore:latest

# 5. Test the deployment
python test_client.py
```


---

## Repository Structure

```
ai-foundation/
├── README.md                          # Project overview
├── DOCUMENTATION.md                   # This file
├── agentcore/                         # Main infrastructure and application
│   ├── README.md                      # AgentCore-specific documentation
│   ├── CLOUDWATCH_LOGGING_GUIDE.md   # CloudWatch setup guide
│   ├── TESTING_GUIDE.md               # Testing instructions
│   ├── LOGGING_QUICK_REFERENCE.md    # Quick logging reference
│   │
│   ├── *.tf                           # Terraform infrastructure files
│   ├── agentcore.tf                   # AgentCore runtime and gateway
│   ├── bedrock.tf                     # Bedrock guardrails
│   ├── cloudwatch.tf                  # CloudWatch logging
│   ├── dynamodb.tf                    # DynamoDB tables
│   ├── ecr.tf                         # Container registry
│   ├── iam-gh.tf                      # GitHub Actions IAM
│   ├── main.tf                        # Main Terraform config
│   ├── providers.tf                   # Provider configuration
│   ├── s3.tf                          # S3 buckets
│   ├── secrets.tf                     # Secrets Manager
│   ├── variables.tf                   # Input variables
│   ├── output.tf                      # Output values
│   ├── vpc.tf                         # VPC configuration
│   │
│   └── src/                           # MCP Server application code
│       ├── main.py                    # FastMCP server entry point
│       ├── requirements.txt           # Python dependencies
│       ├── Dockerfile                 # Container image definition
│       ├── README.md                  # Application documentation
│       │
│       ├── clients/                   # External service clients
│       │   ├── bedrock_client.py      # AWS Bedrock integration
│       │   ├── guardrail_client.py    # Bedrock Guardrails
│       │   ├── s3_client.py           # S3 operations
│       │   ├── secrets_client.py      # Secrets Manager
│       │   └── sharepoint/            # SharePoint integration
│       │       ├── auth.py            # OAuth2 authentication
│       │       └── graph_client.py    # Microsoft Graph API
│       │
│       ├── mcp_tools/                 # MCP tool implementations
│       │   ├── image_tools.py         # Image generation tools
│       │   └── sharepoint_tools.py    # SharePoint tools
│       │
│       ├── schemas/                   # Pydantic data models
│       │   ├── image_schemas.py       # Image generation schemas
│       │   └── sharepoint_schemas.py  # SharePoint schemas
│       │
│       ├── utils/                     # Utility functions
│       │   ├── logger_util.py         # Logging configuration
│       │   ├── metric_util.py         # CloudWatch metrics
│       │   └── document_processor.py  # Document text extraction
│       │
│       ├── middlewares/               # FastAPI middlewares
│       │   └── request_logging.py     # Request/response logging
│       │
│       ├── client.py                  # Test client for MCP calls
│       └── test_client.py             # Comprehensive test suite
│
├── quicksuite-administration/         # QuickSuite configuration
│   └── *.tf                           # Terraform for QuickSuite setup
│
└── quicksuite-redirect/               # Route53 DNS configuration
    └── *.tf                           # DNS redirect setup
```

### Key Directories

- **agentcore/**: Core infrastructure and MCP server application
- **agentcore/src/**: Python application code for the MCP server
- **agentcore/src/clients/**: Integration clients for AWS and Microsoft services
- **agentcore/src/mcp_tools/**: MCP tool implementations (the actual AI capabilities)
- **quicksuite-administration/**: Amazon QuickSuite configuration
- **quicksuite-redirect/**: DNS routing configuration


---

## Technical Architecture

### High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    Amazon QuickSuite User                        │
│                  (Chat Interface in Browser)                     │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             │ HTTPS
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│              Amazon QuickSuite Chat Agent                        │
│           (Invokes MCP Actions via AgentCore)                    │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             │ MCP Protocol
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│           AWS Bedrock AgentCore Gateway                          │
│              (AWS_IAM Authorization)                             │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             │ Routes to Runtime
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│         AWS Bedrock AgentCore Runtime                            │
│         (Serverless Container Execution)                         │
│                                                                   │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │           FastMCP Server (Python/FastAPI)                 │  │
│  │                                                            │  │
│  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐   │  │
│  │  │ Image Tools  │  │SharePoint    │  │ Future Tools │   │  │
│  │  │              │  │ Tools        │  │              │   │  │
│  │  └──────────────┘  └──────────────┘  └──────────────┘   │  │
│  └───────────────────────────────────────────────────────────┘  │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             │ Integrates with
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│                      AWS Services                                │
│                                                                   │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐          │
│  │   Bedrock    │  │  Guardrails  │  │      S3      │          │
│  │ (AI Models)  │  │  (Content    │  │   (Image     │          │
│  │              │  │   Filtering) │  │   Storage)   │          │
│  └──────────────┘  └──────────────┘  └──────────────┘          │
│                                                                   │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐          │
│  │  DynamoDB    │  │  CloudWatch  │  │   Secrets    │          │
│  │  (Audit Log) │  │  (Logs &     │  │   Manager    │          │
│  │              │  │   Metrics)   │  │   (Config)   │          │
│  └──────────────┘  └──────────────┘  └──────────────┘          │
│                                                                   │
│  ┌──────────────────────────────────────────────────┐           │
│  │  Bedrock AgentCore Identity                      │           │
│  │  (OAuth2 Credential Provider for SharePoint)    │           │
│  └──────────────────────────────────────────────────┘           │
└─────────────────────────────────────────────────────────────────┘
                             │
                             │ OAuth2 + Graph API
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│                   Microsoft Services                             │
│                                                                   │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐          │
│  │  Azure AD    │  │  Graph API   │  │  SharePoint  │          │
│  │  (OAuth2)    │  │  (REST API)  │  │   Online     │          │
│  └──────────────┘  └──────────────┘  └──────────────┘          │
└─────────────────────────────────────────────────────────────────┘
```

### Component Descriptions

#### 1. Amazon QuickSuite Chat Agent
- User-facing chat interface
- Natural language processing
- Invokes MCP actions based on user intent
- Displays responses (text, images, documents)

#### 2. AWS Bedrock AgentCore Gateway
- Entry point for MCP protocol
- AWS_IAM authorization
- Routes requests to appropriate runtime
- Handles authentication and authorization

#### 3. AWS Bedrock AgentCore Runtime
- Serverless container execution environment
- Runs the FastMCP server
- Auto-scales based on demand
- Isolated execution per request

#### 4. FastMCP Server (Python Application)
- Implements Model Context Protocol
- Hosts multiple MCP tools
- Manages connections to AWS and Microsoft services
- Handles request/response lifecycle

#### 5. AWS Services Integration
- **Bedrock**: AI model inference (Stability AI, Amazon Titan)
- **Guardrails**: Content filtering and PII detection
- **S3**: Image storage with presigned URLs
- **DynamoDB**: Audit logging and state management
- **CloudWatch**: Application logs and metrics
- **Secrets Manager**: Configuration and credentials
- **AgentCore Identity**: OAuth2 token management

#### 6. Microsoft Services Integration
- **Azure AD**: OAuth2 authentication
- **Graph API**: RESTful API for Microsoft 365
- **SharePoint Online**: Document and content management

### Data Flow Examples

#### Image Generation Flow

```
1. User: "Generate an image of a mountain landscape"
2. QuickSuite → AgentCore Gateway → Runtime
3. Runtime → FastMCP Server → image_tools.generate_image()
4. Validate prompt with Guardrails
5. Generate image with Bedrock
6. Upload image to S3
7. Create presigned URL
8. Log to DynamoDB
9. Return URL to user
10. User sees image in chat
```

#### SharePoint Document Access Flow

```
1. User: "Show me documents from the Marketing folder"
2. QuickSuite → AgentCore Gateway → Runtime
3. Runtime → FastMCP Server → sharepoint_tools.list_sharepoint_folder_contents()
4. Get OAuth2 token from AWS Credential Provider
5. Call Microsoft Graph API
6. Retrieve folder contents
7. Format response
8. Return to user
9. User sees document list in chat
```


---

## Module Documentation

### Core Modules

#### 1. main.py - FastMCP Server Entry Point

**Purpose**: Initializes and runs the FastMCP server with all tools and configurations.

**Key Components**:
- `AppContext`: Shared context containing AWS and SharePoint clients
- `app_lifespan()`: Manages application lifecycle and client initialization
- `FastMCP`: MCP server instance with stateless HTTP mode
- Tool registration: Registers image and SharePoint tools

**Workflow**:
1. Load secrets from AWS Secrets Manager
2. Initialize logger with CloudWatch support
3. Create AWS clients (Bedrock, Guardrails, S3)
4. Create SharePoint clients (if configured)
5. Register all MCP tools
6. Start FastMCP server on specified host/port

**Configuration**:
- Reads from Secrets Manager via `get_secret()`
- Supports environment variables for local testing
- Configurable host, port, log level

---

### Client Modules

#### 2. clients/bedrock_client.py - AWS Bedrock Integration

**Purpose**: Handles image generation using Amazon Bedrock models.

**Supported Models**:
- Stability AI (Stable Diffusion XL)
- Amazon Titan Image Generator

**Key Methods**:
- `generate_image()`: Main entry point for image generation
- `_generate_stability()`: Stability AI-specific implementation
- `_generate_titan()`: Amazon Titan-specific implementation
- `check_health()`: Verifies Bedrock service connectivity

**Features**:
- Model-agnostic interface
- Automatic base64 decoding
- Error handling and logging
- Health check support

**Usage Example**:
```python
bedrock = BedrockClient("us-east-1")
image_bytes = await bedrock.generate_image(
    prompt="A mountain landscape",
    model="stability",
    width=1024,
    height=1024
)
```

---

#### 3. clients/guardrail_client.py - Content Moderation

**Purpose**: Validates prompts and content against Bedrock Guardrails policies.

**Content Filters**:
- Sexual content (HIGH)
- Violence (HIGH)
- Hate speech (HIGH)
- Insults (MEDIUM)
- Misconduct (HIGH)
- Prompt attacks (HIGH)

**PII Handling**:
- Email addresses (ANONYMIZE)
- Phone numbers (ANONYMIZE)
- SSN (BLOCK)
- Credit card numbers (BLOCK)

**Key Methods**:
- `validate_prompt()`: Validates input prompts
- `validate_output()`: Validates generated content
- `check_health()`: Verifies guardrail accessibility

**Response Format**:
```python
{
    "approved": True/False,
    "reason": "Content filter: VIOLENCE (HIGH)",
    "action": "GUARDRAIL_INTERVENED",
    "message": "User-friendly message"
}
```

---

#### 4. clients/s3_client.py - Image Storage

**Purpose**: Manages image storage in Amazon S3 with presigned URLs.

**Key Methods**:
- `upload_image()`: Uploads image with metadata
- `generate_presigned_url()`: Creates temporary access URLs
- `delete_image()`: Removes images from S3
- `list_images()`: Lists stored images

**Features**:
- Date-based folder structure (`images/YYYY-MM-DD/`)
- Server-side encryption (AES256)
- Metadata tagging (request_id, user_id, model)
- Configurable URL expiry

**Storage Pattern**:
```
s3://bucket-name/
└── images/
    └── 2026-02-19/
        ├── uuid-1.png
        ├── uuid-2.png
        └── uuid-3.png
```

---

#### 5. clients/sharepoint/auth.py - OAuth2 Authentication

**Purpose**: Manages OAuth2 authentication with Microsoft using AWS Credential Provider.

**Key Components**:
- `SharePointContext`: Configuration for SharePoint connection
- `@get_access_token_decorator`: Decorator that injects OAuth2 tokens
- `@requires_access_token`: Alternative decorator for token injection

**Authentication Flow**:
1. Tool function decorated with `@get_access_token_decorator`
2. Decorator calls AWS Bedrock AgentCore Identity
3. AWS manages OAuth2 flow with Azure AD
4. Token injected into function as parameter
5. Token used for Microsoft Graph API calls

**Benefits**:
- No credential storage in application
- Automatic token refresh
- Session binding
- Full audit trail

**Usage Example**:
```python
@get_access_token_decorator(sp_context)
async def _get_data_with_token(*, access_token: str):
    return await graph_client.get_site_info(domain, path, access_token)

result = await _get_data_with_token(access_token="")
```

---

#### 6. clients/sharepoint/graph_client.py - Microsoft Graph API

**Purpose**: Provides interface to Microsoft Graph API for SharePoint operations.

**Key Methods**:
- `get()`: Generic GET request to Graph API
- `post()`: Generic POST request to Graph API
- `get_site_info()`: Retrieves SharePoint site metadata
- `list_document_libraries()`: Lists all document libraries
- `get_document_content()`: Downloads document content

**Endpoint Construction**:
- Base URL: `https://graph.microsoft.com/v1.0/`
- Site endpoint: `sites/{domain}:{path}` or `sites/{domain}:` (root)
- Automatic error handling and logging

**Features**:
- Automatic authentication header injection
- Detailed error logging
- Timeout configuration
- Response validation

---

### MCP Tool Modules

#### 7. mcp_tools/image_tools.py - Image Generation Tools

**Purpose**: Implements MCP tools for AI image generation.

**Tool**: `generate_image`

**Parameters**:
- `prompt` (required): Text description of image
- `model` (optional): "stability" or "titan" (default: "stability")
- `width` (optional): Image width 512-2048 (default: 1024)
- `height` (optional): Image height 512-2048 (default: 1024)
- `style` (optional): Style preset for Stability AI
- `cfg_scale` (optional): CFG scale 1.0-35.0 (default: 7.0)
- `steps` (optional): Generation steps 10-150 (default: 50)
- `user_id` (optional): User identifier for audit
- `request_id` (optional): Request tracking ID
- `metadata` (optional): Additional metadata

**Workflow**:
1. Validate prompt with Guardrails
2. Generate image with Bedrock
3. Upload to S3
4. Generate presigned URL
5. Write audit log to DynamoDB
6. Emit CloudWatch metrics
7. Return response with image URL

**Response Format**:
```python
{
    "success": True,
    "request_id": "abc-123",
    "image_url": "https://s3.../image.png?...",
    "image_id": "xyz-789",
    "model_used": "stability",
    "s3_key": "images/2026-02-19/xyz-789.png",
    "expires_in": 3600,
    "elapsed_ms": 5234,
    "status": "SUCCEEDED"
}
```

**Logging Steps**:
- REQUEST_START
- GUARDRAIL_START / GUARDRAIL_COMPLETE / GUARDRAIL_BLOCKED
- IMAGE_GENERATION_START / IMAGE_GENERATION_COMPLETE
- S3_UPLOAD_START / S3_UPLOAD_COMPLETE
- PRESIGN_URL_START / PRESIGN_URL_COMPLETE
- REQUEST_SUCCESS

---

#### 8. mcp_tools/sharepoint_tools.py - SharePoint Integration Tools

**Purpose**: Implements read-only MCP tools for SharePoint operations.

**Tools**:

1. **get_sharepoint_site_info**
   - Retrieves site metadata (name, description, URL, dates)
   - No parameters required
   - Uses configured SHAREPOINT_SITE_URL

2. **list_sharepoint_document_libraries**
   - Lists all document libraries in the site
   - Returns library names, descriptions, URLs, types

3. **search_sharepoint**
   - Searches for content across the site
   - Parameter: `query` (search string)
   - Returns matching documents, lists, and items

4. **get_sharepoint_list_items**
   - Retrieves items from a SharePoint list
   - Parameters: `site_id`, `list_id`, `limit` (max 1000)
   - Returns list items with all fields

5. **get_sharepoint_document_content**
   - Downloads and extracts text from documents
   - Parameters: `site_id`, `drive_id`, `item_id`, `file_name`
   - Supports: PDF, Word, Excel, PowerPoint, text files
   - Returns metadata + extracted text content

6. **list_sharepoint_folder_contents**
   - Lists files and folders in a document library
   - Parameters: `site_id`, `drive_id`, `folder_path`
   - Returns files and folders with metadata

**Common Features**:
- OAuth2 authentication via AWS Credential Provider
- Automatic error handling
- Structured response format
- Comprehensive logging

**SharePoint URL Parsing**:
```python
# Input: https://tenant.sharepoint.com/sites/Marketing
# Parsed:
domain = "tenant.sharepoint.com"
site_path = "/sites/Marketing"

# Used in Graph API:
# sites/tenant.sharepoint.com:/sites/Marketing
```

---

### Utility Modules

#### 9. utils/logger_util.py - Logging Configuration

**Purpose**: Configures structured logging with CloudWatch support.

**Features**:
- Structured JSON logging for CloudWatch
- Contextual logging with request_id, user_id, step
- Log level configuration (DEBUG, INFO, WARNING, ERROR)
- Multiple output handlers (stdout, CloudWatch)

**Key Functions**:
- `setup_logger()`: Initializes logger with configuration
- `log_step()`: Logs functional steps with context

**Usage**:
```python
logger = setup_logger("DEBUG", "true")
log_step(logger, "IMAGE_GENERATION_START", request_id, user_id, 
         "Starting image generation", model="stability")
```

---

#### 10. utils/metric_util.py - CloudWatch Metrics

**Purpose**: Emits custom metrics to CloudWatch for monitoring.

**Metrics Tracked**:
- ToolRequests: Total tool invocations
- ToolSuccess / ToolFailures: Success/failure counts
- ToolLatency: Request duration
- GuardrailApprovals / GuardrailBlocks: Content filtering
- ImagesGenerated: Successful image generations
- ImageGenerationTime: Bedrock generation duration
- S3Uploads / S3UploadFailures: Storage operations

**Namespace**: `MCP/ImageGenerator`

**Usage**:
```python
log_metric("ImagesGenerated", 1)
log_metric("ToolLatency", 5.234, unit="Seconds")
```

---

#### 11. utils/document_processor.py - Document Text Extraction

**Purpose**: Extracts text content from various document formats.

**Supported Formats**:
- PDF (.pdf)
- Microsoft Word (.docx, .doc)
- Microsoft Excel (.xlsx, .xls)
- Microsoft PowerPoint (.pptx, .ppt)
- Text files (.txt, .md, .csv)

**Key Methods**:
- `is_supported()`: Checks if file type is supported
- `process_document()`: Extracts text from document bytes
- `get_supported_formats()`: Returns list of supported formats

**Features**:
- Automatic format detection
- Error handling for corrupted files
- Metadata extraction
- Character encoding detection


---

## Setup and Configuration

### AWS Prerequisites

1. **AWS Account Access**
   - Account ID: `<your-account-id>` (nonprod)
   - Required permissions: BedrockAgentCoreFullAccess, IAM, S3, DynamoDB, CloudWatch

2. **AccessCenter Roles**
   - AccountReadOnly (read-only access)
   - DevOpsContributor (deployment access)
   - DevOpsOwner (full access)

3. **AWS CLI Configuration**
   ```bash
   aws configure
   # or use AWS SSO
   aws sso login --profile your-profile
   ```

### Terraform Setup

1. **Install Terraform**
   ```bash
   # macOS
   brew install terraform
   
   # Verify installation
   terraform version  # Should be >= 1.5.0
   ```

2. **Initialize Terraform**
   ```bash
   cd ai-foundation/agentcore
   terraform init
   ```

3. **Configure Variables**
   
   Create `terraform.tfvars`:
   ```hcl
   aws_region    = "us-east-1"
   project_name  = "ai-foundation"
   environment   = "dev"
   
   # VPC Configuration
   existing_vpc_id = "<your-vpc-id>"
   existing_private_subnet_ids = [
     "<subnet-id-1>",
     "<subnet-id-2>"
   ]
   
   # Bedrock Configuration
   bedrock_model_id = "anthropic.claude-sonnet-4-20250514-v1:0"
   
   # Container Configuration
   agent_runtime_container_uri = "<account-id>.dkr.ecr.us-east-1.amazonaws.com/aifoundation:latest"
   
   # SharePoint OAuth2 (if using SharePoint)
   agentcore_microsoft_client_id     = "your-azure-client-id"
   agentcore_microsoft_client_secret = "your-azure-client-secret"
   ```

### Secrets Manager Configuration

1. **Navigate to Secrets Manager**
   ```bash
   aws secretsmanager list-secrets --region us-east-1
   ```

2. **Update MCP Server Secrets**
   
   Secret name: `non-prod/mcp-server/secrets`
   
   ```json
   {
     "AWS_REGION": "us-east-1",
     "PORT": "8000",
     "HOST": "0.0.0.0",
     "LOG_LEVEL": "DEBUG",
     "ENABLE_CLOUDWATCH_LOGS": "true",
     "ENABLE_CLOUDWATCH_METRICS": "true",
     
     "GUARDRAIL_ID": "your-guardrail-id",
     "GUARDRAIL_VERSION": "DRAFT",
     
     "S3_BUCKET": "ai-foundation-dev-data",
     "PRESIGNED_URL_EXPIRY": "3600",
     
     "DDB_AUDIT_TABLE": "ai-foundation-dev-audit",
     
     "SHAREPOINT_PROVIDER_NAME": "microsoft-oauth-provider",
     "SHAREPOINT_CALLBACK_URL": "https://your-callback-url",
     "SHAREPOINT_SITE_URL": "https://yourtenant.sharepoint.com/sites/yoursite",
     "SHAREPOINT_AUTH_FLOW": "USER_FEDERATION",
     "SHAREPOINT_SCOPES": "Sites.Read.All,Files.Read.All,User.Read",
     
     "ALLOWED_HOSTS": "*"
   }
   ```

3. **Update via CLI**
   ```bash
   aws secretsmanager update-secret \
     --secret-id non-prod/mcp-server/secrets \
     --secret-string file://secrets.json \
     --region us-east-1
   ```

### SharePoint Setup (Optional)

#### Step 1: Azure AD Application Registration

1. Go to Azure Portal → Azure Active Directory → App registrations
2. Click "New registration"
3. Name: "AI Foundation MCP Server"
4. Supported account types: "Single tenant"
5. Redirect URI: Leave blank (will add later)
6. Click "Register"

#### Step 2: Configure API Permissions

1. Go to "API permissions"
2. Click "Add a permission"
3. Select "Microsoft Graph"
4. Select "Delegated permissions"
5. Add permissions:
   - Sites.Read.All
   - Files.Read.All
   - User.Read
6. Click "Grant admin consent"

#### Step 3: Create Client Secret

1. Go to "Certificates & secrets"
2. Click "New client secret"
3. Description: "MCP Server Secret"
4. Expires: 24 months
5. Click "Add"
6. Copy the secret value (shown only once)

#### Step 4: Note Application Details

Copy these values:
- Application (client) ID
- Directory (tenant) ID
- Client secret value

#### Step 5: Create AWS OAuth2 Credential Provider

```bash
aws bedrock-agentcore create-oauth2-credential-provider \
  --region us-east-1 \
  --name "microsoft-oauth-provider" \
  --credential-provider-vendor "MicrosoftOauth2" \
  --oauth2-provider-config-input '{
      "microsoftOauth2ProviderConfig": {
        "clientId": "your-azure-client-id",
        "clientSecret": "your-azure-client-secret",
        "tenantId": "your-azure-tenant-id"
      }
    }'
```

#### Step 6: Get Callback URL

```bash
# Extract callback URL from response
aws bedrock-agentcore get-oauth2-credential-provider \
  --region us-east-1 \
  --name "microsoft-oauth-provider" \
  --query 'callbackUrl' \
  --output text
```

#### Step 7: Add Callback URL to Azure AD

1. Go back to Azure AD app registration
2. Go to "Authentication"
3. Click "Add a platform"
4. Select "Web"
5. Add the callback URL from Step 6
6. Click "Configure"

#### Step 8: Update Secrets Manager

Add to `non-prod/mcp-server/secrets`:
```json
{
  "SHAREPOINT_PROVIDER_NAME": "microsoft-oauth-provider",
  "SHAREPOINT_CALLBACK_URL": "callback-url-from-step-6",
  "SHAREPOINT_SITE_URL": "https://yourtenant.sharepoint.com/sites/yoursite"
}
```

### Container Build and Push

1. **Build Docker Image**
   ```bash
   cd ai-foundation/agentcore/src
   docker build -t agentcore-mcp-server:latest .
   ```

2. **Authenticate to ECR**
   ```bash
   aws ecr get-login-password --region us-east-1 | \
     docker login --username AWS --password-stdin \
     <account-id>.dkr.ecr.us-east-1.amazonaws.com
   ```

3. **Tag Image**
   ```bash
   docker tag agentcore-mcp-server:latest \
     <account-id>.dkr.ecr.us-east-1.amazonaws.com/ai-foundation-dev-agentcore:latest
   ```

4. **Push to ECR**
   ```bash
   docker push \
     <account-id>.dkr.ecr.us-east-1.amazonaws.com/ai-foundation-dev-agentcore:latest
   ```

### Local Development Setup

1. **Create Virtual Environment**
   ```bash
   cd ai-foundation/agentcore/src
   python3 -m venv venv
   source venv/bin/activate  # macOS/Linux
   ```

2. **Install Dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Create .env File**
   ```bash
   cp .env_sample .env
   # Edit .env with your configuration
   ```

4. **Run Locally**
   ```bash
   python main.py
   # or
   uvicorn main:app --host 0.0.0.0 --port 8000 --reload
   ```

5. **Test Locally**
   ```bash
   # Test health endpoint
   curl http://localhost:8000/health
   
   # Run test suite
   python test_client.py
   ```


---

## Deployment Guide

### Initial Deployment

1. **Review Terraform Plan**
   ```bash
   cd ai-foundation/agentcore
   terraform plan -var-file=terraform.tfvars
   ```

2. **Apply Infrastructure**
   ```bash
   terraform apply -var-file=terraform.tfvars
   ```

3. **Verify Deployment**
   ```bash
   # Check AgentCore Runtime status
   aws bedrock-agentcore get-agent-runtime \
     --agent-runtime-id "ai_foundation_dev_runtime-xxxxx" \
     --region us-east-1
   
   # Should show status: "READY"
   ```

4. **Build and Deploy Container**
   ```bash
   cd src
   docker build -t agentcore-mcp-server:latest .
   
   # Push to ECR (see Container Build section)
   ```

5. **Update Runtime** (if needed)
   ```bash
   terraform apply -var-file=terraform.tfvars
   ```

6. **Test Deployment**
   ```bash
   python test_client.py
   ```

### Updating the Application

#### Code Changes Only

1. **Make code changes** in `src/`

2. **Test locally**
   ```bash
   python main.py
   python test_client.py
   ```

3. **Build new container**
   ```bash
   docker build -t agentcore-mcp-server:latest .
   ```

4. **Push to ECR**
   ```bash
   # Tag with version
   docker tag agentcore-mcp-server:latest \
     <account-id>.dkr.ecr.us-east-1.amazonaws.com/ai-foundation-dev-agentcore:v1.2.3
   
   # Push
   docker push \
     <account-id>.dkr.ecr.us-east-1.amazonaws.com/ai-foundation-dev-agentcore:v1.2.3
   ```

5. **Update runtime** (if using versioned tags)
   ```bash
   # Update terraform.tfvars with new image tag
   agent_runtime_container_uri = "<account-id>.dkr.ecr.us-east-1.amazonaws.com/aifoundation:v1.2.3"
   
   # Apply
   terraform apply -var-file=terraform.tfvars
   ```

#### Infrastructure Changes

1. **Update Terraform files**

2. **Plan changes**
   ```bash
   terraform plan -var-file=terraform.tfvars
   ```

3. **Review plan carefully**

4. **Apply changes**
   ```bash
   terraform apply -var-file=terraform.tfvars
   ```

#### Configuration Changes

1. **Update Secrets Manager**
   ```bash
   aws secretsmanager update-secret \
     --secret-id non-prod/mcp-server/secrets \
     --secret-string file://secrets.json \
     --region us-east-1
   ```

2. **Restart runtime** (automatic on next invocation)

### Rollback Procedure

#### Rollback Container Version

1. **Identify previous version**
   ```bash
   aws ecr describe-images \
     --repository-name ai-foundation-dev-agentcore \
     --region us-east-1
   ```

2. **Update terraform.tfvars**
   ```hcl
   agent_runtime_container_uri = "<account-id>.dkr.ecr.us-east-1.amazonaws.com/aifoundation:v1.2.2"
   ```

3. **Apply**
   ```bash
   terraform apply -var-file=terraform.tfvars
   ```

#### Rollback Infrastructure

1. **Revert Terraform changes**
   ```bash
   git revert <commit-hash>
   ```

2. **Apply previous state**
   ```bash
   terraform apply -var-file=terraform.tfvars
   ```

### CI/CD with GitHub Actions

The repository includes GitHub Actions workflow for automated deployment.

**Workflow File**: `.github/workflows/deploy.yml`

**Triggers**:
- Push to `main` branch
- Manual workflow dispatch

**Steps**:
1. Checkout code
2. Configure AWS credentials
3. Build Docker image
4. Push to ECR
5. Update Terraform
6. Run tests

**Required Secrets**:
- `AWS_ROLE_ARN`: IAM role for GitHub Actions
- `AWS_REGION`: Deployment region

### Monitoring Deployment

1. **Check CloudWatch Logs**
   ```bash
   aws logs tail /aws/bedrock-agentcore/ai_foundation_dev_runtime \
     --follow \
     --region us-east-1
   ```

2. **Check Runtime Status**
   ```bash
   aws bedrock-agentcore get-agent-runtime \
     --agent-runtime-id "ai_foundation_dev_runtime-xxxxx" \
     --region us-east-1 \
     --query 'status'
   ```

3. **Run Health Check**
   ```bash
   python test_client.py 1  # Test 1: List tools
   ```

4. **Check CloudWatch Metrics**
   - Go to CloudWatch → Metrics → MCP/ImageGenerator
   - View ToolRequests, ToolSuccess, ToolLatency


---

## Using Amazon QuickSuite Chat Agents

### Accessing QuickSuite

1. **Navigate to QuickSuite**
   - URL: [QuickSuite Portal](https://quicksuite.aws.amazon.com)
   - Login with your AWS credentials

2. **Open Chat Interface**
   - Click on "Chat" or "Agents" in the navigation
   - Select the AI Foundation agent

### Available Commands

#### Image Generation

**Basic Usage**:
```
Generate an image of a mountain landscape at sunset
```

**With Specifications**:
```
Create a 1024x1024 image of a robot using the stability model
```

**Style Variations**:
```
Generate a photorealistic image of a coffee shop interior
```

**What Happens**:
1. Your prompt is sent to the MCP server
2. Guardrails check for inappropriate content
3. Bedrock generates the image
4. Image is uploaded to S3
5. You receive a presigned URL
6. Image is displayed in chat

**Response Time**: 5-10 seconds

#### SharePoint Operations

**Get Site Information**:
```
Show me information about the SharePoint site
```

**List Document Libraries**:
```
What document libraries are available?
```

**Search for Content**:
```
Search SharePoint for "quarterly report"
```

**List Folder Contents**:
```
Show me files in the Marketing folder
```

**Get Document Content**:
```
Show me the content of the Q4 Report document
```

**What Happens**:
1. Your request is sent to the MCP server
2. OAuth2 token is obtained from AWS
3. Microsoft Graph API is called
4. Results are formatted and returned
5. You see the information in chat

**Response Time**: 2-5 seconds

### Best Practices

#### For Image Generation

1. **Be Specific**: "A serene mountain landscape with a lake" is better than "nature"
2. **Avoid Inappropriate Content**: Guardrails will block violent, sexual, or hateful content
3. **Use Style Keywords**: "photorealistic", "artistic", "minimalist", "detailed"
4. **Specify Dimensions**: Default is 1024x1024, but you can request different sizes
5. **Choose Model**: Stability AI for artistic images, Titan for general purpose

#### For SharePoint

1. **Know Your Site Structure**: Understand folder hierarchy
2. **Use Specific Search Terms**: Better results with specific keywords
3. **Check Permissions**: You can only access content you have permissions for
4. **Document Formats**: Text extraction works best with PDF, Word, Excel
5. **Be Patient**: Large documents may take longer to process

### Example Conversations

#### Image Generation Example

```
User: Generate an image of a futuristic city skyline at night

Agent: I'll generate that image for you using Amazon Bedrock.

[Processing...]

Agent: ✅ Image generated successfully!
      Model: Stability AI
      Size: 1024x1024
      Time: 6.2 seconds
      
      [Image displayed]
      
      This image will be available for 1 hour.
```

#### SharePoint Example

```
User: Search for documents about the marketing campaign

Agent: I'll search SharePoint for "marketing campaign".

[Processing...]

Agent: Found 5 documents:

      1. Marketing Campaign Q1 2026.docx
         Modified: 2026-02-15
         Location: /Marketing/Campaigns/
         
      2. Campaign Budget Analysis.xlsx
         Modified: 2026-02-10
         Location: /Finance/Marketing/
         
      [... more results ...]
      
      Would you like me to show you the content of any of these documents?
```

### Limitations in QuickSuite

1. **Image Display**: Images are shown as links or embedded (depending on QuickSuite version)
2. **File Downloads**: SharePoint documents are shown as text, not downloadable
3. **Concurrent Requests**: One request at a time per user
4. **Session Timeout**: OAuth sessions expire after inactivity
5. **Rate Limiting**: AWS and Microsoft APIs have rate limits

### Troubleshooting in QuickSuite

**Problem**: "Content blocked by guardrails"
- **Solution**: Rephrase your prompt to avoid inappropriate content

**Problem**: "SharePoint not configured"
- **Solution**: Contact administrator to set up SharePoint integration

**Problem**: "Image generation failed"
- **Solution**: Try again with a simpler prompt or different model

**Problem**: "Access denied to SharePoint"
- **Solution**: Ensure you have permissions to the SharePoint site

**Problem**: "Request timeout"
- **Solution**: Try a simpler request or wait and retry


---

## Features and Capabilities

### Current Features

#### 1. AI Image Generation

**Capabilities**:
- Generate images from text descriptions
- Support for multiple AI models (Stability AI, Amazon Titan)
- Customizable image dimensions (512x512 to 2048x2048)
- Style presets and generation parameters
- Automatic content moderation
- PII detection and handling

**Use Cases**:
- Marketing materials and visuals
- Presentation graphics
- Concept visualization
- Product mockups
- Social media content

**Technical Details**:
- Models: Stability AI SDXL, Amazon Titan Image Generator
- Output format: PNG
- Storage: Amazon S3 with presigned URLs
- Expiry: Configurable (default 1 hour)
- Audit: Full logging in DynamoDB

#### 2. SharePoint Integration

**Capabilities**:
- Browse SharePoint sites and libraries
- Search across site content
- Access list items and metadata
- Download and extract document text
- Navigate folder structures
- View document metadata

**Supported Document Types**:
- PDF documents
- Microsoft Word (.docx, .doc)
- Microsoft Excel (.xlsx, .xls)
- Microsoft PowerPoint (.pptx, .ppt)
- Text files (.txt, .md, .csv)

**Use Cases**:
- Document discovery and search
- Content summarization
- Information retrieval
- Compliance and audit
- Knowledge management

**Technical Details**:
- Authentication: OAuth2 via AWS Credential Provider
- API: Microsoft Graph API v1.0
- Permissions: Read-only (Sites.Read.All, Files.Read.All)
- Token management: Automatic via AWS
- Session binding: User-specific access

#### 3. Content Moderation

**Guardrail Filters**:
- Sexual content (HIGH sensitivity)
- Violence (HIGH sensitivity)
- Hate speech (HIGH sensitivity)
- Insults (MEDIUM sensitivity)
- Misconduct (HIGH sensitivity)
- Prompt attacks (HIGH sensitivity)

**PII Handling**:
- Email addresses: Anonymized
- Phone numbers: Anonymized
- Social Security Numbers: Blocked
- Credit card numbers: Blocked

**Benefits**:
- Prevents inappropriate content generation
- Protects sensitive information
- Ensures compliance with policies
- Provides user-friendly error messages

#### 4. Audit and Compliance

**Audit Logging**:
- Every request logged to DynamoDB
- Includes: request_id, user_id, timestamp, status
- Tracks: prompts, models used, outcomes
- Retention: Configurable

**CloudWatch Logging**:
- Structured JSON logs
- Request tracing with unique IDs
- Performance metrics
- Error tracking

**Metrics**:
- Request counts
- Success/failure rates
- Latency measurements
- Resource utilization

#### 5. Security Features

**Authentication**:
- AWS IAM for AgentCore Gateway
- OAuth2 for SharePoint (via AWS Credential Provider)
- JWT for QuickSuite integration

**Authorization**:
- Role-based access control
- Scoped IAM policies
- SharePoint permissions respected

**Encryption**:
- Data in transit: TLS 1.2+
- Data at rest: S3 encryption (AES256)
- Secrets: AWS Secrets Manager with KMS

**Network Security**:
- VPC isolation
- Security groups
- Private subnets for sensitive operations

### Performance Characteristics

**Image Generation**:
- Average latency: 5-8 seconds
- Guardrail validation: 200-500ms
- S3 upload: 100-300ms
- Total: 5-10 seconds end-to-end

**SharePoint Operations**:
- Site info: 1-2 seconds
- Document list: 2-3 seconds
- Search: 3-5 seconds
- Document download: 2-10 seconds (depends on size)

**Scalability**:
- Concurrent users: Unlimited (serverless)
- Auto-scaling: Automatic via AgentCore
- Rate limits: AWS and Microsoft API limits apply

**Availability**:
- Target: 99.9% uptime
- Multi-AZ deployment
- Automatic failover
- Health checks every 30 seconds


---

## Current Limitations

### Technical Limitations

#### Image Generation

1. **Model Limitations**
   - Maximum resolution: 2048x2048 pixels
   - Minimum resolution: 512x512 pixels
   - Single image per request
   - No image editing or variations
   - No image-to-image generation

2. **Content Restrictions**
   - Guardrails may block legitimate content
   - No fine-tuning of content filters
   - Cannot generate copyrighted characters
   - Limited style control

3. **Performance**
   - Generation time: 5-10 seconds (cannot be reduced)
   - No batch processing
   - No priority queuing

#### SharePoint Integration

1. **Read-Only Access**
   - Cannot create documents
   - Cannot update documents
   - Cannot delete documents
   - Cannot modify permissions
   - Cannot create folders or lists

2. **Document Processing**
   - Text extraction only (no formatting)
   - Large documents (>10MB) may timeout
   - Some formats not supported (images, videos)
   - No OCR for scanned documents
   - Limited metadata extraction

3. **Search Limitations**
   - Basic keyword search only
   - No advanced query syntax
   - Results limited to 50 items
   - No relevance ranking customization

#### Infrastructure

1. **Deployment**
   - Single region only (us-east-1)
   - No multi-region failover
   - Manual deployment process
   - No blue-green deployment

2. **Monitoring**
   - CloudWatch logs only
   - No distributed tracing
   - Limited custom metrics
   - No real-time alerting

3. **Scalability**
   - AWS API rate limits apply
   - Microsoft Graph API throttling
   - No request queuing
   - No load balancing control

### Functional Limitations

#### User Experience

1. **No User Interface**
   - Chat-only interface
   - No web dashboard
   - No admin console
   - No user management UI

2. **Limited Feedback**
   - No progress indicators
   - No partial results
   - No cancellation support
   - No request history

3. **Session Management**
   - No persistent sessions
   - OAuth tokens expire
   - No session recovery
   - No multi-device sync

#### Integration

1. **QuickSuite Dependency**
   - Requires Amazon QuickSuite
   - No standalone API
   - No direct HTTP access
   - No webhook support

2. **SharePoint Constraints**
   - Single site configuration
   - No multi-tenant support
   - No on-premises SharePoint
   - Azure AD only (no other identity providers)

3. **No Third-Party Integrations**
   - No Slack integration
   - No Microsoft Teams integration
   - No email notifications
   - No calendar integration

### Known Issues

1. **Occasional Timeout**
   - Large SharePoint documents may timeout
   - Workaround: Request smaller documents or use pagination

2. **OAuth Token Refresh**
   - First-time users must authorize in browser
   - Tokens expire after inactivity
   - Workaround: Re-authorize when prompted

3. **Image URL Expiry**
   - Presigned URLs expire after 1 hour
   - Workaround: Regenerate image if needed

4. **CloudWatch Log Delay**
   - Logs may take 1-2 minutes to appear
   - Workaround: Wait before checking logs

5. **Guardrail False Positives**
   - Some legitimate prompts may be blocked
   - Workaround: Rephrase prompt or contact admin

### Planned Improvements

#### Short Term (Next 3 Months)

- [ ] Add image editing capabilities
- [ ] Support for more document formats
- [ ] Improved error messages
- [ ] Request cancellation
- [ ] Progress indicators

#### Medium Term (3-6 Months)

- [ ] Multi-site SharePoint support
- [ ] Document upload capability
- [ ] Advanced search features
- [ ] Custom guardrail configuration
- [ ] Real-time monitoring dashboard

#### Long Term (6-12 Months)

- [ ] Multi-region deployment
- [ ] Blue-green deployment
- [ ] Distributed tracing
- [ ] Third-party integrations
- [ ] Admin console
- [ ] API gateway for direct access

### Workarounds

#### For Image Generation Limitations

1. **Need higher resolution?**
   - Generate at max resolution (2048x2048)
   - Use external upscaling tools

2. **Content blocked by guardrails?**
   - Rephrase prompt to be more specific
   - Avoid trigger words
   - Contact admin for policy review

3. **Generation too slow?**
   - Use Titan model (slightly faster)
   - Reduce image dimensions
   - Generate during off-peak hours

#### For SharePoint Limitations

1. **Need to edit documents?**
   - Use SharePoint web interface
   - Use Microsoft Office apps
   - Request write access from admin

2. **Document too large?**
   - Request specific sections
   - Use search to find relevant parts
   - Download directly from SharePoint

3. **Need multiple sites?**
   - Contact admin to configure additional sites
   - Use separate deployments per site
   - Use SharePoint search across sites


---

## Monitoring and Debugging

### CloudWatch Logs

#### Accessing Logs

**Via AWS Console**:
1. Navigate to CloudWatch → Logs → Log groups
2. Find log group: `/aws/bedrock-agentcore/ai_foundation_dev_runtime`
3. Click on latest log stream
4. Use filter patterns to search

**Via AWS CLI**:
```bash
# Tail logs in real-time
aws logs tail /aws/bedrock-agentcore/ai_foundation_dev_runtime \
  --follow \
  --region us-east-1

# Get logs for specific time range
aws logs filter-log-events \
  --log-group-name /aws/bedrock-agentcore/ai_foundation_dev_runtime \
  --start-time $(date -u -d '1 hour ago' +%s)000 \
  --region us-east-1
```

#### Log Structure

**Structured JSON Format**:
```json
{
  "timestamp": "2026-02-19T10:30:45Z",
  "level": "INFO",
  "step": "IMAGE_GENERATION_COMPLETE",
  "request_id": "abc-123-def",
  "user_id": "test-user",
  "message": "Image generated successfully in 5.23s",
  "model": "stability",
  "generation_time_s": 5.23,
  "image_size_bytes": 1048576
}
```

**Functional Steps Logged**:
- REQUEST_START
- GUARDRAIL_START / GUARDRAIL_COMPLETE / GUARDRAIL_BLOCKED / GUARDRAIL_ERROR
- IMAGE_GENERATION_START / IMAGE_GENERATION_COMPLETE / IMAGE_GENERATION_ERROR
- S3_UPLOAD_START / S3_UPLOAD_COMPLETE / S3_UPLOAD_ERROR
- PRESIGN_URL_START / PRESIGN_URL_COMPLETE / PRESIGN_URL_ERROR
- REQUEST_SUCCESS

#### CloudWatch Insights Queries

**Trace Specific Request**:
```sql
fields @timestamp, step, message
| filter request_id = "abc-123-def"
| sort @timestamp asc
```

**Find All Errors**:
```sql
fields @timestamp, step, message, error
| filter level = "ERROR"
| sort @timestamp desc
| limit 50
```

**Performance Analysis**:
```sql
fields @timestamp, request_id, elapsed_ms, step
| filter step = "REQUEST_SUCCESS"
| stats avg(elapsed_ms), max(elapsed_ms), min(elapsed_ms)
```

**Guardrail Blocks**:
```sql
fields @timestamp, user_id, reason, message
| filter step = "GUARDRAIL_BLOCKED"
| sort @timestamp desc
```

**Image Generation by Model**:
```sql
fields generation_time_s, model
| filter step = "IMAGE_GENERATION_COMPLETE"
| stats avg(generation_time_s), count() by model
```

### CloudWatch Metrics

#### Available Metrics

**Namespace**: `MCP/ImageGenerator`

**Metrics**:
- `ToolRequests`: Total tool invocations
- `ToolSuccess`: Successful completions
- `ToolFailures`: Failed requests
- `ToolLatency`: Request duration (seconds)
- `GuardrailApprovals`: Content approved
- `GuardrailBlocks`: Content blocked
- `GuardrailErrors`: Guardrail failures
- `ImagesGenerated`: Successful generations
- `ImageGenerationTime`: Bedrock generation time
- `S3Uploads`: Successful uploads
- `S3UploadFailures`: Failed uploads

#### Creating Dashboards

1. Go to CloudWatch → Dashboards
2. Create dashboard: "AI Foundation MCP"
3. Add widgets:
   - Line graph: ToolRequests over time
   - Number: Current ToolSuccess rate
   - Stacked area: ToolSuccess vs ToolFailures
   - Line graph: ToolLatency (p50, p95, p99)
   - Number: GuardrailBlocks count
   - Line graph: ImageGenerationTime by model

#### Setting Up Alarms

**High Error Rate Alarm**:
```bash
aws cloudwatch put-metric-alarm \
  --alarm-name "MCP-High-Error-Rate" \
  --alarm-description "Alert when error rate exceeds 10%" \
  --metric-name ToolFailures \
  --namespace MCP/ImageGenerator \
  --statistic Sum \
  --period 300 \
  --evaluation-periods 2 \
  --threshold 10 \
  --comparison-operator GreaterThanThreshold \
  --region us-east-1
```

**High Latency Alarm**:
```bash
aws cloudwatch put-metric-alarm \
  --alarm-name "MCP-High-Latency" \
  --alarm-description "Alert when latency exceeds 30 seconds" \
  --metric-name ToolLatency \
  --namespace MCP/ImageGenerator \
  --statistic Average \
  --period 300 \
  --evaluation-periods 2 \
  --threshold 30 \
  --comparison-operator GreaterThanThreshold \
  --region us-east-1
```

### DynamoDB Audit Logs

#### Accessing Audit Data

**Via AWS Console**:
1. Navigate to DynamoDB → Tables
2. Select table: `ai-foundation-dev-audit`
3. Click "Explore table items"
4. Use filters to search

**Via AWS CLI**:
```bash
# Scan recent records
aws dynamodb scan \
  --table-name ai-foundation-dev-audit \
  --limit 10 \
  --region us-east-1

# Query by request_id
aws dynamodb query \
  --table-name ai-foundation-dev-audit \
  --key-condition-expression "request_id = :rid" \
  --expression-attribute-values '{":rid":{"S":"abc-123-def"}}' \
  --region us-east-1
```

#### Audit Record Structure

```json
{
  "request_id": "abc-123-def",
  "ts": "2026-02-19T10:30:45.123Z",
  "status": "SUCCEEDED",
  "user_id": "test-user",
  "model": "stability",
  "prompt": "A mountain landscape...",
  "image_id": "xyz-789",
  "s3_key": "images/2026-02-19/xyz-789.png",
  "elapsed_ms": 5234,
  "width": 1024,
  "height": 1024,
  "metadata": {}
}
```

### Debugging Common Issues

#### Issue: No Logs Appearing

**Diagnosis**:
```bash
# Check log group exists
aws logs describe-log-groups \
  --log-group-name-prefix "/aws/bedrock-agentcore" \
  --region us-east-1

# Check runtime status
aws bedrock-agentcore get-agent-runtime \
  --agent-runtime-id "ai_foundation_dev_runtime-xxxxx" \
  --region us-east-1
```

**Solutions**:
1. Verify `ENABLE_CLOUDWATCH_LOGS=true` in Secrets Manager
2. Check IAM role has CloudWatch Logs permissions
3. Trigger a test request to generate logs
4. Wait 1-2 minutes for logs to appear

#### Issue: High Error Rate

**Diagnosis**:
```bash
# Check recent errors
aws logs filter-log-events \
  --log-group-name /aws/bedrock-agentcore/ai_foundation_dev_runtime \
  --filter-pattern "ERROR" \
  --start-time $(date -u -d '1 hour ago' +%s)000 \
  --region us-east-1
```

**Common Causes**:
1. Bedrock model throttling
2. S3 bucket permissions
3. Guardrail configuration
4. Network connectivity

#### Issue: Slow Performance

**Diagnosis**:
```sql
-- CloudWatch Insights query
fields @timestamp, request_id, elapsed_ms, step
| filter step = "REQUEST_SUCCESS"
| sort elapsed_ms desc
| limit 20
```

**Common Causes**:
1. Large image dimensions
2. Complex prompts
3. Network latency
4. Cold start (first request)

#### Issue: SharePoint Authentication Failures

**Diagnosis**:
```bash
# Check OAuth2 provider
aws bedrock-agentcore get-oauth2-credential-provider \
  --name "microsoft-oauth-provider" \
  --region us-east-1

# Check logs for auth errors
aws logs filter-log-events \
  --log-group-name /aws/bedrock-agentcore/ai_foundation_dev_runtime \
  --filter-pattern "401" \
  --region us-east-1
```

**Common Causes**:
1. Expired client secret
2. Incorrect callback URL
3. Missing API permissions
4. Token not refreshed

### Testing and Validation

#### Running Test Suite

```bash
cd ai-foundation/agentcore/src

# Run all tests
python test_client.py

# Run specific test
python test_client.py 1      # List tools
python test_client.py 3      # Image generation (Stability)
python test_client.py 2      # SharePoint connectivity

# Run multiple tests
python test_client.py 1 3 4  # Tests 1, 3, and 4
```

#### Manual Testing

**Test Image Generation**:
```bash
curl -X POST http://localhost:8000/mcp \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "id": "1",
    "method": "tools/call",
    "params": {
      "name": "generate_image",
      "arguments": {
        "prompt": "A serene mountain landscape",
        "model": "stability"
      }
    }
  }'
```

**Test Health Endpoint**:
```bash
curl http://localhost:8000/health
```

#### Load Testing

```bash
# Install Apache Bench
brew install apache-bench  # macOS

# Run load test
ab -n 100 -c 10 http://localhost:8000/ping
```


---

## Maintenance and Updates

### Regular Maintenance Tasks

#### Weekly

1. **Review CloudWatch Logs**
   - Check for errors and warnings
   - Identify performance issues
   - Review guardrail blocks

2. **Check Metrics**
   - Monitor success/failure rates
   - Review latency trends
   - Check resource utilization

3. **Audit Log Review**
   - Review DynamoDB audit records
   - Check for unusual patterns
   - Verify compliance

#### Monthly

1. **Update Dependencies**
   ```bash
   cd ai-foundation/agentcore/src
   pip list --outdated
   pip install --upgrade <package>
   # Update requirements.txt
   ```

2. **Review IAM Policies**
   - Check for unused permissions
   - Update least-privilege policies
   - Review access logs

3. **Clean Up S3**
   - Review old images
   - Apply lifecycle policies
   - Check storage costs

4. **Update Documentation**
   - Update this file with changes
   - Document new features
   - Update troubleshooting guides

#### Quarterly

1. **Security Review**
   - Review IAM roles and policies
   - Check for security updates
   - Review audit logs
   - Update secrets and credentials

2. **Performance Optimization**
   - Analyze CloudWatch metrics
   - Identify bottlenecks
   - Optimize configurations

3. **Cost Analysis**
   - Review AWS costs
   - Optimize resource usage
   - Adjust retention policies

4. **Disaster Recovery Test**
   - Test backup procedures
   - Verify rollback process
   - Update DR documentation

### Updating Components

#### Updating Python Dependencies

1. **Check for Updates**
   ```bash
   pip list --outdated
   ```

2. **Update Specific Package**
   ```bash
   pip install --upgrade boto3
   ```

3. **Update requirements.txt**
   ```bash
   pip freeze > requirements.txt
   ```

4. **Test Locally**
   ```bash
   python main.py
   python test_client.py
   ```

5. **Deploy**
   ```bash
   docker build -t agentcore-mcp-server:latest .
   # Push to ECR and update runtime
   ```

#### Updating Terraform Modules

1. **Check for Updates**
   ```bash
   terraform init -upgrade
   ```

2. **Review Changes**
   ```bash
   terraform plan -var-file=terraform.tfvars
   ```

3. **Apply Updates**
   ```bash
   terraform apply -var-file=terraform.tfvars
   ```

#### Updating Bedrock Models

1. **Check Available Models**
   ```bash
   aws bedrock list-foundation-models --region us-east-1
   ```

2. **Update Configuration**
   ```hcl
   # In terraform.tfvars
   bedrock_model_id = "new-model-id"
   ```

3. **Apply Changes**
   ```bash
   terraform apply -var-file=terraform.tfvars
   ```

#### Updating Guardrails

1. **Modify Guardrail Configuration**
   ```hcl
   # In bedrock.tf
   content_policy_config {
     filters_config {
       type            = "SEXUAL"
       input_strength  = "MEDIUM"  # Changed from HIGH
       output_strength = "HIGH"
     }
   }
   ```

2. **Apply Changes**
   ```bash
   terraform apply -var-file=terraform.tfvars
   ```

3. **Test New Configuration**
   ```bash
   python test_client.py 5  # Test guardrail blocking
   ```

### Backup and Recovery

#### Backup Procedures

**DynamoDB Backups**:
```bash
# Create on-demand backup
aws dynamodb create-backup \
  --table-name ai-foundation-dev-audit \
  --backup-name "audit-backup-$(date +%Y%m%d)" \
  --region us-east-1
```

**S3 Backups**:
```bash
# Enable versioning
aws s3api put-bucket-versioning \
  --bucket ai-foundation-dev-data \
  --versioning-configuration Status=Enabled

# Create backup
aws s3 sync s3://ai-foundation-dev-data s3://ai-foundation-dev-backup
```

**Secrets Manager Backups**:
```bash
# Export secrets
aws secretsmanager get-secret-value \
  --secret-id non-prod/mcp-server/secrets \
  --region us-east-1 \
  --query SecretString \
  --output text > secrets-backup.json
```

**Terraform State Backups**:
```bash
# Backup state file
terraform state pull > terraform-state-backup.json
```

#### Recovery Procedures

**Restore DynamoDB**:
```bash
aws dynamodb restore-table-from-backup \
  --target-table-name ai-foundation-dev-audit-restored \
  --backup-arn <backup-arn> \
  --region us-east-1
```

**Restore S3**:
```bash
aws s3 sync s3://ai-foundation-dev-backup s3://ai-foundation-dev-data
```

**Restore Secrets**:
```bash
aws secretsmanager update-secret \
  --secret-id non-prod/mcp-server/secrets \
  --secret-string file://secrets-backup.json \
  --region us-east-1
```

### Scaling Considerations

#### Vertical Scaling

**Increase Container Resources**:
```hcl
# In agentcore.tf
resource "aws_bedrockagentcore_agent_runtime" "main" {
  # ... other configuration ...
  
  compute_configuration {
    memory_size = 1024  # Increased from 512
    cpu_units   = 512   # Increased from 256
  }
}
```

#### Horizontal Scaling

AgentCore automatically scales horizontally based on demand. No configuration needed.

**Monitor Scaling**:
```bash
# Check active instances
aws bedrock-agentcore describe-agent-runtime \
  --agent-runtime-id "ai_foundation_dev_runtime-xxxxx" \
  --region us-east-1 \
  --query 'scalingConfiguration'
```

#### Cost Optimization

1. **Reduce Image Storage Costs**
   ```hcl
   # Add lifecycle policy to S3
   lifecycle_rule {
     enabled = true
     expiration {
       days = 7  # Delete images after 7 days
     }
   }
   ```

2. **Optimize DynamoDB**
   ```hcl
   # Use on-demand billing
   billing_mode = "PAY_PER_REQUEST"
   ```

3. **Reduce Log Retention**
   ```bash
   aws logs put-retention-policy \
     --log-group-name /aws/bedrock-agentcore/ai_foundation_dev_runtime \
     --retention-in-days 7 \
     --region us-east-1
   ```

### Decommissioning

#### Graceful Shutdown

1. **Notify Users**
   - Send advance notice
   - Provide migration path
   - Set end-of-life date

2. **Disable New Requests**
   ```hcl
   # In agentcore.tf
   resource "aws_bedrockagentcore_agent_runtime" "main" {
     # ... other configuration ...
     enabled = false
   }
   ```

3. **Export Data**
   ```bash
   # Export audit logs
   aws dynamodb scan \
     --table-name ai-foundation-dev-audit \
     --region us-east-1 > audit-export.json
   
   # Backup images
   aws s3 sync s3://ai-foundation-dev-data ./image-backup/
   ```

4. **Destroy Infrastructure**
   ```bash
   terraform destroy -var-file=terraform.tfvars
   ```

5. **Clean Up**
   - Delete ECR images
   - Remove Secrets Manager secrets
   - Delete CloudWatch log groups
   - Remove IAM roles and policies


---

## Troubleshooting

### Common Issues and Solutions

#### Issue: Runtime Status Not "READY"

**Symptoms**:
- Runtime shows "CREATING" or "FAILED" status
- Requests fail with "Runtime not available"

**Diagnosis**:
```bash
aws bedrock-agentcore get-agent-runtime \
  --agent-runtime-id "ai_foundation_dev_runtime-xxxxx" \
  --region us-east-1
```

**Solutions**:
1. Check container image exists in ECR
2. Verify IAM role permissions
3. Check CloudWatch logs for errors
4. Ensure VPC and subnets are correct
5. Wait 5-10 minutes for initialization

#### Issue: "Guardrail validation failed"

**Symptoms**:
- Image generation fails
- Error message mentions guardrails

**Diagnosis**:
```bash
# Check guardrail configuration
aws bedrock get-guardrail \
  --guardrail-identifier <guardrail-id> \
  --region us-east-1
```

**Solutions**:
1. Verify guardrail ID and version in Secrets Manager
2. Check IAM permissions for Bedrock Guardrails
3. Test with a simple, safe prompt
4. Review guardrail configuration

#### Issue: "SharePoint not configured"

**Symptoms**:
- SharePoint tools not available
- Error message about missing configuration

**Diagnosis**:
```bash
# Check secrets
aws secretsmanager get-secret-value \
  --secret-id non-prod/mcp-server/secrets \
  --region us-east-1 \
  --query SecretString
```

**Solutions**:
1. Verify `SHAREPOINT_CALLBACK_URL` is set
2. Check OAuth2 credential provider exists
3. Ensure Azure AD app is configured
4. Verify callback URL matches Azure AD

#### Issue: "Access token expired"

**Symptoms**:
- SharePoint operations fail with 401 error
- Error message about authentication

**Diagnosis**:
```bash
# Check CloudWatch logs for auth errors
aws logs filter-log-events \
  --log-group-name /aws/bedrock-agentcore/ai_foundation_dev_runtime \
  --filter-pattern "401" \
  --region us-east-1
```

**Solutions**:
1. Re-authorize in browser (first-time users)
2. Check Azure AD client secret hasn't expired
3. Verify OAuth2 provider configuration
4. Wait for automatic token refresh

#### Issue: "S3 upload failed"

**Symptoms**:
- Image generation succeeds but upload fails
- Error message about S3

**Diagnosis**:
```bash
# Check S3 bucket exists
aws s3 ls s3://ai-foundation-dev-data

# Check IAM permissions
aws iam get-role-policy \
  --role-name ai-foundation-dev-agentcore-runtime-role \
  --policy-name ai-foundation-dev-agentcore-runtime-policy
```

**Solutions**:
1. Verify S3 bucket exists
2. Check IAM role has S3 permissions
3. Ensure bucket name in Secrets Manager is correct
4. Check bucket region matches runtime region

#### Issue: High Latency

**Symptoms**:
- Requests take longer than 30 seconds
- Timeout errors

**Diagnosis**:
```sql
-- CloudWatch Insights
fields @timestamp, elapsed_ms, step
| filter step = "REQUEST_SUCCESS"
| stats avg(elapsed_ms), max(elapsed_ms)
```

**Solutions**:
1. Reduce image dimensions
2. Use faster model (Titan vs Stability)
3. Check network connectivity
4. Review CloudWatch metrics for bottlenecks
5. Increase timeout in client

#### Issue: Container Build Fails

**Symptoms**:
- Docker build errors
- Missing dependencies

**Diagnosis**:
```bash
# Check Dockerfile
cat Dockerfile

# Check requirements.txt
cat requirements.txt
```

**Solutions**:
1. Update base image version
2. Fix dependency conflicts
3. Clear Docker cache: `docker system prune -a`
4. Check Python version compatibility
5. Review build logs for specific errors

#### Issue: Terraform Apply Fails

**Symptoms**:
- Terraform errors during apply
- Resource creation failures

**Diagnosis**:
```bash
terraform plan -var-file=terraform.tfvars
```

**Solutions**:
1. Check AWS credentials
2. Verify IAM permissions
3. Review Terraform state
4. Check for resource conflicts
5. Update Terraform providers

### Error Messages Reference

#### "name 'site_name' is not defined"

**Cause**: SharePoint URL parsing error
**Solution**: Ensure `SHAREPOINT_SITE_URL` is in correct format:
```
https://domain.sharepoint.com/sites/sitename
```

#### "Unknown service: 'bedrock-agentcore'"

**Cause**: Outdated boto3 version
**Solution**: Update boto3:
```bash
pip install --upgrade boto3>=1.35.0
```

#### "Content blocked by guardrails"

**Cause**: Prompt contains inappropriate content
**Solution**: Rephrase prompt to avoid trigger words

#### "Token does not have required claims"

**Cause**: Missing API permissions in Azure AD
**Solution**: Add required permissions and grant admin consent

#### "Runtime not found"

**Cause**: Incorrect runtime ARN
**Solution**: Verify runtime ARN in test_client.py matches deployed runtime

### Getting Help

#### Internal Support

1. **Check Documentation**
   - Read this file
   - Review README files
   - Check CloudWatch logs

2. **Contact Team**
   - Application Owner: [contact your administrator]
   - DevOps Team: via AccessCenter
   - Slack: #ai-foundation-support

3. **Create Issue**
   - GitHub Issues (if available)
   - Include error messages
   - Provide request_id for tracing

#### External Resources

1. **AWS Documentation**
   - [Bedrock AgentCore](https://docs.aws.amazon.com/bedrock/latest/userguide/agentcore.html)
   - [Bedrock Guardrails](https://docs.aws.amazon.com/bedrock/latest/userguide/guardrails.html)
   - [CloudWatch Logs](https://docs.aws.amazon.com/AmazonCloudWatch/latest/logs/)

2. **Microsoft Documentation**
   - [Graph API](https://docs.microsoft.com/en-us/graph/)
   - [SharePoint REST API](https://docs.microsoft.com/en-us/sharepoint/dev/)
   - [Azure AD OAuth2](https://docs.microsoft.com/en-us/azure/active-directory/develop/)

3. **Community**
   - AWS Forums
   - Stack Overflow
   - GitHub Discussions


---

## Security and Compliance

### Security Architecture

#### Defense in Depth

1. **Network Security**
   - VPC isolation
   - Private subnets for sensitive operations
   - Security groups with least-privilege rules
   - No public internet access for runtime

2. **Identity and Access Management**
   - AWS IAM for service authentication
   - OAuth2 for user authentication
   - Role-based access control (RBAC)
   - Scoped permissions per service

3. **Data Protection**
   - Encryption in transit (TLS 1.2+)
   - Encryption at rest (S3 AES256, DynamoDB encryption)
   - Secrets encrypted with KMS
   - PII detection and anonymization

4. **Application Security**
   - Input validation
   - Content filtering via guardrails
   - Rate limiting
   - Error handling without information disclosure

### Authentication and Authorization

#### AWS IAM

**AgentCore Gateway**:
- Requires AWS_IAM authorization
- Validates caller identity
- Enforces resource policies

**Runtime Role**:
- Scoped permissions for AWS services
- No cross-account access
- Regular permission audits

#### OAuth2 (SharePoint)

**Flow**: Authorization Code with PKCE
**Provider**: AWS Bedrock AgentCore Identity
**Token Storage**: AWS Token Vault (encrypted)
**Token Lifetime**: Configurable (default 1 hour)
**Refresh**: Automatic via AWS

#### QuickSuite Integration

**Authentication**: JWT tokens
**Authorization**: Custom JWT authorizer
**Discovery URL**: PingFederate OIDC endpoint
**Allowed Clients**: AmazonQuickSuite

### Data Security

#### Data Classification

**Public**: None
**Internal**: 
- Application logs
- Performance metrics
- Configuration data

**Confidential**:
- User prompts
- Generated images
- SharePoint content
- Audit logs

**Restricted**:
- OAuth2 tokens
- API keys
- Client secrets

#### Data Handling

**In Transit**:
- TLS 1.2+ for all connections
- Certificate validation
- No plaintext transmission

**At Rest**:
- S3 server-side encryption (AES256)
- DynamoDB encryption
- Secrets Manager with KMS
- CloudWatch Logs encryption

**In Use**:
- Memory encryption (AWS managed)
- No disk persistence
- Secure deletion after processing

#### Data Retention

**Images**: 7 days (configurable)
**Audit Logs**: 90 days (configurable)
**CloudWatch Logs**: 7 days (configurable)
**Metrics**: 15 months (AWS default)

### Compliance

#### Content Moderation

**Guardrail Policies**:
- Sexual content: HIGH sensitivity
- Violence: HIGH sensitivity
- Hate speech: HIGH sensitivity
- Insults: MEDIUM sensitivity
- Misconduct: HIGH sensitivity
- Prompt attacks: HIGH sensitivity

**PII Handling**:
- Email: ANONYMIZE
- Phone: ANONYMIZE
- SSN: BLOCK
- Credit cards: BLOCK

#### Audit Trail

**What is Logged**:
- All tool invocations
- User identifiers
- Timestamps
- Request/response data
- Success/failure status
- Error messages

**Where**:
- DynamoDB (structured audit)
- CloudWatch Logs (detailed logs)
- CloudWatch Metrics (aggregated)

**Retention**:
- Configurable per compliance requirements
- Immutable once written
- Encrypted at rest

#### Access Control

**Principle of Least Privilege**:
- Minimum permissions required
- No wildcard permissions
- Regular permission reviews
- Scoped resource access

**Separation of Duties**:
- Read-only roles for monitoring
- Contributor roles for deployment
- Owner roles for administration

### Security Best Practices

#### For Administrators

1. **Rotate Credentials Regularly**
   ```bash
   # Rotate Azure AD client secret every 6 months
   # Update in Secrets Manager
   # Restart runtime
   ```

2. **Review IAM Policies**
   ```bash
   # Monthly review
   aws iam get-role-policy \
     --role-name ai-foundation-dev-agentcore-runtime-role \
     --policy-name ai-foundation-dev-agentcore-runtime-policy
   ```

3. **Monitor Audit Logs**
   ```bash
   # Weekly review
   aws dynamodb scan \
     --table-name ai-foundation-dev-audit \
     --filter-expression "status = :failed" \
     --expression-attribute-values '{":failed":{"S":"FAILED"}}'
   ```

4. **Update Dependencies**
   ```bash
   # Monthly security updates
   pip list --outdated
   pip install --upgrade <package>
   ```

5. **Review CloudWatch Alarms**
   ```bash
   # Check alarm status
   aws cloudwatch describe-alarms \
     --alarm-name-prefix "MCP-" \
     --region us-east-1
   ```

#### For Developers

1. **Never Commit Secrets**
   - Use .gitignore for .env files
   - Use Secrets Manager for credentials
   - Scan commits for secrets

2. **Validate Input**
   - Use Pydantic schemas
   - Sanitize user input
   - Validate file types

3. **Handle Errors Securely**
   - Don't expose stack traces
   - Log errors internally
   - Return user-friendly messages

4. **Use Secure Dependencies**
   - Pin versions in requirements.txt
   - Review security advisories
   - Update regularly

5. **Follow Coding Standards**
   - Use type hints
   - Write unit tests
   - Document security considerations

#### For Users

1. **Don't Share Credentials**
   - Use personal AWS accounts
   - Don't share OAuth tokens
   - Report suspicious activity

2. **Be Mindful of Content**
   - Don't generate inappropriate images
   - Don't share sensitive information
   - Follow company policies

3. **Report Issues**
   - Report security concerns immediately
   - Don't attempt to exploit vulnerabilities
   - Follow responsible disclosure

### Incident Response

#### Security Incident Procedure

1. **Detection**
   - CloudWatch alarms
   - Audit log anomalies
   - User reports

2. **Assessment**
   - Determine severity
   - Identify affected systems
   - Estimate impact

3. **Containment**
   - Disable affected components
   - Revoke compromised credentials
   - Block malicious traffic

4. **Eradication**
   - Remove malicious code
   - Patch vulnerabilities
   - Update configurations

5. **Recovery**
   - Restore from backups
   - Verify system integrity
   - Resume operations

6. **Post-Incident**
   - Document incident
   - Update procedures
   - Implement preventive measures

#### Contact Information

**Security Team**: [contact your security team]
**On-Call**: [contact your on-call team]
**Escalation**: CISO office

### Compliance Certifications

**Current**:
- AWS Well-Architected Framework
- OWASP Top 10 compliance
- Internal security standards

**Planned**:
- SOC 2 Type II
- ISO 27001
- GDPR compliance


---

## API Reference

### MCP Protocol

The server implements the Model Context Protocol (MCP) for tool invocation.

**Base URL**: Accessed via AgentCore Gateway
**Protocol**: JSON-RPC 2.0
**Transport**: HTTP/HTTPS with Server-Sent Events (SSE)

### JSON-RPC Format

**Request**:
```json
{
  "jsonrpc": "2.0",
  "id": "unique-request-id",
  "method": "tools/call",
  "params": {
    "name": "tool_name",
    "arguments": {
      "param1": "value1",
      "param2": "value2"
    }
  }
}
```

**Response (Success)**:
```json
{
  "jsonrpc": "2.0",
  "id": "unique-request-id",
  "result": {
    "content": [
      {
        "type": "text",
        "text": "{\"success\": true, ...}"
      }
    ]
  }
}
```

**Response (Error)**:
```json
{
  "jsonrpc": "2.0",
  "id": "unique-request-id",
  "error": {
    "code": -32600,
    "message": "Invalid Request",
    "data": "Additional error details"
  }
}
```

### Available Tools

#### 1. generate_image

Generates an image from a text prompt using Amazon Bedrock.

**Method**: `tools/call`
**Tool Name**: `generate_image`

**Parameters**:
| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| prompt | string | Yes | - | Text description of the image |
| model | string | No | "stability" | Model to use ("stability" or "titan") |
| width | integer | No | 1024 | Image width (512-2048) |
| height | integer | No | 1024 | Image height (512-2048) |
| style | string | No | null | Style preset (Stability AI only) |
| cfg_scale | float | No | 7.0 | CFG scale (1.0-35.0) |
| steps | integer | No | 50 | Generation steps (10-150) |
| user_id | string | No | "unknown" | User identifier |
| request_id | string | No | auto-generated | Request tracking ID |
| metadata | object | No | {} | Additional metadata |

**Example Request**:
```json
{
  "jsonrpc": "2.0",
  "id": "1",
  "method": "tools/call",
  "params": {
    "name": "generate_image",
    "arguments": {
      "prompt": "A serene mountain landscape at sunset",
      "model": "stability",
      "width": 1024,
      "height": 1024,
      "user_id": "john.doe"
    }
  }
}
```

**Example Response**:
```json
{
  "jsonrpc": "2.0",
  "id": "1",
  "result": {
    "content": [{
      "type": "text",
      "text": "{\"success\":true,\"request_id\":\"abc-123\",\"image_url\":\"https://s3.../image.png?...\",\"image_id\":\"xyz-789\",\"model_used\":\"stability\",\"s3_key\":\"images/2026-02-19/xyz-789.png\",\"expires_in\":3600,\"elapsed_ms\":5234,\"status\":\"SUCCEEDED\"}"
    }]
  }
}
```

#### 2. get_sharepoint_site_info

Retrieves information about the configured SharePoint site.

**Method**: `tools/call`
**Tool Name**: `get_sharepoint_site_info`

**Parameters**: None

**Example Request**:
```json
{
  "jsonrpc": "2.0",
  "id": "2",
  "method": "tools/call",
  "params": {
    "name": "get_sharepoint_site_info",
    "arguments": {}
  }
}
```

**Example Response**:
```json
{
  "jsonrpc": "2.0",
  "id": "2",
  "result": {
    "content": [{
      "type": "text",
      "text": "{\"success\":true,\"site_name\":\"Marketing Site\",\"description\":\"Marketing team collaboration\",\"created_date\":\"2025-01-15T10:00:00Z\",\"last_modified\":\"2026-02-19T14:30:00Z\",\"web_url\":\"https://tenant.sharepoint.com/sites/marketing\",\"site_id\":\"tenant.sharepoint.com,abc-123,def-456\"}"
    }]
  }
}
```

#### 3. list_sharepoint_document_libraries

Lists all document libraries in the SharePoint site.

**Method**: `tools/call`
**Tool Name**: `list_sharepoint_document_libraries`

**Parameters**: None

**Example Response**:
```json
{
  "success": true,
  "count": 3,
  "libraries": [
    {
      "name": "Documents",
      "description": "Shared documents",
      "web_url": "https://tenant.sharepoint.com/sites/marketing/Shared Documents",
      "drive_type": "documentLibrary",
      "drive_id": "b!abc123..."
    }
  ]
}
```

#### 4. search_sharepoint

Searches for content across the SharePoint site.

**Method**: `tools/call`
**Tool Name**: `search_sharepoint`

**Parameters**:
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| query | string | Yes | Search query string |

**Example Request**:
```json
{
  "jsonrpc": "2.0",
  "id": "4",
  "method": "tools/call",
  "params": {
    "name": "search_sharepoint",
    "arguments": {
      "query": "quarterly report"
    }
  }
}
```

**Example Response**:
```json
{
  "success": true,
  "query": "quarterly report",
  "count": 5,
  "results": [
    {
      "title": "Q4 2025 Report.docx",
      "url": "https://tenant.sharepoint.com/sites/marketing/Documents/Q4%202025%20Report.docx",
      "type": "#microsoft.graph.driveItem",
      "summary": "Quarterly financial report for Q4 2025..."
    }
  ]
}
```

#### 5. get_sharepoint_list_items

Retrieves items from a SharePoint list.

**Method**: `tools/call`
**Tool Name**: `get_sharepoint_list_items`

**Parameters**:
| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| site_id | string | Yes | - | SharePoint site ID |
| list_id | string | Yes | - | List ID or name |
| limit | integer | No | 100 | Max items (1-1000) |

**Example Response**:
```json
{
  "success": true,
  "site_id": "tenant.sharepoint.com,abc-123",
  "list_id": "def-456",
  "count": 10,
  "items": [
    {
      "item_id": "1",
      "created": "2026-01-15T10:00:00Z",
      "modified": "2026-02-19T14:30:00Z",
      "fields": {
        "Title": "Project Alpha",
        "Status": "In Progress",
        "Owner": "Team Member"
      }
    }
  ]
}
```

#### 6. get_sharepoint_document_content

Downloads and extracts text from a SharePoint document.

**Method**: `tools/call`
**Tool Name**: `get_sharepoint_document_content`

**Parameters**:
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| site_id | string | Yes | SharePoint site ID |
| drive_id | string | Yes | Document library ID |
| item_id | string | Yes | Document item ID |
| file_name | string | Yes | File name (for type detection) |

**Example Response**:
```json
{
  "success": true,
  "file_name": "Report.pdf",
  "file_size": 1048576,
  "file_type": "pdf",
  "created": "2026-01-15T10:00:00Z",
  "modified": "2026-02-19T14:30:00Z",
  "created_by": "Team Member",
  "modified_by": "Team Member",
  "web_url": "https://tenant.sharepoint.com/...",
  "content_extracted": true,
  "text_content": "This is the extracted text from the PDF...",
  "page_count": 10
}
```

#### 7. list_sharepoint_folder_contents

Lists files and folders in a document library folder.

**Method**: `tools/call`
**Tool Name**: `list_sharepoint_folder_contents`

**Parameters**:
| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| site_id | string | Yes | - | SharePoint site ID |
| drive_id | string | Yes | - | Document library ID |
| folder_path | string | No | "" | Folder path (empty for root) |

**Example Response**:
```json
{
  "success": true,
  "site_id": "tenant.sharepoint.com,abc-123",
  "drive_id": "b!def456...",
  "folder_path": "Marketing/Campaigns",
  "count": 5,
  "items": [
    {
      "name": "Campaign Plan.docx",
      "id": "01ABC...",
      "type": "file",
      "size": 524288,
      "created": "2026-01-15T10:00:00Z",
      "modified": "2026-02-19T14:30:00Z",
      "web_url": "https://tenant.sharepoint.com/...",
      "mime_type": "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    },
    {
      "name": "Assets",
      "id": "01DEF...",
      "type": "folder",
      "size": 0,
      "created": "2026-01-10T09:00:00Z",
      "modified": "2026-02-18T16:00:00Z",
      "web_url": "https://tenant.sharepoint.com/...",
      "child_count": 12
    }
  ]
}
```

### Health Endpoints

#### GET /ping

Basic liveness check.

**Response**:
```json
{
  "status": "healthy",
  "service": "mcp"
}
```

#### GET /health

Comprehensive health check including AWS service connectivity.

**Response**:
```json
{
  "status": "healthy",
  "services": {
    "bedrock": "healthy",
    "s3": "healthy",
    "guardrail": "healthy"
  }
}
```

### Error Codes

| Code | Message | Description |
|------|---------|-------------|
| -32700 | Parse error | Invalid JSON |
| -32600 | Invalid Request | Invalid JSON-RPC request |
| -32601 | Method not found | Tool does not exist |
| -32602 | Invalid params | Invalid tool parameters |
| -32603 | Internal error | Server error |

### Rate Limits

**AWS Bedrock**: 
- Stability AI: 5 requests/second
- Amazon Titan: 10 requests/second

**Microsoft Graph API**:
- 10,000 requests/10 minutes per app
- Throttling: 429 status code

**AgentCore Runtime**:
- No explicit limit (auto-scales)
- Subject to AWS account limits

---

## Appendix

### Glossary

- **AgentCore**: AWS Bedrock service for hosting AI agent runtimes
- **MCP**: Model Context Protocol - standard for AI tool invocation
- **Guardrails**: Content filtering and moderation system
- **OAuth2**: Open standard for authorization
- **Graph API**: Microsoft's RESTful API for Microsoft 365
- **Presigned URL**: Temporary URL for accessing S3 objects
- **JWT**: JSON Web Token for authentication

### References

- [AWS Bedrock Documentation](https://docs.aws.amazon.com/bedrock/)
- [Model Context Protocol Specification](https://modelcontextprotocol.io/)
- [Microsoft Graph API Documentation](https://docs.microsoft.com/en-us/graph/)
- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [Terraform AWS Provider](https://registry.terraform.io/providers/hashicorp/aws/)

### Change Log

| Version | Date | Changes |
|---------|------|---------|
| 1.0.0 | 2026-02-19 | Initial release with image generation |
| 1.1.0 | 2026-02-19 | Added SharePoint integration |
| 1.2.0 | 2026-02-19 | Added CloudWatch logging and metrics |

### Contributors

- Application Owner: [contact your administrator]
- Development Team: AI Foundation Team
- Documentation: AI Assistant

---

**Document Version**: 1.0
**Last Updated**: February 19, 2026
**Status**: Active

For questions or support, contact: [your administrator]
