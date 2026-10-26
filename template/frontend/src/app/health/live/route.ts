// The container's liveness check (compose.yaml, the platform's probe): answers while the server
// runs, without calling the backend. The backend's own checks are at /api/health/*.
export function GET() {
  return Response.json({ status: "ok" });
}
