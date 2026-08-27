import { defineConfig, globalIgnores } from "eslint/config";
import nextVitals from "eslint-config-next/core-web-vitals";
import nextTs from "eslint-config-next/typescript";

const eslintConfig = defineConfig([
  ...nextVitals,
  ...nextTs,
  globalIgnores([
    ".next/**",
    "out/**",
    "build/**",
    "next-env.d.ts",
    // Python side of this repo -- nothing here is JS/TS.
    "macroservice/**",
    "notebooks/**",
    "scripts/**",
    "tests/**",
    ".venv/**",
  ]),
]);

export default eslintConfig;
