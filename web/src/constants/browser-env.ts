import { z } from "zod";

const BROWSER_ENV_SCHEMA = z.object({
  shifuApiUrl: z.string().url().default("http://localhost:8000"),
});

const BROWSER_ENV_INPUT = {
  shifuApiUrl: import.meta.env.VITE_SHIFU_API_URL,
};

export const BROWSER_ENV = BROWSER_ENV_SCHEMA.parse(BROWSER_ENV_INPUT);
