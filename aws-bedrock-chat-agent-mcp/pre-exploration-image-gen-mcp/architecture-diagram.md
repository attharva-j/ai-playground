# Architecture Diagram: MCP Image Generator on AWS Agentcore Runtime

## High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         Amazon QuickSight Q Suite                           │
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │                          Q Suite Agent                              │    │ 
│  │                                                                     │    │
│  │  User Query: "Generate an image of a sunset over mountains"         │    │
│  └───────────────────────────────┬─────────────────────────────────────┘    │
└────────────────────────────────────┼────────────────────────────────────────┘
                                     │
                                     │ 1. Agent invokes MCP action
                                     │
                                     ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                      AWS Agentcore Runtime                                  │
│                                                                             │
│  ┌───────────────────────────────────────────────────────────────────────┐  │
│  │                    MCP Server Container                               │  │
│  │                                                                       │  │
│  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐                 │  │
│  │  │   Server.py  │  │ Guardrail    │  │  Bedrock     │                 │  │
│  │  │              │  │  Client      │  │  Client      │                 │  │
│  │  │  - Receives  │  │              │  │              │                 │  │
│  │  │    request   │  │  - Validates │  │  - Generates │                 │  │
│  │  │  - Routes    │  │    content   │  │    image     │                 │  │
│  │  │    to tools  │  │  - Blocks    │  │  - Returns   │                 │  │
│  │  │              │  │    unsafe    │  │    base64    │                 │  │
│  │  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘                 │  │
│  │         │                 │                 │                         │  │
│  │         └─────────────────┴─────────────────┘                         │  │
│  │                           │                                           │  │
│  │                           ▼                                           │  │
│  │                  ┌──────────────┐                                     │  │
│  │                  │  S3 Client   │                                     │  │
│  │                  │              │                                     │  │
│  │                  │  - Uploads   │                                     │  │
│  │                  │    image     │                                     │  │
│  │                  │  - Generates │                                     │  │
│  │                  │    presigned │                                     │  │
│  │                  │    URL       │                                     │  │
│  │                  └──────┬───────┘                                     │  │
│  └─────────────────────────┼─────────────────────────────────────────────┘  │
└────────────────────────────┼────────────────────────────────────────────────┘
                             │
                             │ 2. Upload image
                             │
                             ▼
        ┌─────────────────────────────────────────────────┐
        │                                                 │
        │  ┌────────────────────────────────────────┐     │
        │  │      AWS Bedrock Guardrails            │     │
        │  │                                        │     │
        │  │  3. Validate prompt against policies   │     │
        │  │                                        │     │
        │  │  ┌──────────────────────────────────┐  │     │
        │  │  │  Content Filters:                │  │     │
        │  │  │  - Violence: HIGH                │  │     │
        │  │  │  - Sexual: HIGH                  │  │     │
        │  │  │  - Hate: MEDIUM                  │  │     │
        │  │  │  - Insults: MEDIUM               │  │     │
        │  │  └──────────────────────────────────┘  │     │
        │  │                                        │     │
        │  │  ┌──────────────────────────────────┐  │     │
        │  │  │  Topic Policies:                 │  │     │
        │  │  │  - Violence (DENY)               │  │     │
        │  │  │  - Adult Content (DENY)          │  │     │
        │  │  │  - Obscene Content (DENY)        │  │     │
        │  │  └──────────────────────────────────┘  │     │
        │  └────────────────┬───────────────────────┘     │
        │                   │                             │
        │                   │ 4. If approved              │
        │                   ▼                             │
        │  ┌────────────────────────────────────────┐     │
        │  │      AWS Bedrock Models                │     │
        │  │                                        │     │
        │  │  ┌──────────────────────────────────┐  │     │
        │  │  │  Stability AI SDXL 1.0           │  │     │
        │  │  │  - High quality images           │  │     │
        │  │  │  - Multiple styles               │  │     │
        │  │  │  - 1024x1024 max                 │  │     │
        │  │  └──────────────────────────────────┘  │     │
        │  │                                        │     │
        │  │  ┌──────────────────────────────────┐  │     │
        │  │  │  Amazon Titan Image Generator    │  │     │
        │  │  │  - Built-in safety               │  │     │
        │  │  │  - Fast generation               │  │     │
        │  │  │  - 1024x1024 max                 │  │     │
        │  │  └──────────────────────────────────┘  │     │
        │  └────────────────┬───────────────────────┘     │
        │                   │                             │
        │                   │ 5. Return generated image   │
        └───────────────────┼─────────────────────────────┘
                            │
                            ▼
        ┌─────────────────────────────────────────────────┐
        │           Amazon S3 Bucket                      │
        │     agentcore-generated-images                  │
        │                                                 │
        │  ┌────────────────────────────────────────┐     │
        │  │  Generated Images                      │     │
        │  │                                        │     │
        │  │  /images/                              │     │
        │  │    └─ 2024-02-07/                      │     │
        │  │         └─ uuid-123.png                │     │
        │  │         └─ uuid-456.png                │     │
        │  │                                        │     │
        │  │  Features:                             │     │
        │  │  - Versioning enabled                  │     │
        │  │  - Lifecycle policy (30 days)          │     │
        │  │  - Presigned URLs (1 hour expiry)      │     │
        │  └────────────────────────────────────────┘     │
        │                                                 │
        │  6. Generate presigned URL                      │
        └───────────────────┬─────────────────────────────┘
                            │
                            │ 7. Return URL to user
                            │
                            ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                      Amazon QuickSight Q Suite                              │
│                                                                             │
│  ┌───────────────────────────────────────────────────────────────────────┐  │
│  │  Response to User:                                                    │  │
│  │                                                                       │  │
│  │  "I've generated your image! You can view it here:                    │  │
│  │   https://agentcore-generated-images.s3.amazonaws.com/...?X-Amz-..."  │  │
│  │                                                                       │  │
│  │  [Image Preview]                                                      │  │
│  └───────────────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────────────┘
```

## Detailed Component Interaction Flow

### 1. Request Flow (Happy Path)

```
User → Q Suite Agent → MCP Server → Guardrail → Bedrock → S3 → User
```

**Step-by-step:**

1. **User Input**: User types prompt in Q Suite chat
2. **Agent Processing**: Q Suite agent identifies image generation intent
3. **MCP Invocation**: Agent calls MCP server's `generate_image` tool
4. **Guardrail Check**: MCP server validates prompt with Bedrock Guardrails
5. **Content Generation**: If approved, Bedrock model generates image
6. **S3 Storage**: Image uploaded to S3 bucket
7. **URL Generation**: Presigned URL created with 1-hour expiry
8. **Response**: URL returned to user via Q Suite

### 2. Blocked Content Flow

```
User → Q Suite Agent → MCP Server → Guardrail ✗ → Error Response → User
```

**Step-by-step:**

1. **User Input**: User requests inappropriate content
2. **Agent Processing**: Q Suite agent calls MCP server
3. **Guardrail Check**: Guardrail detects policy violation
4. **Block Action**: Request blocked before reaching Bedrock
5. **Error Response**: Friendly error message returned
6. **User Notification**: Q Suite displays blocked message

### 3. Error Handling Flow

```
User → Q Suite Agent → MCP Server → [Error] → Retry/Fallback → User
```

**Possible errors:**
- Guardrail service unavailable
- Bedrock model throttling
- S3 upload failure
- Network timeout

## Component Details

### MCP Server Components

```
┌─────────────────────────────────────────────────────────────┐
│                    MCP Server Architecture                  │
│                                                             │
│  ┌─────────────────────────────────────────────────────┐    │
│  │  server.py (Main Entry Point)                       │    │
│  │  - FastAPI application                              │    │ 
│  │  - MCP protocol handler                             │    │
│  │  - Request routing                                  │    │
│  │  - Error handling                                   │    │
│  └────────────────┬────────────────────────────────────┘    │
│                   │                                         │
│       ┌───────────┼───────────┐                             │
│       │           │           │                             │
│       ▼           ▼           ▼                             │
│  ┌─────────┐ ┌─────────┐ ┌─────────┐                        │
│  │Guardrail│ │ Bedrock │ │   S3    │                        │
│  │ Client  │ │ Client  │ │ Client  │                        │
│  │         │ │         │ │         │                        │
│  │- Check  │ │- Invoke │ │- Upload │                        │
│  │  prompt │ │  model  │ │  image  │                        │ 
│  │- Return │ │- Handle │ │- Create │                        │
│  │  result │ │  stream │ │  URL    │                        │
│  └─────────┘ └─────────┘ └─────────┘                        │
│                                                             │
│  ┌─────────────────────────────────────────────────────┐    │
│  │  utils.py (Helper Functions)                        │    │
│  │  - Image processing                                 │    │ 
│  │  - Logging                                          │    │
│  │  - Metrics                                          │    │
│  └─────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────┘
```

### AWS IAM Permissions Flow

```
┌─────────────────────────────────────────────────────────────┐
│                  IAM Role: AgentcoreImageGenRole            │
│                                                             │
│  Trusted Entity: agentcore.amazonaws.com                    │
│                                                             │
│  Attached Policies:                                         │
│  ┌─────────────────────────────────────────────────────┐    │
│  │  AgentcoreImageGenPolicy                            │    │
│  │                                                     │    │
│  │  Permissions:                                       │    │
│  │  ├─ bedrock:InvokeModel                             │    │ 
│  │  ├─ bedrock:ApplyGuardrail                          │    │
│  │  ├─ s3:PutObject                                    │    │
│  │  ├─ s3:GetObject                                    │    │
│  │  └─ logs:CreateLogStream, PutLogEvents              │    │
│  └─────────────────────────────────────────────────────┘    │
│                                                             │
│  Used by:                                                   │
│  - Agentcore Runtime container                              │
│  - MCP Server application                                   │
└─────────────────────────────────────────────────────────────┘
```

### Data Flow Diagram

```
┌──────────┐
│  User    │
│  Prompt  │
└────┬─────┘
     │
     │ "Generate a sunset image"
     │
     ▼
┌─────────────────┐
│  Q Suite Agent  │
│                 │
│  Parses intent  │
│  Extracts params│
└────┬────────────┘
     │
     │ MCP Request:
     │ {
     │   "tool": "generate_image",
     │   "prompt": "sunset",
     │   "model": "stability"
     │ }
     │
     ▼
┌─────────────────────────────────────────┐
│  MCP Server                             │
│                                         │
│  1. Receive request                     │
│  2. Log request                         │
│  3. Validate parameters                 │
└────┬────────────────────────────────────┘
     │
     │ Guardrail Request:
     │ {
     │   "text": "sunset",
     │   "guardrailId": "xxx",
     │   "guardrailVersion": "1"
     │ }
     │
     ▼
┌─────────────────────────────────────────┐
│  Bedrock Guardrails                     │
│                                         │
│  1. Analyze prompt                      │
│  2. Check content filters               │
│  3. Check topic policies                │
│  4. Return decision                     │
└────┬────────────────────────────────────┘
     │
     │ Decision: APPROVED
     │
     ▼
┌─────────────────────────────────────────┐
│  Bedrock Model (Stability AI)           │
│                                         │
│  1. Process prompt                      │
│  2. Generate image                      │
│  3. Return base64 encoded image         │
└────┬────────────────────────────────────┘
     │
     │ Image Data:
     │ {
     │   "image": "base64_encoded_data",
     │   "format": "png"
     │ }
     │
     ▼
┌─────────────────────────────────────────┐
│  S3 Client                              │
│                                         │
│  1. Decode base64                       │
│  2. Upload to S3                        │
│  3. Generate presigned URL              │
└────┬────────────────────────────────────┘
     │
     │ S3 URL:
     │ https://bucket.s3.amazonaws.com/
     │ image.png?X-Amz-Signature=...
     │
     ▼
┌─────────────────────────────────────────┐
│  MCP Server Response                    │
│                                         │
│  {                                      │
│    "success": true,                     │
│    "image_url": "https://...",          │
│    "expires_in": 3600,                  │
│    "model_used": "stability"            │
│  }                                      │
└────┬────────────────────────────────────┘
     │
     ▼
┌─────────────────┐
│  Q Suite Agent  │
│                 │
│  Formats        │
│  response       │
└────┬────────────┘
     │
     ▼
┌──────────┐
│   User   │
│  Receives│
│   URL    │
└──────────┘
```

## Security Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Security Layers                          │
│                                                             │
│  Layer 1: Network Security                                  │
│  ┌─────────────────────────────────────────────────────┐    │
│  │  - VPC with private subnets                         │    │
│  │  - Security groups (port 8080 only)                 │    │
│  │  - No public internet access                        │    │ 
│  │  - VPC endpoints for AWS services                   │    │
│  └─────────────────────────────────────────────────────┘    │
│                                                             │
│  Layer 2: IAM Security                                      │
│  ┌─────────────────────────────────────────────────────┐    │
│  │  - Least privilege policies                         │    │
│  │  - Role-based access control                        │    │
│  │  - No long-term credentials                         │    │
│  │  - Temporary session tokens                         │    │
│  └─────────────────────────────────────────────────────┘    │
│                                                             │
│  Layer 3: Content Security (Guardrails)                     │
│  ┌─────────────────────────────────────────────────────┐    │
│  │  - Input validation                                 │    │ 
│  │  - Content filtering                                │    │
│  │  - Topic policies                                   │    │
│  │  - Blocked content logging                          │    │
│  └─────────────────────────────────────────────────────┘    │
│                                                             │
│  Layer 4: Data Security                                     │
│  ┌─────────────────────────────────────────────────────┐    │
│  │  - S3 encryption at rest (AES-256)                  │    │
│  │  - TLS 1.2+ for data in transit                     │    │
│  │  - Presigned URLs with expiry                       │    │
│  │  - No public bucket access                          │    │ 
│  └─────────────────────────────────────────────────────┘    │
│                                                             │
│  Layer 5: Monitoring & Audit                                │
│  ┌─────────────────────────────────────────────────────┐    │
│  │  - CloudWatch logs                                  │    │ 
│  │  - CloudTrail audit logs                            │    │ 
│  │  - Metrics and alarms                               │    │
│  │  - Security Hub integration                         │    │
│  └─────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────┘
```

## Scalability Architecture

```
┌─────────────────────────────────────────────────────────────┐
│              Scalability Considerations                     │
│                                                             │
│  ┌─────────────────────────────────────────────────────┐    │
│  │  Load Balancing                                     │    │
│  │  - Application Load Balancer                        │    │
│  │  - Multiple Agentcore Runtime instances             │    │
│  │  - Auto-scaling based on CPU/memory                 │    │
│  └─────────────────────────────────────────────────────┘    │
│                                                             │
│  ┌─────────────────────────────────────────────────────┐    │
│  │  Caching Layer (Optional)                           │    │
│  │  - ElastiCache Redis                                │    │
│  │  - Cache repeated prompts                           │    │
│  │  - TTL: 24 hours                                    │    │
│  └─────────────────────────────────────────────────────┘    │
│                                                             │
│  ┌─────────────────────────────────────────────────────┐    │
│  │  Async Processing (Future)                          │    │
│  │  - SQS queue for requests                           │    │
│  │  - Lambda workers for generation                    │    │
│  │  - SNS notifications on completion                  │    │
│  └─────────────────────────────────────────────────────┘    │
│                                                             │
│  ┌─────────────────────────────────────────────────────┐    │
│  │  Storage Optimization                               │    │
│  │  - S3 Intelligent-Tiering                           │    │
│  │  - CloudFront CDN for delivery                      │    │
│  │  - Image compression                                │    │
│  └─────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────┘
```

## Monitoring Dashboard Layout

```
┌─────────────────────────────────────────────────────────────┐
│              CloudWatch Dashboard                           │
│                                                             │
│  ┌──────────────────┐  ┌──────────────────┐                 │
│  │  Request Count   │  │  Success Rate    │                 │
│  │                  │  │                  │                 │
│  │  [Line Graph]    │  │  [Gauge: 98.5%]  │                 │
│  └──────────────────┘  └──────────────────┘                 │
│                                                             │
│  ┌──────────────────┐  ┌──────────────────┐                 │
│  │ Guardrail Blocks │  │  Avg Latency     │                 │
│  │                  │  │                  │                 │
│  │  [Bar Chart]     │  │  [Line: 2.3s]    │                 │
│  └──────────────────┘  └──────────────────┘                 │
│                                                             │
│  ┌──────────────────┐  ┌──────────────────┐                 │
│  │  S3 Upload Rate  │  │  Error Rate      │                 │ 
│  │                  │  │                  │                 │ 
│  │  [Line Graph]    │  │  [Gauge: 1.5%]   │                 │
│  └──────────────────┘  └──────────────────┘                 │
│                                                             │
│  ┌─────────────────────────────────────────────────────┐    │
│  │  Recent Errors                                      │    │
│  │  - 2024-02-07 10:23: S3 upload timeout              │    │
│  │  - 2024-02-07 10:15: Guardrail blocked request      │    │
│  └─────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────┘
```

## Cost Breakdown

```
┌─────────────────────────────────────────────────────────────┐
│                    Monthly Cost Estimate                    │
│                    (1000 images/month)                      │
│                                                             │
│  Service                          Cost                      │
│  ───────────────────────────────────────────────────────────│
│  AWS Bedrock (Stability AI)       $40.00                    │
│  AWS Agentcore Runtime            $25.00                    │
│  Amazon S3 Storage                $2.30                     │
│  S3 Data Transfer                 $9.00                     │
│  CloudWatch Logs                  $5.00                     │
│  Bedrock Guardrails               $15.00                    │
│  ─────────────────────────────────────────────────────────  │
│  Total                            $96.30/month              │
│                                                             │
│  Per Image Cost: ~$0.096                                    │
└─────────────────────────────────────────────────────────────┘
```

This architecture provides a secure, scalable, and cost-effective solution for generating images with content safety guardrails integrated into Amazon QuickSight Q Suite.
