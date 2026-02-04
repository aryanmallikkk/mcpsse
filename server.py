import os
import requests
import mcp.types as types
from mcp.server import Server
from mcp.server.sse import SseServerTransport
from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import Response, PlainTextResponse
from starlette.routing import Route
import uvicorn

print("🔥 LAMBDA HEADER MCP SERVER BOOTED")

LAMBDA_URL = os.getenv("LAMBDA_URL", "")
server = Server("lambda-header-mcp")

# -------------------- TOOLS --------------------
@server.list_tools()
async def list_tools() -> list[types.Tool]:
    return [
        types.Tool(
            name="call_lambda",
            description="Call Lambda with a custom header",
            inputSchema={
                "type": "object",
                "properties": {
                    "note": {"type": "string"}
                },
                "required": ["note"]
            },
        )
    ]

@server.call_tool()
async def call_tool(name: str, arguments: dict | None):
    if name != "call_lambda":
        raise ValueError(f"Unknown tool: {name}")
    
    note = arguments.get("note", "") if arguments else ""
    
    try:
        r = requests.post(
            LAMBDA_URL,
            headers={"message": note},
            timeout=10,
        )
        text = f"Status {r.status_code}\n{r.text}"
    except Exception as e:
        text = f"Lambda error: {e}"
    
    return [types.TextContent(type="text", text=text)]

# -------------------- SSE --------------------
sse = SseServerTransport("/messages")

async def handle_sse(request: Request):
    async with sse.connect_sse(
        request.scope,
        request.receive,
        request._send,
    ) as (reader, writer):
        await server.run(
            reader,
            writer,
            server.create_initialization_options(),
        )
    # Don't return anything - SSE handles the response

async def handle_messages(request: Request):
    await sse.handle_post_message(
        request.scope,
        request.receive,
        request._send,
    )
    # Don't return anything

async def health(_: Request) -> Response:
    return PlainTextResponse("OK")

# -------------------- APP --------------------
app = Starlette(
    routes=[
        Route("/sse", handle_sse),
        Route("/messages", handle_messages, methods=["POST"]),
        Route("/health", health),
    ]
)

if __name__ == "__main__":
    port = int(os.getenv("PORT", "8080"))
    uvicorn.run(app, host="0.0.0.0", port=port)
