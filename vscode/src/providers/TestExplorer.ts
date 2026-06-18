import * as vscode from 'vscode';
import { runValidate } from '../commands/validate';
import { fetchLastReport } from '../api/CherenkovClient';

export class CherenkovTestExplorer {
  private controller: vscode.TestController;
  private baseUrl: string;
  private outputChannel: vscode.OutputChannel;

  constructor(outputChannel: vscode.OutputChannel, baseUrl: string) {
    this.outputChannel = outputChannel;
    this.baseUrl = baseUrl;
    this.controller = vscode.tests.createTestController('cherenkovTestController', 'Cherenkov QA');

    this.controller.createRunProfile(
      'Run Conformance Tests',
      vscode.TestRunProfileKind.Run,
      (request, token) => {
        this.runHandler(request, token);
      }
    );

    vscode.workspace.onDidOpenTextDocument(doc => this.parseTests(doc));
    vscode.workspace.onDidChangeTextDocument(e => this.parseTests(e.document));

    // Initial parse of visible documents
    vscode.window.visibleTextEditors.forEach(editor => this.parseTests(editor.document));
  }

  public updateBaseUrl(url: string): void {
    this.baseUrl = url;
  }

  private parseTests(document: vscode.TextDocument) {
    if (!document.getText().includes('openapi:') && !document.getText().includes('"openapi"')) {
      return;
    }

    const text = document.getText();
    const lines = text.split('\n');
    let inPaths = false;

    for (let i = 0; i < lines.length; i++) {
      const line = lines[i];
      if (line.trim() === 'paths:') {
        inPaths = true;
        continue;
      }
      if (!inPaths) {continue;}

      if (/^(  |\t)\//.test(line)) {
        const pathMatch = line.match(/^\s*(\/[^\s:]+)/);
        if (!pathMatch) {continue;}
        const endpoint = pathMatch[1];

        // Create or update TestItem
        const id = `${document.uri.toString()}::${endpoint}`;
        let testItem = this.controller.items.get(id);
        if (!testItem) {
          testItem = this.controller.createTestItem(id, endpoint, document.uri);
          this.controller.items.add(testItem);
        }
        testItem.range = new vscode.Range(i, 0, i, line.length);
      }

      if (/^\S/.test(line) && line.trim() !== 'paths:') {
        inPaths = false;
      }
    }
  }

  private async runHandler(request: vscode.TestRunRequest, token: vscode.CancellationToken) {
    const run = this.controller.createTestRun(request);

    // Collect all tests if no specific tests selected
    const testsToRun: vscode.TestItem[] = [];
    if (request.include) {
      request.include.forEach(t => testsToRun.push(t));
    } else {
      this.controller.items.forEach(t => testsToRun.push(t));
    }

    // Mark as running
    testsToRun.forEach(t => run.enqueued(t));
    testsToRun.forEach(t => run.started(t));

    // We just run the entire validate command for now
    await runValidate(this.outputChannel);

    const report = await fetchLastReport(this.baseUrl);

    // Resolve results
    for (const test of testsToRun) {
      if (token.isCancellationRequested) {
        run.skipped(test);
        continue;
      }

      if (!report) {
        run.errored(test, new vscode.TestMessage('No report generated'));
        continue;
      }

      const findings = report.findings?.filter(f => f.endpoint === test.label) ?? [];
      const hasFailures = findings.some(f => f.severity === 'high');

      if (hasFailures) {
        const msgs = findings.map(f => new vscode.TestMessage(`Expected: ${f.expected}, Actual: ${f.actual}`));
        run.failed(test, msgs);
      } else {
        run.passed(test);
      }
    }

    run.end();
  }

  dispose() {
    this.controller.dispose();
  }
}
