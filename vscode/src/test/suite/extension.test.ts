import * as assert from 'assert';
import * as vscode from 'vscode';

suite('Extension Test Suite', () => {
  vscode.window.showInformationMessage('Start all tests.');

  test('Extension should be present', () => {
    assert.ok(vscode.extensions.getExtension('cherenkov-qa.cherenkov-qa'));
  });

  test('Commands should be registered', async () => {
    const ext = vscode.extensions.getExtension('cherenkov-qa.cherenkov-qa');
    await ext?.activate();
    const commands = await vscode.commands.getCommands(true);
    assert.ok(commands.includes('cherenkov.validate'));
    assert.ok(commands.includes('cherenkov.generate'));
    assert.ok(commands.includes('cherenkov.doctor'));
    assert.ok(commands.includes('cherenkov.eject'));
  });
});
