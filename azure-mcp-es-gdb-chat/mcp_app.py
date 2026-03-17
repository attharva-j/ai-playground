"""
MCP Server for ChatGPT Integration (Azure Option A - ASGI Mount)

Adds INTENT-AWARE routing:
  - Intent 'qna'      -> GraphDB (Neo4j)
  - Intent 'smartpack'-> ElasticSearch (default), with env-toggles to allow Databricks now/later

Exposes:
  - MCP tools: search (auto), qna (force), smartpack (force), fetch
  - REST:      /api/search (auto / accepts 'intent'), /api/qna, /api/smartpack, /api/fetch
"""
import json
import logging
import os
from dotenv import load_dotenv
from typing import Dict, List, Any, Optional

from fastmcp import FastMCP
from openai import AzureOpenAI,OpenAI
from flask import Flask, request, jsonify, send_file
from io import BytesIO

import warnings
warnings.filterwarnings(
    "ignore",
    category=DeprecationWarning,
    module=r"neo4j\..*",
)
from Mapping.smartpack_entities import ISmartpackEntity, CompanySmartpack, PersonSmartpack
from prompt_injection_detector import is_prompt_injection, explain_prompt_injection

from utils import (
    load_intents,
    sanitize_filename,
    is_empty,
    merge_values,
    merge_dicts,
    build_elasticsearch_query,
    _from_env,
    _get_secrets,
    _strip_code_fences,
    _openai_json_call,
    _classify_intent,
    _get_intent,
    _parse_smartpack_backends,
    _connectors_for_intent,
    _generate_request_for,
    _post_process_with_openai,
    _neo4j_jsonable,
    _coerce_graph_rows,
    _rows_via_connector,
    _gdb_query_safe,
    _graph_schema_context,
    _validate_graph_request_or_error,
    _format_schema_for_prompt,
    _generate_graphdb_request_with_schema,
    _execute_connector,
    download_pdf_from_storage,
    _es,
    _gdb,
    _dbx,
)

load_dotenv()

# -------------------------------
# Env toggles & config path
# -------------------------------
SMARTPACK_BACKENDS = os.getenv("SMARTPACK_BACKENDS", "elastic")  # "elastic" | "databricks" | "elastic,databricks"
SMARTPACK_PRIMARY = os.getenv("SMARTPACK_PRIMARY", "elastic")    # primary to prefer when multiple
CONFIG_PATH = os.path.join(os.path.dirname(__file__), "config", "mcp_config.json")
# Graph schema discovery options
GRAPHDB_SCHEMA_DB = os.getenv("GRAPHDB_SCHEMA_DB", "neo4j")      # which database to introspect
GRAPH_SCHEMA_TTL_SECONDS = int(os.getenv("GRAPH_SCHEMA_TTL_SECONDS", "900"))  # cache 15 min
GRAPH_SCHEMA_MAX_ITEMS = int(os.getenv("GRAPH_SCHEMA_MAX_ITEMS", "500"))      # trim very large schemas in prompt
DEFAULT_LIST_LIMIT = int(os.getenv("DEFAULT_LIST_LIMIT", "100"))



INTENTS_FILE = "config/intents.json"
# -------------------------------
# Logging
# -------------------------------
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

with open(CONFIG_PATH, "r", encoding="utf-8") as _f:
    MCP_CONFIG = json.load(_f)

# Load intents.json for smartpack configuration
INTENTS_CONFIG = "config/intents.json"
try:
    intents_path = os.path.join(os.path.dirname(__file__), INTENTS_FILE)
    if os.path.exists(intents_path):
        with open(intents_path, "r", encoding="utf-8") as _f:
            INTENTS_CONFIG = json.load(_f).get("smartpack")
        logger.info(f"Intents configuration loaded from {intents_path}")
    else:
        logger.warning(f"Intents file not found at {intents_path}")
except Exception as e:
    logger.error(f"Failed to load intents configuration: {e}")

SECRETS = _get_secrets()

# -------------------------------
# OpenAI (Azure) client
# -------------------------------
def _build_openai_client():
    """
    If LOCAL_DEV=true => use OpenAI API key (non-Azure).
    Otherwise => use Azure OpenAI (Azure AI Foundry).
    """
    local_dev_flag = os.getenv("LOCAL_DEV", "false").lower()
    local_dev = local_dev_flag in ("1", "true", "yes")

    if local_dev:
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise RuntimeError("LOCAL_DEV enabled but OPENAI_API_KEY not set.")
        logger.info("LOCAL_DEV enabled: using standard OpenAI client with OPENAI_API_KEY.")
        return OpenAI(api_key=api_key)

    # Otherwise → Azure OpenAI
    api_version = SECRETS.get("API_VERSION")
    endpoint = SECRETS.get("AZ_COGNITIVE_URL")
    key = SECRETS.get("COGNITIVE_SUBSCRIPTION_KEY")

    if not (api_version and endpoint and key):
        raise RuntimeError(
            "Azure OpenAI configuration missing: API_VERSION, AZ_COGNITIVE_URL, COGNITIVE_SUBSCRIPTION_KEY."
        )

    logger.info("LOCAL_DEV disabled: using Azure OpenAI client.")
    return AzureOpenAI(api_version=api_version, azure_endpoint=endpoint, api_key=key)

# Initialize client
try:
    openai_client = _build_openai_client()
except Exception as e:
    logger.error(f"Failed to initialize OpenAI client: {e}")
    openai_client = None

GPT_MODEL_NAME = SECRETS.get("GPT_MODEL_NAME")

server_instructions = MCP_CONFIG.get("server_instructions", (
    "This MCP server provides search and document retrieval capabilities\n"
    "for chat and deep research connectors. Use the search tool to find relevant documents\n"
    "based on keywords, then use the fetch tool to retrieve complete\n"
    "document content with citations."
))

def search_sync(query: str, intent: Optional[str] = None) -> Dict[str, Any]:
    """
    Intent-aware search:
      - Classify/accept intent -> pick allowed connectors -> choose connector
      - Identify second intent, what is user looking for, company SmartPack, Person SmartPack, Person info, etc. (Need to check what are the intents)
      - Extract the json query for intent and connector from config/intents.json
      - Execute query in proper connector (Check the default scenarios and error handling also)
      - Process Database output with OpenAI for reduce the amout of data to return and generate the smartpack or report
    """
    logger.info("***Search API was called***")
    logging_trace: List[Dict[str, Any]] = []
    if not query or not isinstance(query, str) or not query.strip():
        return {"results": [], "intent": intent or "other", "connector": None, "logging": logging_trace}

    # Guardrail: Check for prompt injection attempts
    if is_prompt_injection(query):
        detected_rules = explain_prompt_injection(query)
        logger.warning(f"Potential prompt injection detected in search query. Rules triggered: {detected_rules}")
        return {
            "results": [],
            "intent": intent or "other",
            "connector": None,
            "error": "Request blocked: potential prompt injection detected",
            "detected_rules": detected_rules,
            "logging": logging_trace
        }

    # Verify OpenAI config (needed for intent + request generation)
    if not openai_client or not GPT_MODEL_NAME:
        logger.error(f"OpenAI/Azure configuration not set" + str(GPT_MODEL_NAME))
        return {"error": "OpenAI/Azure configuration not set"}

    # 1) Decide intent (if not forced), need to determine both intents, for connector and action
    classification = _classify_intent(openai_client, GPT_MODEL_NAME, query, MCP_CONFIG)
    try:
        if intent is None:
            intent = _get_intent(classification)
        logging_trace.append({"intent": intent})
    except Exception as e:
        logger.error(f"Intent classification failed: {e}")
        intent = "other"

    # 2) Allowed connectors for this intent
    allowed = _connectors_for_intent(intent)
    intent_for_query = classification.get("baseQuery")
    instance = classification.get("instance")
    logging_trace.append({"allowed_connectors": allowed})
    logging_trace.append({"intent_for_query": intent_for_query})

    # 3) Choose connector
    try:
        connector = allowed[0]
    except Exception as e:
        logger.error(f"Connector selection failed: {e}")
        connector = allowed[0]
    logging_trace.append({"chosen_connector": connector})
    # 4) Generate connector-specific request
    # CHG-0011 change this, instead of generating the query with OpenAI use config intents.json file to pull the proper query
    smartpack_generator: ISmartpackEntity
    try:
        if connector == "graphdb":
            # NEW: schema-aware Cypher generation
            logger.info("Using graphdb connector")
            request_spec = _generate_graphdb_request_with_schema(openai_client, GPT_MODEL_NAME, query, MCP_CONFIG)
            err = _validate_graph_request_or_error(request_spec)
            if err:
                logging.info("Error")
                logging_trace.append({"graph_request_error": err})
                return {
                    "results": [{"connector": connector, "intent": intent, "request": request_spec, "data": err}],
                    "intent": intent, "connector": connector, "logging": logging_trace
                }
        elif intent == "smartpack" and connector == "elasticsearch":
            # Extract company name from query or intent_for_query

            smartpack_cfg = ""
            if intent_for_query == "companySmartpack":
                smartpack_generator = CompanySmartpack()
            else:
                smartpack_generator = PersonSmartpack()
            smartpack_cfg = smartpack_generator.get_smartpack_config(instance, INTENTS_CONFIG)
            print(f"desired config: {smartpack_cfg}")

            if smartpack_cfg and smartpack_cfg.get("indexes"):
                # Build request spec from intents.json configuration
                request_spec = {
                    "operation": "search",
                    "index": smartpack_cfg.get("indexes", ""),
                    "query": smartpack_cfg.get("body", {}).get("query", {})
                }
                logger.info(f"Using smartpack configuration from intents.json for company: {instance} request_spec: {request_spec}")
            else:
                # Fallback to OpenAI generation if config not available
                logger.warning("Smartpack configuration not found, falling back to OpenAI generation")
                request_spec = _generate_request_for(openai_client, GPT_MODEL_NAME, connector, query, MCP_CONFIG)
        else:
            # For other intents, use OpenAI-based generation
            request_spec = _generate_request_for(openai_client, GPT_MODEL_NAME, connector, query, MCP_CONFIG)

        logging_trace.append({"request_spec": request_spec})
    except Exception as e:
        logger.error(f"Request generation failed: {e}")
        request_spec = {}

    # 5) Execute
    # CHG-0011 Execute the process to run the query, I said process cause for some intents we can't run directly the query
    try:
        logger.info(f"Executing request_spec => {request_spec} on connector => {connector}")
        data = _execute_connector(connector, request_spec)
        # logger.info(f"data received from connector: {data}")
    except Exception as e:
        logger.error(f"Connector execution failed: {e}")
        data = {"error": str(e)}

    # ----------------------------
    # Normalize connector output & capture final cypher (for graphdb)
    # ----------------------------
    generated_cypher = None
    # default: assume data is already rows (for ES/databricks) or raw doc
    data_rows_for_post = data

    # If graphdb connector returned our enhanced dict (rows + _generated_cypher), normalize it
    if connector == "graphdb":
        # _execute_connector historically returned list[dict] for graphdb; but recent changes
        # may return {"rows": [...], "_generated_cypher": "..."}.
        if isinstance(data, dict) and "generated_cypher" in data:
            generated_cypher = data.get("generated_cypher")
            data_rows_for_post = data.get("rows", [])
        else:
            # keep backward compatibility: if list was returned, use it directly
            if isinstance(data, list):
                data_rows_for_post = data
            else:
                # if graphdb returned some other shape (e.g., single dict row), wrap appropriately
                data_rows_for_post = data if data is not None else []

    # 6) Post-process with OpenAI to generate summary
    summary = None
    try:
        # For smartpack intent, generate company or person summary
        if intent == "smartpack" and connector == "elasticsearch":
            company_or_person_name = instance
            summary = smartpack_generator.generate_summary(data, company_or_person_name, openai_client, secrets=SECRETS)
            logger.info(f"Company or person summary generated for: {company_or_person_name}")
        else:
            # For other intents, use generic OpenAI post-processing on normalized rows
            summary = _post_process_with_openai(openai_client, GPT_MODEL_NAME, data_rows_for_post, query)

    except Exception as e:
        logger.error(f"Post-processing failed: {e}")
        summary = {"error": f"Post-processing failed: {str(e)}"}

    # 7) Shape response (keep current shape but include intent/connector and summary)
    result_entry = {
        "connector": connector,
        "intent": intent,
        "summary": summary,
        # include the final executed cypher in the API response (None when not available)
        "generated_cypher": generated_cypher
    }
    return {"results": [result_entry]}

def fetch_sync(doc_id: str) -> Dict[str, Any]:
    if not doc_id:
        raise ValueError("Document ID is required")

    # Guardrail: Check for prompt injection attempts in document ID
    if is_prompt_injection(doc_id):
        detected_rules = explain_prompt_injection(doc_id)
        logger.warning(f"Potential prompt injection detected in fetch document ID. Rules triggered: {detected_rules}")
        return {
            "error": "Request blocked: potential prompt injection detected in document ID",
            "detected_rules": detected_rules
        }

    if not openai_client or not GPT_MODEL_NAME:
        logger.error("OpenAI/Azure configuration not set2")
        return {"error": "OpenAI/Azure configuration not set"}

    fetch_cfg = MCP_CONFIG.get("openai", {}).get("fetch_response", {})
    prompt = fetch_cfg.get("prompt", "").format(doc_id=doc_id)
    messages_system = fetch_cfg.get("messages_system", "You are an assistant that generates complete fictitious documents in valid JSON format.")
    temperature = fetch_cfg.get("temperature", 0.7)
    max_tokens = fetch_cfg.get("max_tokens", 1500)

    try:
        response = openai_client.chat.completions.create(
            model=GPT_MODEL_NAME,
            messages=[
                {"role": "system", "content": messages_system},
                {"role": "user", "content": prompt}
            ],
            temperature=temperature,
            max_tokens=max_tokens
        )
        result_text = _strip_code_fences(response.choices[0].message.content or "")
        result = json.loads(result_text)
    except Exception as e:
        logger.error(f"Error generating content with OpenAI: {e}")
        result = {
            "id": doc_id,
            "title": f"Document {doc_id}",
            "text": f"Complete content of the document {doc_id}. This is a fictitious document generated for demonstration purposes.",
            "url": f"https://platform.openai.com/storage/files/{doc_id}",
            "metadata": f"Fictitious document generated for ID {doc_id}"
        }

    return result

# -------------------------------
# MCP Server
# -------------------------------
def create_server():
    mcp = FastMCP(name="Sample MCP Server", instructions=server_instructions)

    @mcp.tool()
    def search(query: str) -> Dict[str, Any]:
        """Auto intent detection and routing across connectors."""
        return search_sync(query)

    @mcp.tool()
    def qna(query: str) -> Dict[str, Any]:
        """QnA over the knowledge graph (Neo4j)."""
        # Guardrail: Check for prompt injection attempts
        if is_prompt_injection(query):
            detected_rules = explain_prompt_injection(query)
            logger.warning(f"Potential prompt injection detected in QnA query. Rules triggered: {detected_rules}")
            return {
                "error": "Request blocked: potential prompt injection detected",
                "detected_rules": detected_rules
            }
        return search_sync(query, intent="qna")

    @mcp.tool()
    def smartpack(query: str) -> Dict[str, Any]:
        """Generate Smartpack content (Elastic now; env toggles can permit Databricks)."""
        # Guardrail: Check for prompt injection attempts
        if is_prompt_injection(query):
            detected_rules = explain_prompt_injection(query)
            logger.warning(f"Potential prompt injection detected in Smartpack query. Rules triggered: {detected_rules}")
            return {
                "error": "Request blocked: potential prompt injection detected",
                "detected_rules": detected_rules
            }
        return search_sync(query, intent="smartpack")

    @mcp.tool()
    def fetch(id: str) -> Dict[str, Any]:
        """Fetch full document content by id."""
        return fetch_sync(id)

    return mcp

# -------------------------------
# Flask App (compatibility)
# -------------------------------
def create_app():
    app = Flask(__name__)

    @app.route('/')
    def home():
        return jsonify({
            "name": "MCP Server",
            "version": "1.1.0",
            "status": "running",
            "endpoints": {
                "search": "/api/search",
                "qna": "/api/qna",
                "smartpack": "/api/smartpack",
                "fetch": "/api/fetch",
                "mcp_sse": "/sse"
            }
        })

    @app.route('/api/search', methods=['POST'])
    def search_endpoint():
        try:
            data = request.get_json(force=True, silent=True) or {}
            query = data.get('query', '')
            intent = data.get('intent')  # optional: "qna" | "smartpack"
            if not query:
                return jsonify({"error": "Query parameter is required"}), 400
            result = search_sync(query, intent=intent)
            return jsonify(result)
        except Exception as e:
            logger.error(f"Error in search endpoint: {e}")
            return jsonify({"error": str(e)}), 500

    @app.route('/api/qna', methods=['POST'])
    def qna_endpoint():
        try:
            data = request.get_json(force=True, silent=True) or {}
            query = data.get('query', '')
            if not query:
                return jsonify({"error": "Query parameter is required"}), 400
            result = search_sync(query, intent="qna")
            return jsonify(result)
        except Exception as e:
            logger.error(f"Error in qna endpoint: {e}")
            return jsonify({"error": str(e)}), 500

    @app.route('/api/smartpack', methods=['POST'])
    def smartpack_endpoint():
        try:
            data = request.get_json(force=True, silent=True) or {}
            query = data.get('query', '')
            if not query:
                return jsonify({"error": "Query parameter is required"}), 400
            result = search_sync(query, intent="smartpack")
            return jsonify(result)
        except Exception as e:
            logger.error(f"Error in smartpack endpoint: {e}")
            return jsonify({"error": str(e)}), 500

    @app.route('/api/fetch', methods=['POST'])
    def fetch_endpoint():
        try:
            data = request.get_json(force=True, silent=True) or {}
            doc_id = data.get('id', '')
            if not doc_id:
                return jsonify({"error": "ID parameter is required"}), 400
            result = fetch_sync(doc_id)
            return jsonify(result)
        except Exception as e:
            logger.error(f"Error in fetch endpoint: {e}")
            return jsonify({"error": str(e)}), 500

    @app.route('/api/download-pdf-local/<path:filename>', methods=['GET'])
    def download_pdf_local(filename):
        """
        Download PDF from local storage (smartpackPdfMapping/generated_pdfs/)
        Security: Only allows downloading from the generated_pdfs directory
        """
        try:
            # Security: Normalize and validate the path to prevent directory traversal
            import os.path
            from pathlib import Path

            # Get the base directory for PDFs
            base_dir = os.path.join(os.path.dirname(__file__), "smartpackPdfMapping", "generated_pdfs")

            # Normalize the filename to prevent path traversal attacks
            safe_filename = os.path.basename(filename)

            # Build the full path
            pdf_path = os.path.join(base_dir, safe_filename)

            # Verify the file exists and is within the allowed directory
            pdf_path_resolved = os.path.abspath(pdf_path)
            base_dir_resolved = os.path.abspath(base_dir)

            if not pdf_path_resolved.startswith(base_dir_resolved):
                logger.warning(f"Attempted path traversal attack: {filename}")
                return jsonify({"error": "Invalid file path"}), 403

            if not os.path.exists(pdf_path_resolved):
                logger.warning(f"PDF file not found: {pdf_path_resolved}")
                return jsonify({"error": "PDF file not found"}), 404

            # Verify it's a PDF file
            if not pdf_path_resolved.endswith('.pdf'):
                logger.warning(f"Attempted to download non-PDF file: {filename}")
                return jsonify({"error": "Only PDF files are allowed"}), 403

            logger.info(f"Serving PDF file: {pdf_path_resolved}")
            return send_file(
                pdf_path_resolved,
                mimetype='application/pdf',
                as_attachment=True,
                download_name=safe_filename
            )

        except Exception as e:
            logger.error(f"Error in download_pdf_local endpoint: {e}")
            return jsonify({"error": str(e)}), 500

    @app.route('/api/download-pdf-storage/<path:blob_path>', methods=['GET'])
    def download_pdf_storage(blob_path):
        """
        Download PDF from Azure Storage (server acts as proxy)
        Security: Only allows downloading PDFs from company/ and person/ folders
        """
        try:
            # Security: Validate blob path
            if not (blob_path.startswith('company/') or blob_path.startswith('person/')):
                logger.warning(f"Attempted to download from unauthorized path: {blob_path}")
                return jsonify({"error": "Access denied. Only company/ and person/ paths are allowed"}), 403

            # Verify it's a PDF file
            if not blob_path.endswith('.pdf'):
                logger.warning(f"Attempted to download non-PDF file: {blob_path}")
                return jsonify({"error": "Only PDF files are allowed"}), 403

            # Download from Azure Storage
            result = download_pdf_from_storage(blob_path)

            if not result.get('success'):
                error_msg = result.get('error', 'Unknown error')
                logger.error(f"Failed to download PDF from storage: {error_msg}")
                return jsonify({"error": error_msg}), 500

            # Return the PDF as a file download
            pdf_data = result['data']
            filename = result.get('filename', 'smartpack.pdf')

            logger.info(f"Serving PDF from Azure Storage: {blob_path}")
            return send_file(
                BytesIO(pdf_data),
                mimetype='application/pdf',
                as_attachment=True,
                download_name=filename
            )

        except Exception as e:
            logger.error(f"Error in download_pdf_storage endpoint: {e}")
            return jsonify({"error": str(e)}), 500

    return app
