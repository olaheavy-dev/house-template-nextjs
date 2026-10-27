"""CI stand-in for an OTLP collector and a backend, on one port: logs each trace export and each
API call with the traceparent it carried, one line per request, to the file named on the command line.

python telemetry_sink.py <port> <log file>
"""

import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer


class Sink(BaseHTTPRequestHandler):
    def _answer(self) -> None:
        self.rfile.read(int(self.headers.get("content-length") or 0))
        if self.path == "/v1/traces":
            line = "traces"
            body, kind = b"", "application/x-protobuf"
        else:
            line = f"api {self.path} {self.headers.get('traceparent', '-')}"
            body, kind = b"{}", "application/json"
        with open(sys.argv[2], "a") as log:
            log.write(line + "\n")
        self.send_response(200)
        self.send_header("content-type", kind)
        self.send_header("content-length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    do_GET = do_POST = _answer

    def log_message(self, *args: object) -> None:
        pass


ThreadingHTTPServer(("127.0.0.1", int(sys.argv[1])), Sink).serve_forever()
