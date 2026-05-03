export const maxDuration = 60;

export async function POST(req: Request) {
  const body = await req.json();

  // Forward the request to the Python backend
  const response = await fetch("http://localhost:8000/api/chat", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });

  // Forward the stream and the critical AI SDK header
  const headers = new Headers({
    "Content-Type": "text/event-stream",
    "Cache-Control": "no-cache",
    Connection: "keep-alive",
  });

  // Forward the x-vercel-ai-ui-message-stream header from the Python backend
  const streamHeader = response.headers.get("x-vercel-ai-ui-message-stream");
  if (streamHeader) {
    headers.set("x-vercel-ai-ui-message-stream", streamHeader);
  }

  return new Response(response.body, { headers });
}
