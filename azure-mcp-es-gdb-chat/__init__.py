"""
Azure Functions entry point for MCP Server
"""

import azure.functions as func
import logging
import os
import sys
import json
from dotenv import load_dotenv

# Cargar variables de entorno
load_dotenv()

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Agregar el directorio actual al path para importar server
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Crear el app de Azure Functions
app = func.FunctionApp()

@app.route(route="mcp/{restOfPath:?}", methods=["GET", "POST"])
async def mcp_handler(req: func.HttpRequest) -> func.HttpResponse:
    """
    Manejador principal para el servidor MCP en Azure Functions
    
    Este endpoint maneja las peticiones MCP tanto para SSE como para HTTP streamable.
    """
    try:
        # Obtener el método HTTP
        method = req.method.lower()
        logger.info(f"Recibida petición {method} a /mcp")
        
        # Obtener headers
        headers = dict(req.headers)
        logger.info(f"Headers: {headers}")
        
        # Verificar si es una petición SSE
        accept_header = headers.get('accept', '').lower()
        if 'text/event-stream' in accept_header:
            return handle_sse_request(req)
        
        # Verificar si es una petición MCP JSON-RPC
        content_type = headers.get('content-type', '').lower()
        if 'application/json' in content_type:
            return handle_jsonrpc_request(req)
        
        # Para GET sin headers específicos, devolver información del servidor
        if method == "get":
            return handle_info_request()
        
        # Método no soportado
        return func.HttpResponse(
            json.dumps({
                "error": "Method not supported",
                "supported_methods": ["GET", "POST"],
                "supported_content_types": ["application/json", "text/event-stream"]
            }),
            status_code=405,
            headers={"Content-Type": "application/json"}
        )
            
    except Exception as e:
        logger.error(f"Error en MCP handler: {str(e)}")
        return func.HttpResponse(
            json.dumps({
                "error": "Internal server error",
                "message": str(e)
            }),
            status_code=500,
            headers={"Content-Type": "application/json"}
        )

def handle_sse_request(req: func.HttpRequest) -> func.HttpResponse:
    """Maneja peticiones Server-Sent Events para MCP"""
    logger.info("Manejando petición SSE")
    
    # Para SSE, necesitamos devolver headers específicos
    headers = {
        "Content-Type": "text/event-stream",
        "Cache-Control": "no-cache",
        "Connection": "keep-alive",
        "Access-Control-Allow-Origin": "*",
        "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
        "Access-Control-Allow-Headers": "Content-Type, Authorization"
    }
    
    # Simular una respuesta SSE básica
    sse_data = "data: {\"jsonrpc\":\"2.0\",\"id\":\"server-info\",\"result\":{\"message\":\"MCP Server SSE endpoint active\"}}\n\n"
    
    return func.HttpResponse(
        sse_data,
        status_code=200,
        headers=headers
    )

def handle_jsonrpc_request(req: func.HttpRequest) -> func.HttpResponse:
    """Maneja peticiones JSON-RPC para MCP"""
    logger.info("Manejando petición JSON-RPC")
    
    try:
        # Obtener el body de la petición
        body = req.get_body()
        if not body:
            return func.HttpResponse(
                json.dumps({
                    "jsonrpc": "2.0",
                    "id": None,
                    "error": {"code": -32700, "message": "Parse error"}
                }),
                status_code=400,
                headers={"Content-Type": "application/json"}
            )
        
        # Parsear JSON
        try:
            data = json.loads(body.decode('utf-8'))
        except json.JSONDecodeError:
            return func.HttpResponse(
                json.dumps({
                    "jsonrpc": "2.0",
                    "id": None,
                    "error": {"code": -32700, "message": "Parse error"}
                }),
                status_code=400,
                headers={"Content-Type": "application/json"}
            )
        
        # Procesar la petición MCP
        method = data.get('method', '')
        params = data.get('params', {})
        request_id = data.get('id')
        
        logger.info(f"Método MCP: {method}")
        
        # Simular respuestas para métodos comunes de MCP
        if method == "initialize":
            response = {
                "jsonrpc": "2.0",
                "id": request_id,
                "result": {
                    "protocolVersion": "2024-11-05",
                    "capabilities": {
                        "tools": {},
                        "resources": {},
                        "prompts": {}
                    },
                    "serverInfo": {
                        "name": "Sample MCP Server",
                        "version": "1.0.0"
                    }
                }
            }
        elif method == "tools/list":
            response = {
                "jsonrpc": "2.0",
                "id": request_id,
                "result": {
                    "tools": [
                        {
                            "name": "search",
                            "description": "Search for documents using OpenAI Vector Store search",
                            "inputSchema": {
                                "type": "object",
                                "properties": {
                                    "query": {
                                        "type": "string",
                                        "description": "Search query string"
                                    }
                                },
                                "required": ["query"]
                            }
                        },
                        {
                            "name": "fetch",
                            "description": "Retrieve complete document content by ID",
                            "inputSchema": {
                                "type": "object",
                                "properties": {
                                    "id": {
                                        "type": "string",
                                        "description": "File ID from vector store"
                                    }
                                },
                                "required": ["id"]
                            }
                        }
                    ]
                }
            }
        else:
            # Método no implementado
            response = {
                "jsonrpc": "2.0",
                "id": request_id,
                "error": {
                    "code": -32601,
                    "message": f"Method '{method}' not found"
                }
            }
        
        return func.HttpResponse(
            json.dumps(response),
            status_code=200,
            headers={"Content-Type": "application/json"}
        )
        
    except Exception as e:
        logger.error(f"Error procesando JSON-RPC: {str(e)}")
        return func.HttpResponse(
            json.dumps({
                "jsonrpc": "2.0",
                "id": request_id if 'request_id' in locals() else None,
                "error": {"code": -32603, "message": "Internal error"}
            }),
            status_code=500,
            headers={"Content-Type": "application/json"}
        )

def handle_info_request() -> func.HttpResponse:
    """Maneja peticiones GET para información del servidor"""
    logger.info("Manejando petición de información")
    
    info = {
        "name": "Sample MCP Server",
        "version": "1.0.0",
        "protocol": "MCP 2024-11-05",
        "capabilities": ["search", "fetch"],
        "status": "running",
        "endpoints": {
            "sse": "/api/mcp (Accept: text/event-stream)",
            "jsonrpc": "/api/mcp (Content-Type: application/json)"
        },
        "tools": [
            {
                "name": "search",
                "description": "Search for documents using OpenAI Vector Store"
            },
            {
                "name": "fetch", 
                "description": "Retrieve complete document content by ID"
            }
        ]
    }
    
    return func.HttpResponse(
        json.dumps(info, indent=2),
        status_code=200,
        headers={"Content-Type": "application/json"}
    )
