// render_beautiful.mjs — Wrapper around beautiful-mermaid for CLI use
// Usage:
//   node render_beautiful.mjs svg   <input.mmd> <output.svg>
//   node render_beautiful.mjs ascii <input.mmd> <output.txt> [--ascii-only] [--padding-x N] [--padding-y N]

import { readFileSync, writeFileSync } from "node:fs";
import { resolve } from "node:path";

const MODE = process.argv[2];
const INPUT = process.argv[3];
const OUTPUT = process.argv[4];

if (!MODE || !INPUT || !OUTPUT) {
    console.error("Usage: node render_beautiful.mjs <svg|ascii> <input.mmd> <output> [options]");
    process.exit(1);
}

const source = readFileSync(INPUT, "utf-8");

// Parse optional flags
function parseFlags(argv) {
    const flags = {};
    for (let i = 5; i < argv.length; i++) {
        if (argv[i] === "--ascii-only") flags.useAscii = true;
        if (argv[i] === "--padding-x" && argv[i + 1]) flags.paddingX = parseInt(argv[++i], 10);
        if (argv[i] === "--padding-y" && argv[i + 1]) flags.paddingY = parseInt(argv[++i], 10);
        if (argv[i] === "--color-mode" && argv[i + 1]) flags.colorMode = argv[++i];
    }
    return flags;
}

async function main() {
    if (MODE === "svg") {
        const { renderMermaidSVG } = await import("beautiful-mermaid");
        const svg = renderMermaidSVG(source);
        writeFileSync(OUTPUT, svg, "utf-8");
        console.log(`SVG written to ${OUTPUT}`);
    } else if (MODE === "ascii") {
        const { renderMermaidASCII } = await import("beautiful-mermaid");
        const flags = parseFlags(process.argv);
        const ascii = renderMermaidASCII(source, flags);
        writeFileSync(OUTPUT, ascii, "utf-8");
        console.log(`ASCII written to ${OUTPUT}`);
    } else {
        console.error(`Unknown mode: ${MODE}. Use 'svg' or 'ascii'.`);
        process.exit(1);
    }
}

main().catch((err) => {
    console.error(`[render_beautiful] Error: ${err.message}`);
    process.exit(1);
});
