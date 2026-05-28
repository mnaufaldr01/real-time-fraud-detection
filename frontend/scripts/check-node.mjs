import { execSync } from "node:child_process";

const MIN_MAJOR = 20;
const version = process.versions.node;
const major = Number.parseInt(version.split(".")[0] ?? "0", 10);

if (major < MIN_MAJOR) {
  console.error("");
  console.error("  Fraud Analytics Dashboard requires Node.js 20 or newer.");
  console.error(`  Current: v${version}`);
  console.error("");
  console.error("  Fix (Windows):");
  console.error("    winget upgrade OpenJS.NodeJS.LTS");
  console.error("  Then close and reopen your terminal, and run:");
  console.error("    node -v          # should show v20+");
  console.error("    npm run dev");
  console.error("");
  console.error("  Or use Docker (no local Node upgrade):");
  console.error("    docker compose up -d --build analytics-api dashboard-web");
  console.error("    # open http://localhost:3000");
  console.error("");
  process.exit(1);
}

try {
  execSync("node --input-type=module -e \"crypto.getRandomValues(new Uint8Array(1))\"", {
    stdio: "ignore",
  });
} catch {
  console.error("");
  console.error("  Node crypto API is unavailable. Upgrade Node.js to 20 LTS or newer.");
  console.error(`  Current: v${version}`);
  console.error("");
  process.exit(1);
}
