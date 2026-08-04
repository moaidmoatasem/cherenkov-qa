/**
 * @license
 * SPDX-License-Identifier: Apache-2.0
 */

import React from 'react';
import ProjectManager from './ProjectManager';
import DeviceManager from './DeviceManager';
import EjectSuitePanel from './EjectSuitePanel';
import GovernanceSettings from './GovernanceSettings';
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

      {/* 2. Hardware & VLM Device Diagnostics */}
      <DeviceManager />

      {/* 3. Plain Playwright Suite Eject Exporter */}
      <EjectSuitePanel />

      {/* 4. Governance & System Settings */}
      <GovernanceSettings />
    </div>
  );
};

export default SettingsWorkspace;
