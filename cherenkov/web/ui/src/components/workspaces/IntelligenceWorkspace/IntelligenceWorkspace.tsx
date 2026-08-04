/**
 * @license
 * SPDX-License-Identifier: Apache-2.0
 */

import React from 'react';
import SseChatAssistant from './SseChatAssistant';
import KnowledgeGraphExplorer from './KnowledgeGraphExplorer';
import SddMemoryCockpit from './SddMemoryCockpit';
import { PageHeader } from '../../ui/PageHeader';

export const IntelligenceWorkspace: React.FC = () => {
  return (
    <div className="p-6 h-full overflow-y-auto space-y-6 grid-bg bg-transparent relative z-10" id="intelligence-workspace">
      <PageHeader
        title="Knowledge"
        description="What Cherenkov has learned about your API, plus a chat assistant to ask it questions."
      />

      {/* 1. SSE Streamed AI Chat Copilot */}
      <SseChatAssistant />

      {/* 2. Knowledge Graph Explorer */}
      <KnowledgeGraphExplorer />

      {/* 3. SDD Memory & Token Cockpit */}
      <SddMemoryCockpit />
    </div>
  );
};

export default IntelligenceWorkspace;
