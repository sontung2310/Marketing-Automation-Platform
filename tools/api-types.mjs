// Fails when frontend/src/api/types.ts drifts from backend/openapi.json
// (roadmap 6.6): each mapped interface must have exactly the schema's fields.
import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";

/** OpenAPI schema name → the frontend interface that mirrors it. */
export const SCHEMA_TO_TYPE = {
  CompanyView: "Company",
  TrackedKeywords: "TrackedKeywordsBody",
  ICP: "CompanyIcp",
  Service: "CompanyService",
  BrandVoice: "BrandVoice",
  ActivityItem: "Activity",
  ActivityPage: "ActivityPage",
  ActivityAuthor: "ActivityAuthor",
  Price: "ActivityPrice",
  Engagement: "ActivityEngagement",
  SimulateBody: "SimulateBody",
  ItemAction: "ItemAction",
  TrendItem: "Trend",
  SamplePost: "SamplePost",
  InfluencerItem: "Influencer",
  EvidenceLink: "InfluencerEvidence",
  RecommendationItem: "Recommendation",
  RecommendationEvidence: "Evidence",
  NextAction: "NextAction",
};

/** Field names of every `export interface` in a TypeScript source. */
export function interfaceFields(source) {
  const fields = {};
  for (const [, name, body] of source.matchAll(/export interface (\w+)\s*{([\s\S]*?)\n}/g)) {
    const withoutComments = body.replace(/\/\*[\s\S]*?\*\/|\/\/.*$/gm, "");
    fields[name] = [...withoutComments.matchAll(/^\s*(\w+)\??:/gm)].map((match) => match[1]);
  }
  return fields;
}

export function drift(openapi, source, mapping = SCHEMA_TO_TYPE) {
  const schemas = openapi.components?.schemas ?? {};
  const types = interfaceFields(source);
  const problems = [];
  for (const [schema, type] of Object.entries(mapping)) {
    if (!schemas[schema]) problems.push(`schema ${schema} is missing from openapi.json`);
    else if (!types[type]) problems.push(`interface ${type} is missing from types.ts`);
    else {
      const expected = new Set(Object.keys(schemas[schema].properties ?? {}));
      const actual = new Set(types[type]);
      for (const field of expected.difference(actual)) problems.push(`${type} lacks ${field}`);
      for (const field of actual.difference(expected)) problems.push(`${type} has extra ${field}`);
    }
  }
  return problems;
}

if (process.argv[1] === fileURLToPath(import.meta.url)) {
  const root = new URL("../", import.meta.url);
  const openapi = JSON.parse(readFileSync(new URL("backend/openapi.json", root), "utf8"));
  const source = readFileSync(new URL("frontend/src/api/types.ts", root), "utf8");
  const problems = drift(openapi, source);
  for (const problem of problems) console.error(`API type drift: ${problem}`);
  process.exit(problems.length ? 1 : 0);
}
