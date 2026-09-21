// Pre-commit: fix and format staged files only. `npm run check` (CI) runs the full suite.
const quote = (files) => files.map((file) => JSON.stringify(file)).join(" ");

// ESLint 9 resolves eslint.config.js from its working directory, so frontend tools run in the workspace.
const inFrontend = (command) => (files) => `npm exec -w frontend -- ${command} ${quote(files)}`;

export default {
  "backend/**/*.py": (files) => [
    `uv run --directory backend ruff check --fix ${quote(files)}`,
    `uv run --directory backend ruff format ${quote(files)}`,
  ],
  "frontend/**/*.{js,jsx,ts,tsx}": [
    inFrontend("eslint --fix --max-warnings=0 --no-warn-ignored"),
    inFrontend("prettier --write"),
  ],
  "frontend/**/*.{css,html,json}": inFrontend("prettier --write"),
};
