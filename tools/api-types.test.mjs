import assert from "node:assert/strict";
import { test } from "node:test";

import { drift } from "./api-types.mjs";

const openapi = (properties) => ({ components: { schemas: { ItemAction: { properties } } } });
const source = "export interface ItemAction {\n  action: string;\n  // a note\n  label?: string;\n}";
const mapping = { ItemAction: "ItemAction" };

test("matching fields pass", () => {
  assert.deepEqual(drift(openapi({ action: {}, label: {} }), source, mapping), []);
});

test("a renamed field is drift in both directions", () => {
  assert.deepEqual(drift(openapi({ action: {}, title: {} }), source, mapping), [
    "ItemAction lacks title",
    "ItemAction has extra label",
  ]);
});

test("a missing schema or interface is drift", () => {
  assert.deepEqual(drift(openapi({}), source, { Gone: "ItemAction" }), [
    "schema Gone is missing from openapi.json",
  ]);
  assert.deepEqual(drift(openapi({}), source, { ItemAction: "Gone" }), [
    "interface Gone is missing from types.ts",
  ]);
});
