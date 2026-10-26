// @vitest-environment node
import { GET } from "./route";

describe("the liveness check", () => {
  it("answers ok without calling anything", async () => {
    const response = GET();
    expect(response.status).toBe(200);
    expect(await response.json()).toEqual({ status: "ok" });
  });
});
