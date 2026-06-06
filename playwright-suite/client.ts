// Standalone openapi-fetch client configuration
// Stripped of all trace and interception metadata.

import createClient from "openapi-fetch";
import type { paths } from "./generated-types";

export const client = createClient<paths>({
  baseUrl: process.env.API_URL ?? "http://localhost:8000",
});
