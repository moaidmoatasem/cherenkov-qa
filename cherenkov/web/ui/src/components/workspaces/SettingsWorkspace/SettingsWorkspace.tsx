/**
 * @license
 * SPDX-License-Identifier: Apache-2.0
 */

import React from 'react';
import ProjectManager from './ProjectManager';
import DeviceManager from './DeviceManager';
import EjectSuitePanel from './EjectSuitePanel';
import GovernanceSettings from './GovernanceSettings';
import ModelProviderSettings from './ModelProviderSettings';
import { PageHeader } from '../../ui/PageHeader';

export const SettingsWorkspace: React.FC = () => {
  return (
    <div className="p-6 h-full overflow-y-auto space-y-6 grid-bg bg-transparent relative z-10" id="settings-workspace">
      <PageHeader
        title="Settings Workspace"
        description="Project management, VLM & hardware devices, LLM provider configuration, plain Playwright eject export, and system governance parameters."
      />

      {/* 1. LLM Provider & Model Configuration */}
      <ModelProviderSettings />

      {/* 2. Project Management */}
      <ProjectManager />

      {/* 3. Hardware & VLM Device Diagnostics */}
      <DeviceManager />

      {/* 4. Plain Playwright Suite Eject Exporter */}
      <EjectSuitePanel />

      {/* 5. Governance & System Settings */}
      <GovernanceSettings />
    </div>
  );
};

export default SettingsWorkspace;
