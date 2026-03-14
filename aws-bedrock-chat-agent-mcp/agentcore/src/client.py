import boto3
import json
from typing import Optional, Dict, Any
from botocore.exceptions import ClientError

# Initialize the Bedrock AgentCore client
client = boto3.client("bedrock-agentcore", region_name="us-east-1")

# Your AgentCore Runtime ARN
runtime_arn = "arn:aws:bedrock-agentcore:us-east-1:<account-id>:runtime/<runtime-id>"


def call_mcp(method: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    Call an MCP JSON-RPC method on the agent runtime.

    Args:
        method: MCP method name (e.g., 'tools/list', 'tools/call')
        params: Optional params dict

    Returns:
        Parsed JSON response (dict)
    """
    payload = json.dumps(
        {
            "jsonrpc": "2.0",
            "id": "1",
            "method": method,
            "params": params or {},
        }
    ).encode("utf-8")

    try:
        response = client.invoke_agent_runtime(
            agentRuntimeArn=runtime_arn,
            payload=payload,
            qualifier="DEFAULT",
            contentType="application/json",
            accept="application/json",
        )

        raw = response["response"].read().decode("utf-8", errors="replace")

        print("\n=== RAW RESPONSE ===")
        print(raw)
        print("=== /RAW RESPONSE ===\n")

        # AgentCore sometimes returns SSE or extra text; parse JSON from first '{'
        json_text = raw[raw.find("{") :]
        return json.loads(json_text)

    except ClientError as e:
        print("\n" + "=" * 60)
        print("Boto ClientError:")
        print(json.dumps(e.response, indent=2, default=str))
        print("=" * 60 + "\n")
        raise


def main():
    # 1) List available tools
    print("=== tools/list ===")
    tools_resp = call_mcp("tools/list")

    if "error" in tools_resp:
        print("tools/list failed:")
        print(json.dumps(tools_resp, indent=2))
        return

    tools = tools_resp.get("result", {}).get("tools", [])
    print("Tools found:", [t.get("name") for t in tools])

    # 2) Call generate_image tool
    print("\n=== tools/call generate_image ===")
    call_resp = call_mcp(
        "tools/call",
        {
            "name": "generate_image",
            "arguments": {
                "prompt": "A cute robot holding a coffee mug, studio lighting, high detail",
                "model": "stability",   # or "titan"
                "width": 1024,
                "height": 1024,
                "user_id": "test-user",
            },
        },
    )

    if "error" in call_resp:
        print("generate_image call failed:")
        print(json.dumps(call_resp, indent=2))
        return

    print("generate_image response:")
    print(json.dumps(call_resp.get("result", {}), indent=2))


if __name__ == "__main__":
    main()
