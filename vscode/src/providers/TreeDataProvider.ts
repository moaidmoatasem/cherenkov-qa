import * as vscode from 'vscode';
import { ConformanceReport, DriftFinding, fetchLastReport } from '../api/CherenkovClient';

export class ConformanceTreeItem extends vscode.TreeItem {
  constructor(
    public readonly label: string,
    public readonly collapsibleState: vscode.TreeItemCollapsibleState,
    public readonly finding?: DriftFinding,
    description?: string,
    iconId?: string,
    contextValue?: string
  ) {
    super(label, collapsibleState);
    this.description = description;
    if (iconId) {
      this.iconPath = new vscode.ThemeIcon(iconId);
    }
    this.contextValue = contextValue;
  }
}

export class ConformanceTreeProvider implements vscode.TreeDataProvider<ConformanceTreeItem> {
  private _onDidChangeTreeData = new vscode.EventEmitter<ConformanceTreeItem | undefined | null>();
  readonly onDidChangeTreeData = this._onDidChangeTreeData.event;

  private report: ConformanceReport | null = null;
  private baseUrl: string;

  constructor(baseUrl: string) {
    this.baseUrl = baseUrl;
  }

  updateBaseUrl(url: string): void {
    this.baseUrl = url;
  }

  async refresh(): Promise<void> {
    this.report = await fetchLastReport(this.baseUrl);
    this._onDidChangeTreeData.fire(null);
  }

  setReport(report: ConformanceReport | null): void {
    this.report = report;
    this._onDidChangeTreeData.fire(null);
  }

  getTreeItem(element: ConformanceTreeItem): vscode.TreeItem {
    return element;
  }

  getChildren(element?: ConformanceTreeItem): ConformanceTreeItem[] {
    if (element) {
      // Children of a finding
      const f = element.finding;
      if (!f) {
        return [];
      }
      return [
        new ConformanceTreeItem(`Expected: ${f.expected}`, vscode.TreeItemCollapsibleState.None, undefined, undefined, 'check'),
        new ConformanceTreeItem(`Actual: ${f.actual}`, vscode.TreeItemCollapsibleState.None, undefined, undefined, 'close'),
      ];
    }

    if (!this.report) {
      return [
        new ConformanceTreeItem(
          'No report yet — run Cherenkov: Run Conformance Tests',
          vscode.TreeItemCollapsibleState.None,
          undefined,
          undefined,
          'info'
        ),
      ];
    }

    const items: ConformanceTreeItem[] = [];

    // Summary row
    const summaryIcon = this.report.failed === 0 ? 'pass' : 'warning';
    items.push(new ConformanceTreeItem(
      `${this.report.passed} passed  ${this.report.failed} failed  ${this.report.driftCount} drift`,
      vscode.TreeItemCollapsibleState.None,
      undefined,
      this.report.timestamp ? new Date(this.report.timestamp).toLocaleTimeString() : undefined,
      summaryIcon
    ));

    // Drift findings
    if (this.report.findings?.length) {
      for (const finding of this.report.findings) {
        const icon = finding.severity === 'high' ? 'error' : finding.severity === 'medium' ? 'warning' : 'info';
        items.push(new ConformanceTreeItem(
          `${finding.method} ${finding.endpoint}`,
          vscode.TreeItemCollapsibleState.Collapsed,
          finding,
          finding.scenario,
          icon,
          'finding'
        ));
      }
    }

    return items;
  }
}
