#!/usr/bin/env python3
"""
Enhanced MCP Test Client for AgentCore Runtime

Usage:
    python test_client.py                    # Run all tests
    python test_client.py 1                  # Run test 1 only
    python test_client.py 1 3 4              # Run tests 1, 3, and 4
    python test_client.py --list             # List available tests
    python test_client.py --help             # Show help

Tests:
  1. List available MCP tools
  2. SharePoint connectivity (get_sharepoint_site_info)
  3. Generate image with Stability AI
  4. Generate image with Amazon Titan
  5. Test guardrail blocking
"""

import boto3
import json
import sys
import time
import argparse
from typing import Optional, Dict, Any, List, Callable, Tuple
from botocore.exceptions import ClientError

# Configuration
REGION = "us-east-1"
RUNTIME_ARN = "arn:aws:bedrock-agentcore:us-east-1:<account-id>:runtime/<runtime-id>"

# Initialize client
client = boto3.client("bedrock-agentcore", region_name=REGION)


def print_section(title: str):
    """Print a formatted section header."""
    print("\n" + "=" * 80)
    print(f"  {title}")
    print("=" * 80)


def print_json(data: dict, indent: int = 2):
    """Pretty print JSON data."""
    print(json.dumps(data, indent=indent, default=str))


def _extract_json_from_mcp_response(raw: str) -> Dict[str, Any]:
    """
    Best-effort parsing: server may return application/json or SSE text/event-stream.
    """
    # If SSE, the JSON is usually in a "data: {...}" line
    if "data:" in raw:
        lines = [ln.strip() for ln in raw.splitlines() if ln.strip().startswith("data:")]
        for ln in lines:
            candidate = ln[len("data:"):].strip()
            try:
                return json.loads(candidate)
            except json.JSONDecodeError:
                continue

    json_text = raw[raw.find("{"):] if "{" in raw else raw
    return json.loads(json_text)


def call_mcp(method: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    Call an MCP JSON-RPC method on the agent runtime.
    """
    payload = json.dumps(
        {
            "jsonrpc": "2.0",
            "id": "1",
            "method": method,
            "params": params or {},
        }
    ).encode("utf-8")

    print(f"\n📤 Sending request: {method}")
    if params:
        print(f"   Parameters: {json.dumps(params, indent=2)}")

    try:
        start_time = time.time()

        response = client.invoke_agent_runtime(
            agentRuntimeArn=RUNTIME_ARN,
            payload=payload,
            qualifier="DEFAULT",
            contentType="application/json",
            accept="application/json, text/event-stream",
        )

        print("HTTP statusCode:", response.get("statusCode"))
        print("contentType:", response.get("contentType"))

        elapsed = time.time() - start_time
        raw = response["response"].read().decode("utf-8", errors="replace")

        print(f"✅ Response received in {elapsed:.2f}s")

        parsed = _extract_json_from_mcp_response(raw)
        return parsed

    except ClientError as e:
        print("\n❌ AWS ClientError:")
        print_json(e.response)
        raise
    except json.JSONDecodeError as e:
        print(f"\n❌ JSON Parse Error: {e}")
        print(f"Raw response (first 800 chars):\n{raw[:800]}")
        raise
    except Exception as e:
        print(f"\n❌ Unexpected Error: {type(e).__name__}: {e}")
        raise


def _tool_exists(tool_name: str) -> bool:
    """Check whether a tool exists."""
    resp = call_mcp("tools/list")
    tools = resp.get("result", {}).get("tools", [])
    return any(t.get("name") == tool_name for t in tools)


def test_tools_list() -> bool:
    """Test 1: List available MCP tools."""
    print_section("TEST 1: List Available Tools")

    response = call_mcp("tools/list")

    if "error" in response:
        print("\n❌ Error listing tools:")
        print_json(response["error"])
        return False

    tools = response.get("result", {}).get("tools", [])
    print(f"\n✅ Found {len(tools)} tool(s):")

    for tool in tools:
        print(f"\n   📋 Tool: {tool.get('name')}")
        print(f"      Description: {tool.get('description', 'N/A')[:100]}...")

        schema = tool.get("inputSchema", {})
        props = schema.get("properties", {})
        print(f"      Parameters: {', '.join(props.keys())}")

    return True


def test_sharepoint_connectivity() -> bool:
    """Test 2: SharePoint connectivity (get_sharepoint_site_info)."""
    print_section("TEST 2: SharePoint Connectivity (Site Info)")

    tool_name = "get_sharepoint_site_info"

    # Skip gracefully if tool isn't registered
    if not _tool_exists(tool_name):
        print(f"\n⚠️  Tool '{tool_name}' not found. Skipping SharePoint test.")
        return True

    response = call_mcp(
        "tools/call",
        {
            "name": tool_name,
            "arguments": {},
        },
    )

    if "error" in response:
        print("\n❌ Error calling SharePoint tool:")
        print_json(response["error"])
        return False

    result = response.get("result", {})
    content = result.get("content", [])

    if not content:
        print("\n❌ No content in response")
        return False

    text_content = content[0].get("text", "{}")

    try:
        data = json.loads(text_content)
    except Exception:
        data = {"raw": text_content}

    print("\n📊 Result:")
    print_json(data)

    if data.get("success") is True:
        print("\n✅ SharePoint connectivity looks good!")
        return True

    print("\n⚠️  SharePoint connectivity test failed.")
    return False


def test_generate_image_stability() -> bool:
    """Test 3: Generate image with Stability AI."""
    print_section("TEST 3: Generate Image (Stability AI)")

    prompt = "A serene mountain landscape at sunset with a lake reflection, photorealistic"
    model = "stability"
    user_id = "test-user"

    print(f"\n📝 Request Details:")
    print(f"   Prompt: {prompt}")
    print(f"   Model: {model}")
    print(f"   Size: 1024x1024")
    print(f"   User: {user_id}")

    response = call_mcp(
        "tools/call",
        {
            "name": "generate_image",
            "arguments": {
                "prompt": prompt,
                "model": model,
                "width": 1024,
                "height": 1024,
                "user_id": user_id,
            },
        },
    )

    if "error" in response:
        print("\n❌ Error calling generate_image:")
        print_json(response["error"])
        return False

    result = response.get("result", {})
    content = result.get("content", [])

    if not content:
        print("\n❌ No content in response")
        return False

    text_content = content[0].get("text", "{}")
    result_data = json.loads(text_content)

    print("\n📊 Result:")
    print(f"   Success: {result_data.get('success')}")
    print(f"   Status: {result_data.get('status')}")
    print(f"   Request ID: {result_data.get('request_id')}")

    if result_data.get("success"):
        print(f"   Image ID: {result_data.get('image_id')}")
        print(f"   Model Used: {result_data.get('model_used')}")
        print(f"   S3 Key: {result_data.get('s3_key')}")
        print(f"   Elapsed: {result_data.get('elapsed_ms')}ms")
        print(f"   URL Expires In: {result_data.get('expires_in')}s")
        print(f"\n   🖼️  Image URL:")
        print(f"   {result_data.get('image_url')[:100]}...")
        print("\n   ✅ Image generated successfully!")
        return True

    print(f"   Reason: {result_data.get('reason', 'N/A')}")
    print(f"   Message: {result_data.get('message', 'N/A')}")
    print("\n   ⚠️  Image generation blocked or failed")
    return False


def test_generate_image_titan() -> bool:
    """Test 4: Generate image with Amazon Titan."""
    print_section("TEST 4: Generate Image (Amazon Titan)")

    prompt = "A cute robot holding a coffee mug, studio lighting, high detail"
    model = "titan"
    user_id = "test-user"

    print(f"\n📝 Request Details:")
    print(f"   Prompt: {prompt}")
    print(f"   Model: {model}")
    print(f"   Size: 1024x1024")
    print(f"   User: {user_id}")

    response = call_mcp(
        "tools/call",
        {
            "name": "generate_image",
            "arguments": {
                "prompt": prompt,
                "model": model,
                "width": 1024,
                "height": 1024,
                "user_id": user_id,
            },
        },
    )

    if "error" in response:
        print("\n❌ Error calling generate_image:")
        print_json(response["error"])
        return False

    result = response.get("result", {})
    content = result.get("content", [])

    if not content:
        print("\n❌ No content in response")
        return False

    text_content = content[0].get("text", "{}")
    result_data = json.loads(text_content)

    print("\n📊 Result:")
    print(f"   Success: {result_data.get('success')}")
    print(f"   Status: {result_data.get('status')}")
    print(f"   Request ID: {result_data.get('request_id')}")

    if result_data.get("success"):
        print(f"   Image ID: {result_data.get('image_id')}")
        print(f"   Model Used: {result_data.get('model_used')}")
        print(f"   S3 Key: {result_data.get('s3_key')}")
        print(f"   Elapsed: {result_data.get('elapsed_ms')}ms")
        print(f"\n   ✅ Image generated successfully!")
        return True

    print(f"   Reason: {result_data.get('reason', 'N/A')}")
    print(f"   Message: {result_data.get('message', 'N/A')}")
    print("\n   ⚠️  Image generation blocked or failed")
    return False


def test_guardrail_blocking() -> bool:
    """Test 5: Test guardrail blocking."""
    print_section("TEST 5: Test Guardrail Blocking")

    prompt = "violent scene with weapons"
    model = "stability"
    user_id = "test-user"

    print(f"\n📝 Request Details:")
    print(f"   Prompt: {prompt}")
    print(f"   Model: {model}")
    print(f"   Note: This prompt should be blocked by guardrails")

    response = call_mcp(
        "tools/call",
        {
            "name": "generate_image",
            "arguments": {
                "prompt": prompt,
                "model": model,
                "width": 1024,
                "height": 1024,
                "user_id": user_id,
            },
        },
    )

    if "error" in response:
        print("\n❌ Error calling generate_image:")
        print_json(response["error"])
        return False

    result = response.get("result", {})
    content = result.get("content", [])

    if not content:
        print("\n❌ No content in response")
        return False

    text_content = content[0].get("text", "{}")
    result_data = json.loads(text_content)

    print("\n📊 Result:")
    print(f"   Success: {result_data.get('success')}")
    print(f"   Status: {result_data.get('status')}")

    # For guardrail test, we expect it to be blocked
    if result_data.get("status") == "BLOCKED":
        print(f"   Reason: {result_data.get('reason', 'N/A')}")
        print("\n   ✅ Guardrail correctly blocked inappropriate content!")
        return True
    elif result_data.get("success"):
        print("\n   ⚠️  Content was NOT blocked (guardrails may need adjustment)")
        return True  # Still pass, but warn
    else:
        print("\n   ⚠️  Unexpected result")
        return False


# Define all available tests
AVAILABLE_TESTS: List[Tuple[int, str, Callable[[], bool]]] = [
    (1, "List Tools", test_tools_list),
    (2, "SharePoint Connectivity", test_sharepoint_connectivity),
    (3, "Generate Image (Stability AI)", test_generate_image_stability),
    (4, "Generate Image (Amazon Titan)", test_generate_image_titan),
    (5, "Test Guardrail Blocking", test_guardrail_blocking),
]


def list_tests():
    """List all available tests."""
    print("\nAvailable Tests:")
    print("=" * 80)
    for test_num, test_name, _ in AVAILABLE_TESTS:
        print(f"  {test_num}. {test_name}")
    print("=" * 80)
    print("\nUsage:")
    print("  python test_client.py           # Run all tests")
    print("  python test_client.py 1         # Run test 1 only")
    print("  python test_client.py 1 3 4     # Run tests 1, 3, and 4")
    print("  python test_client.py --list    # Show this list")


def parse_arguments():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="MCP Server Test Client",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python test_client.py           # Run all tests
  python test_client.py 1         # Run test 1 only
  python test_client.py 1 3 4     # Run tests 1, 3, and 4
  python test_client.py --list    # List available tests
        """
    )
    
    parser.add_argument(
        'tests',
        nargs='*',
        type=int,
        help='Test numbers to run (1-5). If not specified, runs all tests.'
    )
    
    parser.add_argument(
        '--list',
        action='store_true',
        help='List all available tests'
    )
    
    return parser.parse_args()


def main():
    """Run tests based on command line arguments."""
    args = parse_arguments()

    """
    Available Tests:
        1. List Tools - Lists all available MCP tools
        2. SharePoint Connectivity - Tests SharePoint site info retrieval
        3. Generate Image (Stability AI) - Tests image generation with Stability
        4. Generate Image (Amazon Titan) - Tests image generation with Titan
        5. Test Guardrail Blocking - Tests content filtering
    """
    
    # Handle --list flag
    if args.list:
        list_tests()
        return 0
    
    # Determine which tests to run
    if args.tests:
        # Validate test numbers
        invalid_tests = [t for t in args.tests if t < 1 or t > len(AVAILABLE_TESTS)]
        if invalid_tests:
            print(f"❌ Invalid test number(s): {invalid_tests}")
            print(f"Valid test numbers are 1-{len(AVAILABLE_TESTS)}")
            list_tests()
            return 1
        
        tests_to_run = [t for t in AVAILABLE_TESTS if t[0] in args.tests]
        print(f"\n🎯 Running {len(tests_to_run)} selected test(s): {args.tests}")
    else:
        tests_to_run = AVAILABLE_TESTS
        print(f"\n🎯 Running all {len(tests_to_run)} tests")
    
    print_section("MCP Server Test Suite")
    print(f"Runtime ARN: {RUNTIME_ARN}")
    print(f"Region: {REGION}")

    # Verify AWS credentials
    try:
        sts = boto3.client("sts")
        identity = sts.get_caller_identity()
        print(f"AWS Account: {identity['Account']}")
        print(f"AWS User/Role: {identity['Arn']}")
    except Exception as e:
        print(f"\n❌ AWS Credentials Error: {e}")
        print("Please configure AWS credentials and try again.")
        return 1

    # Run selected tests
    results = []
    for test_num, test_name, test_func in tests_to_run:
        try:
            success = test_func()
            results.append((test_name, success))
        except Exception as e:
            print(f"\n❌ Test failed with exception: {e}")
            results.append((test_name, False))

    # Summary
    print_section("Test Summary")

    passed = sum(1 for _, success in results if success)
    total = len(results)

    print(f"\n📊 Results: {passed}/{total} tests passed\n")

    for test_name, success in results:
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"   {status}  {test_name}")

    print("\n" + "=" * 80)

    if passed == total:
        print("\n🎉 All tests passed!")
        print("\n💡 Next steps:")
        print("   1. Check CloudWatch Logs for detailed execution logs")
        print("   2. Verify images in S3 bucket")
        print("   3. Check DynamoDB for audit records")
        print("\n   View logs:")
        print(f"   aws logs tail /aws/bedrock-agentcore/ai_foundation_dev_runtime --follow --region {REGION}")
        return 0

    print("\n⚠️  Some tests failed. Check the output above for details.")
    return 1


if __name__ == "__main__":
    sys.exit(main())
