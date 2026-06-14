"""Live interfaces for the Mosaic Spend Intelligence agent.

The deterministic Mosaic agent can run as a one-shot command, an interactive
terminal session, or a small local HTTP service for demos and integrations.
"""

from __future__ import annotations

import argparse
import json
import os
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, Callable

try:
    from .agent import MosaicSpendIntelligenceAgent
except ImportError:  # Allows `python src/live_agent.py` from the project root.
    from agent import MosaicSpendIntelligenceAgent


DEFAULT_REQUEST = (
    "Analyze Protein spend for price variance over 20%, maverick spend, "
    "supplier risk, and substitution opportunities."
)
EXIT_COMMANDS = {"exit", "quit", ":q"}


def project_root() -> Path:
    """Return the repository root regardless of how this module is invoked."""
    return Path(__file__).resolve().parents[1]


def default_data_dir() -> Path:
    return project_root() / "data"


def run_live_request(
    agent: MosaicSpendIntelligenceAgent,
    request: str,
    *,
    use_llm: bool = False,
) -> dict[str, Any]:
    """Run a single live request and validate basic input shape."""
    cleaned_request = request.strip()
    if not cleaned_request:
        raise ValueError("Request cannot be empty.")
    return agent.run(cleaned_request, use_llm=use_llm)


def print_result(result: dict[str, Any], *, as_json: bool = False) -> None:
    """Print either the full JSON payload or the buyer-friendly narrative."""
    if as_json:
        print(json.dumps(result, indent=2, default=str))
    else:
        print(result["operator_summary"])


def append_transcript(
    transcript_path: Path,
    request: str,
    result: dict[str, Any],
) -> None:
    """Append a JSONL record for a live session."""
    transcript_path.parent.mkdir(parents=True, exist_ok=True)
    with transcript_path.open("a", encoding="utf-8") as transcript:
        transcript.write(
            json.dumps(
                {
                    "request": request,
                    "status": result["status"],
                    "llm_status": result["llm_status"],
                    "constraints": result["constraints"],
                    "operator_summary": result["operator_summary"],
                },
                default=str,
            )
        )
        transcript.write("\n")


def run_once(
    agent: MosaicSpendIntelligenceAgent,
    request: str,
    *,
    use_llm: bool = False,
    as_json: bool = False,
    transcript_path: Path | None = None,
) -> dict[str, Any]:
    """Run and print a single live request."""
    result = run_live_request(agent, request, use_llm=use_llm)
    print_result(result, as_json=as_json)
    if transcript_path:
        append_transcript(transcript_path, request, result)
    return result


def run_repl(
    agent: MosaicSpendIntelligenceAgent,
    *,
    use_llm: bool = False,
    as_json: bool = False,
    transcript_path: Path | None = None,
    input_fn: Callable[[str], str] = input,
) -> None:
    """Start an interactive procurement analyst loop."""
    print("Mosaic live agent is ready.")
    print("Ask a procurement question, or type 'exit' to stop.")
    print(f"Example: {DEFAULT_REQUEST}")
    while True:
        try:
            request = input_fn("\nmosaic> ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nStopping Mosaic live agent.")
            return

        if request.lower() in EXIT_COMMANDS:
            print("Stopping Mosaic live agent.")
            return
        if not request:
            continue

        try:
            result = run_live_request(agent, request, use_llm=use_llm)
        except Exception as exc:
            print(f"Request failed: {exc}")
            continue

        print()
        print_result(result, as_json=as_json)
        if transcript_path:
            append_transcript(transcript_path, request, result)


def make_handler(
    agent: MosaicSpendIntelligenceAgent,
    *,
    default_use_llm: bool = False,
) -> type[BaseHTTPRequestHandler]:
    """Build a request handler bound to an initialized Mosaic agent."""

    class MosaicLiveHandler(BaseHTTPRequestHandler):
        server_version = "MosaicLiveAgent/1.0"

        def _send_json(self, status_code: int, payload: dict[str, Any]) -> None:
            body = json.dumps(payload, indent=2, default=str).encode("utf-8")
            self.send_response(status_code)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def do_GET(self) -> None:  # noqa: N802 - http.server uses this name.
            if self.path == "/health":
                self._send_json(
                    200,
                    {
                        "status": "ok",
                        "agent": "mosaic_spend_intelligence",
                        "data_dir": agent.data_dir,
                    },
                )
                return

            if self.path == "/":
                self._send_json(
                    200,
                    {
                        "agent": "mosaic_spend_intelligence",
                        "endpoints": {
                            "health": "GET /health",
                            "ask": "POST /ask with JSON body {'request': '...'}",
                        },
                    },
                )
                return

            self._send_json(404, {"status": "error", "message": "Not found"})

        def do_POST(self) -> None:  # noqa: N802 - http.server uses this name.
            if self.path != "/ask":
                self._send_json(404, {"status": "error", "message": "Not found"})
                return

            content_length = int(self.headers.get("Content-Length", "0"))
            raw_body = self.rfile.read(content_length)
            try:
                payload = json.loads(raw_body.decode("utf-8") or "{}")
            except json.JSONDecodeError:
                self._send_json(400, {"status": "error", "message": "Invalid JSON body"})
                return

            request = str(payload.get("request", "")).strip()
            if not request:
                self._send_json(400, {"status": "error", "message": "Field 'request' is required"})
                return

            use_llm = bool(payload.get("use_llm", default_use_llm))
            try:
                result = run_live_request(agent, request, use_llm=use_llm)
            except Exception as exc:
                self._send_json(500, {"status": "error", "message": str(exc)})
                return

            self._send_json(200, result)

        def log_message(self, format: str, *args: Any) -> None:
            if os.getenv("MOSAIC_HTTP_LOGS") == "1":
                super().log_message(format, *args)

    return MosaicLiveHandler


def serve_http(
    agent: MosaicSpendIntelligenceAgent,
    *,
    host: str,
    port: int,
    use_llm: bool = False,
) -> None:
    """Serve the live Mosaic agent over HTTP."""
    handler = make_handler(agent, default_use_llm=use_llm)
    server = ThreadingHTTPServer((host, port), handler)
    print(f"Mosaic live agent listening on http://{host}:{server.server_port}")
    print("POST procurement questions to /ask. Press Ctrl+C to stop.")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopping Mosaic live agent.")
    finally:
        server.server_close()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the Mosaic live procurement agent.")
    parser.add_argument(
        "--data-dir",
        default=str(default_data_dir()),
        help="Directory containing Mosaic synthetic CSV data.",
    )
    parser.add_argument(
        "--use-llm",
        action="store_true",
        help="Use the optional OpenAI narrative layer when OPENAI_API_KEY is configured.",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Print full JSON results instead of the narrative summary.",
    )
    parser.add_argument(
        "--once",
        help="Run one procurement request and exit.",
    )
    parser.add_argument(
        "--serve",
        action="store_true",
        help="Start a local HTTP server with GET /health and POST /ask.",
    )
    parser.add_argument("--host", default="127.0.0.1", help="HTTP server host.")
    parser.add_argument("--port", type=int, default=8000, help="HTTP server port.")
    parser.add_argument(
        "--transcript",
        type=Path,
        help="Optional JSONL path for recording live requests and summaries.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    agent = MosaicSpendIntelligenceAgent(data_dir=args.data_dir)

    if args.serve:
        serve_http(agent, host=args.host, port=args.port, use_llm=args.use_llm)
        return

    if args.once:
        run_once(
            agent,
            args.once,
            use_llm=args.use_llm,
            as_json=args.json,
            transcript_path=args.transcript,
        )
        return

    run_repl(
        agent,
        use_llm=args.use_llm,
        as_json=args.json,
        transcript_path=args.transcript,
    )


if __name__ == "__main__":
    main()
