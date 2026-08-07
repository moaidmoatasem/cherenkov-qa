/**
 * @license
 * SPDX-License-Identifier: Apache-2.0
 */

import React from 'react';
import ProjectManager from './ProjectManager';
import ModelProviderSettings from './ModelProviderSettings';
import DeviceManager from './DeviceManager';
import EjectSuitePanel from './EjectSuitePanel';
import GovernanceSettings from './GovernanceSettings';
import A11ySettings from './A11ySettings';
import { PageHeader } from '../../ui/PageHeader';

export const SettingsWorkspace: React.FC = () => {
  return (
    <div className="p-6 h-full overflow-y-auto space-y-6 grid-bg bg-transparent relative z-10" id="settings-workspace">
      <PageHeader
        title="Settings"
        description="Projects, hardware & model providers, exporting your tests, and access control."
      />

      {/* 1. Project Management */}
      <ProjectManager />

      {/* 2. LLM provider, model tiers & AirLLM */}
      <ModelProviderSettings />

      {/* 3. Hardware & VLM Device Diagnostics */}
      <DeviceManager />

      {/* 4. Plain Playwright Suite Eject Exporter */}
      <EjectSuitePanel />

      {/* 5. Governance & System Settings */}
      <GovernanceSettings />

      {/* 6. Accessibility & Display */}
      <A11ySettings />
    </div>
  );
};

export default SettingsWorkspace;
