import type { NextConfig } from "next";
import { config } from "dotenv";
import { resolve } from "path";

// Load environment variables from the root .env file (belo/.env)
// This ensures frontend and backend use the same configuration
const rootEnvPath = resolve(__dirname, "..", ".env");
const result = config({ path: rootEnvPath });

if (result.error) {
  console.warn(`[next.config] Could not load .env from ${rootEnvPath}`);
} else {
  console.log(`[next.config] Loaded environment from ${rootEnvPath}`);
}

const nextConfig: NextConfig = {
  /* config options here */
};

export default nextConfig;
