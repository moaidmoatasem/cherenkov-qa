#!/usr/bin/env node

const fs = require('fs');
const path = require('path');
const { execSync } = require('child_process');

console.log('☢️ Initializing CHERENKOV-QA...\\n');

const currentDir = process.cwd();

// 1. Create .cherenkov directory
const cherenkovDir = path.join(currentDir, '.cherenkov');
if (!fs.existsSync(cherenkovDir)) {
  fs.mkdirSync(cherenkovDir);
  console.log('✅ Created .cherenkov config directory');
} else {
  console.log('ℹ️ .cherenkov config directory already exists');
}

// 2. Scaffold config.yaml
const configPath = path.join(cherenkovDir, 'config.yaml');
if (!fs.existsSync(configPath)) {
  const configContent = `
provider:
  name: ollama
  model: qwen2.5-coder:7b
  url: http://localhost:11434
api:
  target_url: http://localhost:8000
  spec_path: ./api.yaml
  strict_validation: true
`.trim();
  fs.writeFileSync(configPath, configContent);
  console.log('✅ Generated .cherenkov/config.yaml');
}

// 3. Scaffold a basic api.yaml if none exists
const apiSpecPath = path.join(currentDir, 'api.yaml');
if (!fs.existsSync(apiSpecPath)) {
  const openApiContent = `
openapi: 3.0.0
info:
  title: Sample API
  version: 1.0.0
paths:
  /health:
    get:
      summary: Health check
      responses:
        '200':
          description: OK
          content:
            application/json:
              schema:
                type: object
                properties:
                  status:
                    type: string
                    example: ok
`.trim();
  fs.writeFileSync(apiSpecPath, openApiContent);
  console.log('✅ Generated sample api.yaml');
}

// 4. Instructions
console.log('\\n🚀 Setup complete! Next steps:');
console.log('  1. Ensure you have Ollama running: ollama run qwen2.5-coder:7b');
console.log('  2. Modify your api.yaml to match your actual API.');
console.log('  3. Start the test generation: npx cherenkov generate --spec api.yaml');
