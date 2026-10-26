import { defineConfig, devices } from "@playwright/test";

const CI = Boolean(process.env.CI);
const PORT = 3100;

// End-to-end tests against the production build, served as the container serves it: the
// standalone server. `make check` builds first; run them alone with `make e2e-frontend`.
export default defineConfig({
  testDir: "./e2e",
  forbidOnly: CI,
  retries: CI ? 1 : 0,
  reporter: CI ? [["github"], ["list"]] : "list",
  use: {
    baseURL: `http://127.0.0.1:${PORT}`,
    trace: "retain-on-failure",
  },
  // Each page is checked in light and dark, and at a phone's width.
  projects: [
    { name: "light", use: { ...devices["Desktop Chrome"], colorScheme: "light" } },
    { name: "dark", use: { ...devices["Desktop Chrome"], colorScheme: "dark" } },
    { name: "mobile", use: { ...devices["Pixel 7"] } },
  ],
  webServer: {
    // The standalone server serves .next/static only once it is copied in (the image does the same).
    command: "cp -R .next/static .next/standalone/.next/ && node .next/standalone/server.js",
    url: `http://127.0.0.1:${PORT}`,
    env: { PORT: String(PORT), HOSTNAME: "127.0.0.1", NEXT_TELEMETRY_DISABLED: "1" },
    reuseExistingServer: !CI,
    timeout: 30_000,
  },
});
