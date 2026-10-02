import { setupServer } from "msw/node";

import { handlers } from "./handlers";

/** The fixture API for Vitest. Started and stopped in src/test/setup.ts. */
export const server = setupServer(...handlers);
