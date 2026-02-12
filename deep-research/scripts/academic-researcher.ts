#!/usr/bin/env bun

/**
 * Academic Researcher - Orchestrates Google AI Mode for academic papers
 */

import { spawn } from "child_process";
import { join, resolve } from "path";
import { existsSync } from "fs";

interface AcademicOptions {
  topic: string;
  focus?: 'methodology' | 'literature-review' | 'results' | 'data';
  year?: string;
  maxResults?: number;
}

class AcademicResearcher {
  private readonly googleSkillPath = resolve(__dirname, "../../google-ai-mode-skill");
  
  async search(options: AcademicOptions & { showBrowser?: boolean }) {
    console.log(`🔍 Searching academic sources for: "${options.topic}" (${options.focus || 'general'})...`);

    // 1. Construct Optimized Query
    const query = this.buildQuery(options);
    console.log(`   Query: ${query}`);

    // 2. Execute Google AI Mode Skill
    try {
      const output = await this.executeGoogleSkill(query, options.showBrowser);
      console.log("\n✅ Search complete. Processing results...\n");
      
      // 3. Display Raw Output (for now, can be parsed later)
      console.log(output);

      // 4. Extract Potential PDF Links (Basic Regex)
      const pdfLinks = output.match(/https?:\/\/[^\s)]+\.pdf/g) || [];
      if (pdfLinks.length > 0) {
        console.log("\n📄 Found PDF Candidates for NotebookLM:");
        pdfLinks.forEach(link => console.log(`   - ${link}`));
      }

    } catch (error) {
      console.error("❌ Academic search failed:", error);
    }
  }

  private buildQuery(options: AcademicOptions): string {
    const year = options.year || new Date().getFullYear().toString();
    const focusMap = {
      'methodology': 'research methodology study design',
      'literature-review': 'literature review state of the art',
      'results': 'experimental results data analysis',
      'data': 'dataset raw data'
    };
    
    const focusTerm = options.focus ? focusMap[options.focus] : 'academic research papers';
    return `${options.topic} ${focusTerm} ${year} filetype:pdf (peer-reviewed, journal, conference). Extract key findings and citations.`;
  }

  private executeGoogleSkill(query: string, showBrowser: boolean = false): Promise<string> {
    return new Promise((resolve, reject) => {
      const scriptPath = join(this.googleSkillPath, "scripts", "run.py");
      if (!existsSync(scriptPath)) {
        reject(new Error(`Google AI Mode skill not found at ${scriptPath}`));
        return;
      }

      const args = [scriptPath, "search.py", "--query", query];
      if (showBrowser) {
        args.push("--show-browser");
      }

      // Execute: python ../google-ai-mode-skill/scripts/run.py search.py --query "..."
      const process = spawn("python", args, {
        cwd: this.googleSkillPath,
        env: { ...JSON.parse(JSON.stringify(globalThis.process.env)), PYTHONUTF8: "1" }
      });

      let stdout = "";
      let stderr = "";

      process.stdout.on("data", (data) => stdout += data.toString());
      process.stderr.on("data", (data) => stderr += data.toString());

      process.on("close", (code) => {
        if (code !== 0) {
          reject(new Error(`Process exited with code ${code}: ${stderr}`));
        } else {
          resolve(stdout);
        }
      });
    });
  }
}

// CLI Entry Point
const args = process.argv.slice(2);
const topicIndex = args.indexOf("--topic");
const focusIndex = args.indexOf("--focus");

if (topicIndex === -1) {
  console.log("Usage: bun scripts/academic-researcher.ts --topic 'Your Topic' [--focus methodology]");
  process.exit(1);
}

const topic = args[topicIndex + 1];
const focus = focusIndex !== -1 ? args[focusIndex + 1] as any : undefined;
const showBrowser = args.includes("--show-browser");

new AcademicResearcher().search({ topic, focus, showBrowser });
