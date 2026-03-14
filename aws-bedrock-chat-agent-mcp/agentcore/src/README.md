# AI Foundation AgentCore — MCP Server (FastAPI)

AI Foundation AgentCore is a production-ready Model Context Protocol (MCP) Server built using FastAPI and deployed on Amazon AgentCore Runtime.

This server is designed to host multiple enterprise tools and integrations.  
Currently, it implements:
- **AWS Bedrock Tools**: Image Generation
- **SharePoint Tools**: Read-only operations (site info, document libraries, search, list items, document content, folder contents)

The MCP Server is consumed by Amazon QuickSight (Amazon Quick Suite) Chat Agents through MCP Actions.

------------------------------------------------------------

OVERVIEW

This is a generic MCP Server architecture that supports multiple tools and integrations.

**Current Implementations:**

1. **Image Generation** (AWS Bedrock)
   - Powered by Amazon Bedrock
   - Content moderation via Bedrock Guardrails
   - Image storage in Amazon S3
   - Audit logging in Amazon DynamoDB

2. **SharePoint Integration** (Microsoft Graph API)
   - Read-only operations for SharePoint Online
   - Site information retrieval
   - Document library browsing
   - Content search
   - List item access
   - Document content extraction (PDF, Word, Excel)
   - Folder navigation

**AWS Services Integration:**
- Amazon Bedrock (model inference)
- Bedrock Guardrails (content moderation and policy enforcement)
- Amazon S3 (image storage)
- Amazon DynamoDB (audit logging)
- Amazon CloudWatch (application logging and monitoring)

**Microsoft Services Integration:**
- Microsoft Graph API (SharePoint operations)
- Azure AD (OAuth2 authentication via AWS Credential Provider)
- SharePoint Online (document management)
- AWS Bedrock AgentCore Identity (OAuth2 token management)

------------------------------------------------------------

ARCHITECTURE FLOW

**Image Generation Flow:**
1. User interacts with Amazon Quick Suite Chat Agent  
2. Chat Agent invokes an MCP Action  
3. AgentCore routes the request to this MCP Server  
4. Image generation tool is executed  
5. Guardrails validate the prompt  
6. Bedrock generates the image  
7. Image is stored in Amazon S3  
8. Audit record is written to Amazon DynamoDB  
9. Logs are sent to Amazon CloudWatch  
10. Response (including image reference or presigned URL) is returned to the Chat Agent

**SharePoint Operations Flow:**
1. User interacts with Amazon Quick Suite Chat Agent
2. Chat Agent invokes a SharePoint MCP Action
3. AgentCore routes the request to this MCP Server
4. SharePoint tool is executed
5. AWS Bedrock AgentCore Identity provides OAuth2 token (via @requires_access_token decorator)
6. Microsoft Graph API request is made with token
7. SharePoint data is retrieved and processed
8. Response is returned to the Chat Agent  

------------------------------------------------------------

AWS SERVICES USED

- Amazon QuickSight (Quick Suite)
- Amazon AgentCore Runtime
- Amazon Bedrock
- Amazon Bedrock AgentCore Identity (OAuth2 Credential Provider)
- Bedrock Guardrails
- Amazon S3
- Amazon DynamoDB
- Amazon CloudWatch

MICROSOFT SERVICES USED

- Microsoft Graph API
- Azure Active Directory
- SharePoint Online

------------------------------------------------------------

REPOSITORY STRUCTURE

main.py  
clients/
├── bedrock_client.py
├── guardrail_client.py
├── s3_client.py
├── secrets_client.py
└── sharepoint/
    ├── __init__.py
    ├── auth.py
    └── graph_client.py
mcp_tools/  
├── image_tools.py
└── sharepoint_tools.py
middlewares/  
utils/  
schemas/
README.md  

------------------------------------------------------------

MCP ENDPOINT

Base path: /mcp

Mounted in main.py using the MCP streamable HTTP application.

------------------------------------------------------------

MCP TOOLS

**AWS Bedrock Tools:**
- generate_image - Generate images using Amazon Bedrock with guardrails

**SharePoint Tools (Read-Only):**
- get_sharepoint_site_info - Get SharePoint site information
- list_sharepoint_document_libraries - List all document libraries
- search_sharepoint - Search for content across the site
- get_sharepoint_list_items - Get items from a SharePoint list
- get_sharepoint_document_content - Get document content with text extraction
- list_sharepoint_folder_contents - List files and folders in a library

------------------------------------------------------------

HEALTH ENDPOINTS

GET /ping  
GET /health  

/ ping → Basic liveness check  
/ health → Validates connectivity to Bedrock, Guardrails, and S3  

------------------------------------------------------------

RUNNING LOCALLY

1. Install dependencies  
   pip install -r requirements.txt  

2. Configure environment variables
   cp .env.example .env
   # Edit .env with your AWS and SharePoint credentials

3. Start the server  
   python main.py  

Or using uvicorn:  
   uvicorn main:app --host 0.0.0.0 --port 8000

------------------------------------------------------------

SHAREPOINT SETUP (OPTIONAL)

SharePoint integration is optional. If not configured, only AWS tools will be available.

**Authentication Method:**
SharePoint uses AWS Bedrock AgentCore Identity OAuth2 Credential Provider for secure, managed authentication instead of direct credential management.

**Benefits of AWS Credential Provider:**
- ✅ Credentials stored securely in AWS (not in application)
- ✅ Tokens encrypted in AWS Token Vault
- ✅ Automatic token refresh and lifecycle management
- ✅ Session binding between agent and user identity
- ✅ Full audit trail via AWS CloudWatch
- ✅ Works with AgentCore Runtime for production deployments
- ✅ Supports multiple OAuth2 flows (USER_FEDERATION, CLIENT_CREDENTIALS)

**Prerequisites:**
1. AWS account with BedrockAgentCoreFullAccess permissions
2. Azure AD tenant with admin access
3. SharePoint Online site
4. Azure AD application registration

**Setup Steps:**

**Step 1: Create Azure AD Application**
1. Register app in Azure Portal (Azure AD > App registrations)
2. Add API permissions: Sites.Read.All, Files.Read.All (Delegated permissions)
3. Grant admin consent
4. Create client secret
5. Note: Application (client) ID, Directory (tenant) ID, and client secret

**Step 2: Create AWS OAuth2 Credential Provider**
```bash
aws bedrock-agentcore-control create-oauth2-credential-provider \
  --region us-east-1 \
  --name "microsoft-oauth-provider" \
  --credential-provider-vendor "MicrosoftOauth2" \
  --oauth2-provider-config-input '{
      "microsoftOauth2ProviderConfig": {
        "clientId": "<your-azure-client-id>",
        "clientSecret": "<your-azure-client-secret>",
        "tenantId": "<your-azure-tenant-id>"
      }
    }'
```

**Step 3: Get Callback URL**
```bash
# Extract callback URL from response
OAUTH2_CALLBACK_URL=$(echo $RESPONSE | jq -r '.callbackUrl')
```

**Step 4: Add Callback URL to Azure AD**
1. Go to Azure AD app > Authentication
2. Add the callback URL as a Redirect URI

**Step 5: Configure Environment Variables**
Add to .env file:
```bash
SHAREPOINT_PROVIDER_NAME=microsoft-oauth-provider
SHAREPOINT_CALLBACK_URL=<callback-url-from-step-3>
SHAREPOINT_SITE_URL=https://yourtenant.sharepoint.com/sites/yoursite
```

**Detailed Instructions:**
See SHAREPOINT_AWS_CREDENTIAL_PROVIDER_SETUP.md for complete step-by-step guide.

**Verification:**
- Server logs will show "SharePoint context initialized with provider: microsoft-oauth-provider" if configured
- Server logs will show "SharePoint not configured (missing SHAREPOINT_CALLBACK_URL)" if not configured
- SharePoint tools will only be available if properly configured
- First-time use will prompt for OAuth authorization in browser  

------------------------------------------------------------

CONFIGURATION

Configuration values are loaded using get_secret().

**AWS Configuration (Required):**

AWS_REGION  
PORT  
HOST  
LOG_LEVEL  
ENABLE_CLOUDWATCH_LOGS  
GUARDRAIL_ID  
GUARDRAIL_VERSION  
S3_BUCKET  
PRESIGNED_URL_EXPIRY  
DDB_AUDIT_TABLE (optional)

**SharePoint Configuration (Optional - AWS Credential Provider):**

SHAREPOINT_PROVIDER_NAME (defaults to "microsoft-oauth-provider")
SHAREPOINT_CALLBACK_URL (required - from AWS credential provider)
SHAREPOINT_AUTH_FLOW (defaults to "USER_FEDERATION")
SHAREPOINT_SITE_URL (required)
SHAREPOINT_SCOPES (optional - comma-separated list of Graph API scopes)

**AWS IAM Permissions Required:**

- Bedrock model invocation  
- Bedrock Guardrails  
- Bedrock AgentCore Identity (for SharePoint OAuth2)
  - bedrock-agentcore:CreateWorkloadIdentity
  - bedrock-agentcore:GetWorkloadAccessToken
  - bedrock-agentcore:GetResourceOauth2Token
- S3 read/write access  
- DynamoDB read/write access  
- CloudWatch logging

**Azure AD Permissions Required (for SharePoint):**

- Sites.Read.All (Delegated permission)
- Files.Read.All (Delegated permission)
- User.Read (Delegated permission)
- Admin consent granted  

------------------------------------------------------------

EXTENSIBILITY

This MCP Server is designed to support additional tools and integrations in the future.  
New tools can be added under mcp_tools/ and exposed through the MCP framework.

**Current Integrations:**
- AWS Bedrock (Image Generation)
- Microsoft SharePoint (Read Operations via AWS Credential Provider)

**Future Possibilities:**
- Additional AWS services (Lambda, Step Functions, etc.)
- Other Microsoft 365 services (Teams, OneDrive, Outlook)
- Third-party APIs and services with OAuth2 via AWS Credential Provider
- Custom business logic and workflows

**Adding New Tools:**
1. Create new tool file in mcp_tools/
2. Follow the pattern from image_tools.py or sharepoint_tools.py
3. Register tools in main.py using register_*_tools(mcp)
4. Update AppContext if new clients are needed
5. Add configuration to .env.example