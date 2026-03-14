# Testing Guide

Comprehensive testing guide for the MCP Image Generator.

## Test Categories

1. Unit Tests
2. Integration Tests
3. End-to-End Tests
4. Load Tests
5. Security Tests

## Running Tests

### Unit Tests

```bash
# Run all tests
pytest tests/ -v

# Run with coverage
pytest tests/ --cov=src --cov-report=html

# Run specific test file
pytest tests/test_server.py -v

# Run specific test
pytest tests/test_server.py::test_generate_image_success -v
```

### Integration Tests

```bash
# Start the server
docker-compose up -d

# Wait for server to be ready
sleep 10

# Run integration tests
python tests/integration_tests.py
```

## Manual Testing

### 1. Health Check Tests

```bash
# Basic health check
curl http://localhost:8080/

# Detailed health check
curl http://localhost:8080/health | jq
```

Expected response:
```json
{
  "status": "healthy",
  "timestamp": "2024-02-07T10:00:00",
  "services": {
    "bedrock": "healthy",
    "s3": "healthy",
    "guardrail": "healthy"
  }
}
```

### 2. MCP Protocol Tests

```bash
# List available tools
curl -X POST http://localhost:8080/mcp/tools/list | jq

# Call generate_image tool
curl -X POST http://localhost:8080/mcp/tools/call \
  -H "Content-Type: application/json" \
  -d '{
    "name": "generate_image",
    "arguments": {
      "prompt": "A peaceful garden with colorful flowers",
      "model": "stability",
      "width": 1024,
      "height": 1024
    }
  }' | jq
```

### 3. Image Generation Tests

#### Test Case 1: Basic Generation (Stability AI)

```bash
curl -X POST http://localhost:8080/generate \
  -H "Content-Type: application/json" \
  -d '{
    "prompt": "A serene mountain landscape at sunset with snow-capped peaks",
    "model": "stability",
    "width": 1024,
    "height": 1024,
    "style": "photographic"
  }' | jq
```

#### Test Case 2: Basic Generation (Titan)

```bash
curl -X POST http://localhost:8080/generate \
  -H "Content-Type: application/json" \
  -d '{
    "prompt": "A futuristic city with flying cars and neon lights",
    "model": "titan",
    "width": 1024,
    "height": 1024
  }' | jq
```

#### Test Case 3: Different Styles (Stability AI)

```bash
# Photographic style
curl -X POST http://localhost:8080/generate \
  -H "Content-Type: application/json" \
  -d '{
    "prompt": "A professional portrait of a business person",
    "model": "stability",
    "style": "photographic"
  }' | jq

# Digital art style
curl -X POST http://localhost:8080/generate \
  -H "Content-Type: application/json" \
  -d '{
    "prompt": "A fantasy dragon in a mystical forest",
    "model": "stability",
    "style": "digital-art"
  }' | jq

# Cinematic style
curl -X POST http://localhost:8080/generate \
  -H "Content-Type: application/json" \
  -d '{
    "prompt": "A dramatic scene of a hero standing on a cliff",
    "model": "stability",
    "style": "cinematic"
  }' | jq
```

#### Test Case 4: Different Dimensions

```bash
# Square image
curl -X POST http://localhost:8080/generate \
  -H "Content-Type: application/json" \
  -d '{
    "prompt": "A beautiful sunset",
    "model": "stability",
    "width": 1024,
    "height": 1024
  }' | jq

# Landscape image
curl -X POST http://localhost:8080/generate \
  -H "Content-Type: application/json" \
  -d '{
    "prompt": "A wide panoramic view of mountains",
    "model": "stability",
    "width": 1024,
    "height": 768
  }' | jq

# Portrait image
curl -X POST http://localhost:8080/generate \
  -H "Content-Type: application/json" \
  -d '{
    "prompt": "A tall skyscraper reaching into the clouds",
    "model": "stability",
    "width": 768,
    "height": 1024
  }' | jq
```

### 4. Guardrail Tests

#### Test Case 1: Violence (Should be blocked)

```bash
curl -X POST http://localhost:8080/generate \
  -H "Content-Type: application/json" \
  -d '{
    "prompt": "A violent battle scene with weapons",
    "model": "stability"
  }' | jq
```

Expected response:
```json
{
  "success": false,
  "error": "Content blocked by guardrail",
  "message": "I cannot generate images with violent, adult, or obscene content. Please provide a different request."
}
```

#### Test Case 2: Adult Content (Should be blocked)

```bash
curl -X POST http://localhost:8080/generate \
  -H "Content-Type: application/json" \
  -d '{
    "prompt": "Explicit adult content",
    "model": "stability"
  }' | jq
```

#### Test Case 3: Obscene Content (Should be blocked)

```bash
curl -X POST http://localhost:8080/generate \
  -H "Content-Type: application/json" \
  -d '{
    "prompt": "Disturbing and grotesque imagery",
    "model": "stability"
  }' | jq
```

#### Test Case 4: Safe Content (Should pass)

```bash
curl -X POST http://localhost:8080/generate \
  -H "Content-Type: application/json" \
  -d '{
    "prompt": "A happy family having a picnic in the park",
    "model": "stability"
  }' | jq
```

### 5. Error Handling Tests

#### Test Case 1: Missing Prompt

```bash
curl -X POST http://localhost:8080/generate \
  -H "Content-Type: application/json" \
  -d '{
    "model": "stability"
  }' | jq
```

Expected: 422 Validation Error

#### Test Case 2: Invalid Model

```bash
curl -X POST http://localhost:8080/generate \
  -H "Content-Type: application/json" \
  -d '{
    "prompt": "A sunset",
    "model": "invalid_model"
  }' | jq
```

#### Test Case 3: Invalid Dimensions

```bash
curl -X POST http://localhost:8080/generate \
  -H "Content-Type: application/json" \
  -d '{
    "prompt": "A sunset",
    "model": "stability",
    "width": 100,
    "height": 100
  }' | jq
```

Expected: Validation error or adjusted dimensions

#### Test Case 4: Malformed JSON

```bash
curl -X POST http://localhost:8080/generate \
  -H "Content-Type: application/json" \
  -d '{invalid json}' | jq
```

Expected: 422 JSON Parse Error

### 6. S3 Integration Tests

```bash
# Generate an image
RESPONSE=$(curl -s -X POST http://localhost:8080/generate \
  -H "Content-Type: application/json" \
  -d '{
    "prompt": "A test image",
    "model": "stability"
  }')

# Extract image URL
IMAGE_URL=$(echo $RESPONSE | jq -r '.image_url')

# Download the image
curl -o test_image.png "$IMAGE_URL"

# Verify image file
file test_image.png
# Expected: PNG image data

# Check image size
ls -lh test_image.png
```

## Load Testing

### Using Apache Bench

```bash
# Install Apache Bench
# Ubuntu: sudo apt-get install apache2-utils
# Mac: brew install httpd

# Simple load test (10 requests, 2 concurrent)
ab -n 10 -c 2 -p request.json -T application/json \
  http://localhost:8080/generate

# Create request.json
cat > request.json << 'EOF'
{
  "prompt": "A simple test image",
  "model": "stability"
}
EOF
```

### Using Python Script

```python
import asyncio
import aiohttp
import time

async def generate_image(session, prompt):
    url = "http://localhost:8080/generate"
    payload = {
        "prompt": prompt,
        "model": "stability"
    }
    
    start = time.time()
    async with session.post(url, json=payload) as response:
        result = await response.json()
        duration = time.time() - start
        return duration, result["success"]

async def load_test(num_requests=10):
    async with aiohttp.ClientSession() as session:
        tasks = [
            generate_image(session, f"Test image {i}")
            for i in range(num_requests)
        ]
        results = await asyncio.gather(*tasks)
        
        durations = [r[0] for r in results]
        successes = sum(1 for r in results if r[1])
        
        print(f"Total requests: {num_requests}")
        print(f"Successful: {successes}")
        print(f"Failed: {num_requests - successes}")
        print(f"Avg duration: {sum(durations)/len(durations):.2f}s")
        print(f"Min duration: {min(durations):.2f}s")
        print(f"Max duration: {max(durations):.2f}s")

if __name__ == "__main__":
    asyncio.run(load_test(10))
```

## Security Testing

### 1. Test Authentication (if enabled)

```bash
# Without credentials (should fail)
curl -X POST http://localhost:8080/generate \
  -H "Content-Type: application/json" \
  -d '{"prompt": "test"}'

# With invalid credentials (should fail)
curl -X POST http://localhost:8080/generate \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer invalid_token" \
  -d '{"prompt": "test"}'
```

### 2. Test Input Validation

```bash
# SQL injection attempt
curl -X POST http://localhost:8080/generate \
  -H "Content-Type: application/json" \
  -d '{
    "prompt": "test; DROP TABLE users;--",
    "model": "stability"
  }'

# XSS attempt
curl -X POST http://localhost:8080/generate \
  -H "Content-Type: application/json" \
  -d '{
    "prompt": "<script>alert(\"XSS\")</script>",
    "model": "stability"
  }'

# Command injection attempt
curl -X POST http://localhost:8080/generate \
  -H "Content-Type: application/json" \
  -d '{
    "prompt": "test && rm -rf /",
    "model": "stability"
  }'
```

### 3. Test Rate Limiting (if enabled)

```bash
# Send many requests quickly
for i in {1..100}; do
  curl -X POST http://localhost:8080/generate \
    -H "Content-Type: application/json" \
    -d '{"prompt": "test", "model": "stability"}' &
done
wait
```

## Monitoring Tests

### 1. Check CloudWatch Logs

```bash
# View recent logs
aws logs tail /aws/agentcore/mcp-image-generator --follow

# Search for errors
aws logs filter-log-events \
  --log-group-name /aws/agentcore/mcp-image-generator \
  --filter-pattern "ERROR"
```

### 2. Check CloudWatch Metrics

```bash
# Get metric statistics
aws cloudwatch get-metric-statistics \
  --namespace MCP/ImageGenerator \
  --metric-name ImagesGenerated \
  --start-time 2024-02-07T00:00:00Z \
  --end-time 2024-02-07T23:59:59Z \
  --period 3600 \
  --statistics Sum
```

## Test Automation

### GitHub Actions Workflow

```yaml
name: Test MCP Image Generator

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    
    steps:
    - uses: actions/checkout@v2
    
    - name: Set up Python
      uses: actions/setup-python@v2
      with:
        python-version: 3.11
    
    - name: Install dependencies
      run: |
        pip install -r requirements.txt
        pip install pytest pytest-cov
    
    - name: Run tests
      run: pytest tests/ --cov=src --cov-report=xml
    
    - name: Upload coverage
      uses: codecov/codecov-action@v2
```

## Test Checklist

- [ ] All unit tests pass
- [ ] Health check returns healthy
- [ ] Can generate images with Stability AI
- [ ] Can generate images with Titan
- [ ] Guardrail blocks violent content
- [ ] Guardrail blocks adult content
- [ ] Guardrail blocks obscene content
- [ ] Guardrail allows safe content
- [ ] Images are uploaded to S3
- [ ] Presigned URLs work
- [ ] Images can be downloaded
- [ ] Error handling works correctly
- [ ] Input validation works
- [ ] MCP protocol endpoints work
- [ ] Load test passes (10 concurrent requests)
- [ ] Security tests pass
- [ ] CloudWatch logs are generated
- [ ] CloudWatch metrics are recorded

## Troubleshooting Test Failures

### Server won't start
- Check environment variables
- Verify AWS credentials
- Check Docker logs: `docker-compose logs`

### Guardrail tests failing
- Verify GUARDRAIL_ID is set
- Check guardrail configuration in AWS console
- Review CloudWatch logs for guardrail errors

### Image generation failing
- Verify Bedrock model access is enabled
- Check IAM permissions
- Review Bedrock service quotas

### S3 upload failing
- Verify S3_BUCKET exists
- Check IAM permissions for S3
- Verify bucket policy

### Tests timing out
- Increase timeout values
- Check network connectivity
- Verify AWS service availability
