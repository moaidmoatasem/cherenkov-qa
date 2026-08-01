import React, { useState } from 'react';
import { ArrowLeft, SplitSquareHorizontal, CheckCircle2, AlertTriangle, XCircle, Code2, Play } from 'lucide-react';
import { Divergence } from '../types';

// Mock data for the demonstration
const mockDivergences: (Divergence & { actualResponse: any; expectedSchema: any; endpointMethod: string })[] = [
  {
    id: 'div-001',
    endpoint: '/api/v1/users',
    endpointMethod: 'POST',
    divergenceClass: 'D1',
    severity: 'high',
    status: 'reproduced',
    claimA: 'Spec expects 201 Created',
    claimB: 'Server returned 400 Bad Request',
    evidence: 'Missing required field in auto-generated payload.',
    reproSteps: 'POST /api/v1/users with empty body',
    confidence: 0.95,
    expectedSchema: {
      status: 201,
      body: {
        id: "string",
        email: "string (email)",
        created_at: "string (date-time)"
      }
    },
    actualResponse: {
      status: 400,
      body: {
        error: "ValidationError",
        message: "Field 'email' is required."
      }
    }
  },
  {
    id: 'div-002',
    endpoint: '/api/v1/projects/{id}',
    endpointMethod: 'GET',
    divergenceClass: 'D2',
    severity: 'medium',
    status: 'reproduced',
    claimA: 'Spec expects integer ID',
    claimB: 'Server accepts any string and returns 500',
    evidence: 'Type confusion at DB layer.',
    reproSteps: 'GET /api/v1/projects/abc',
    confidence: 0.88,
    expectedSchema: {
      status: 422,
      body: {
        detail: "Path parameter 'id' must be an integer."
      }
    },
    actualResponse: {
      status: 500,
      body: {
        message: "Internal Server Error"
      }
    }
  }
];

export default function SpecVsRealityScreen() {
  const [selectedDiv, setSelectedDiv] = useState(mockDivergences[0]);

  return (
    <div className="h-full flex flex-col bg-bg-base overflow-hidden">
      <div className="shrink-0 px-6 py-5 border-b border-white/10 flex items-center justify-between bg-black/20">
        <div>
          <h1 className="text-xl font-semibold text-text-primary flex items-center gap-2">
            <SplitSquareHorizontal className="w-5 h-5 text-glow-blue" />
            Spec vs Reality (Pillar 4)
          </h1>
          <p className="text-sm text-text-muted mt-1">Side-by-side visual diff of OpenAPI assertions versus runtime behavior.</p>
        </div>
      </div>

      <div className="flex-1 flex overflow-hidden">
        {/* Left Sidebar: Drift Items */}
        <div className="w-80 border-r border-white/10 bg-black/10 overflow-y-auto flex flex-col">
          <div className="p-3 border-b border-white/10 sticky top-0 bg-black/40 backdrop-blur z-10">
            <h2 className="text-xs font-bold text-text-muted uppercase tracking-wider font-mono">Detected Drift</h2>
          </div>
          <div className="flex-1 p-2 space-y-2">
            {mockDivergences.map(div => (
              <button
                key={div.id}
                onClick={() => setSelectedDiv(div)}
                className={`w-full text-left p-3 rounded-lg border transition-all duration-200 cursor-pointer ${selectedDiv.id === div.id ? 'bg-white/10 border-glow-blue shadow-[0_0_15px_rgba(34,211,238,0.15)]' : 'bg-transparent border-transparent hover:bg-white/5 hover:border-white/10'}`}
              >
                <div className="flex items-center gap-2 mb-1.5">
                  <span className={`text-[9px] font-bold px-1.5 py-0.5 rounded font-mono ${div.endpointMethod === 'GET' ? 'bg-blue-500/20 text-blue-400' : 'bg-green-500/20 text-green-400'}`}>
                    {div.endpointMethod}
                  </span>
                  <span className="text-xs font-medium font-mono text-text-primary truncate">{div.endpoint}</span>
                </div>
                <div className="text-[11px] text-text-secondary line-clamp-1">{div.claimA}</div>
                <div className="text-[11px] text-red-400 line-clamp-1 mt-0.5">{div.claimB}</div>
              </button>
            ))}
          </div>
        </div>

        {/* Right Content: The Visual Diff */}
        <div className="flex-1 flex flex-col overflow-hidden bg-black/5">
          <div className="shrink-0 p-4 border-b border-white/10 bg-black/20 flex items-center justify-between">
            <div className="flex items-center gap-3">
              <span className={`text-xs font-bold px-2 py-1 rounded font-mono ${selectedDiv.endpointMethod === 'GET' ? 'bg-blue-500/20 text-blue-400' : 'bg-green-500/20 text-green-400'}`}>
                {selectedDiv.endpointMethod}
              </span>
              <h2 className="text-lg font-mono font-medium text-text-primary">{selectedDiv.endpoint}</h2>
            </div>
            <span className="text-xs font-bold uppercase tracking-wider text-red-400 border border-red-400/30 bg-red-400/10 px-2 py-1 rounded-full flex items-center gap-1">
              <AlertTriangle className="w-3.5 h-3.5" />
              Drift Detected
            </span>
          </div>

          <div className="flex-1 flex overflow-hidden">
            {/* Spec Expectation Pane */}
            <div className="flex-1 border-r border-white/10 flex flex-col relative group">
              <div className="shrink-0 bg-black/40 p-2 text-center border-b border-white/10">
                <h3 className="text-sm font-semibold tracking-wide text-cyan-400 flex items-center justify-center gap-2">
                  <Code2 className="w-4 h-4" /> Spec Expectation
                </h3>
              </div>
              <div className="flex-1 p-4 overflow-y-auto font-mono text-sm">
                <div className="mb-4">
                  <span className="text-xs text-text-muted uppercase tracking-wider">Expected Status</span>
                  <div className="mt-1 flex items-center gap-2 text-green-400 bg-green-400/10 px-3 py-2 rounded border border-green-400/20">
                    <CheckCircle2 className="w-4 h-4" /> {selectedDiv.expectedSchema.status}
                  </div>
                </div>
                <div>
                  <span className="text-xs text-text-muted uppercase tracking-wider">Expected Schema</span>
                  <pre className="mt-1 p-3 bg-black/30 rounded border border-white/10 text-[#a5d6ff] overflow-x-auto text-xs">
                    {JSON.stringify(selectedDiv.expectedSchema.body, null, 2)}
                  </pre>
                </div>
              </div>
            </div>

            {/* Reality Pane */}
            <div className="flex-1 flex flex-col relative group bg-red-900/5">
              <div className="shrink-0 bg-red-900/20 p-2 text-center border-b border-white/10">
                <h3 className="text-sm font-semibold tracking-wide text-red-400 flex items-center justify-center gap-2">
                  <Play className="w-4 h-4" /> Runtime Reality
                </h3>
              </div>
              <div className="flex-1 p-4 overflow-y-auto font-mono text-sm">
                <div className="mb-4">
                  <span className="text-xs text-text-muted uppercase tracking-wider">Actual Status</span>
                  <div className="mt-1 flex items-center gap-2 text-red-400 bg-red-400/10 px-3 py-2 rounded border border-red-400/20 shadow-[inset_0_0_10px_rgba(248,113,113,0.1)]">
                    <XCircle className="w-4 h-4" /> {selectedDiv.actualResponse.status}
                  </div>
                </div>
                <div>
                  <span className="text-xs text-text-muted uppercase tracking-wider">Actual Payload</span>
                  <pre className="mt-1 p-3 bg-black/30 rounded border border-red-500/20 text-[#ff7b72] overflow-x-auto text-xs shadow-[inset_0_0_10px_rgba(248,113,113,0.1)]">
                    {JSON.stringify(selectedDiv.actualResponse.body, null, 2)}
                  </pre>
                </div>
              </div>
            </div>
          </div>
          
          {/* Footer Action Bar */}
          <div className="shrink-0 p-4 bg-black/40 border-t border-white/10 flex items-center justify-between">
            <div className="text-sm text-text-secondary">
              <span className="font-semibold text-text-primary">Evidence:</span> {selectedDiv.evidence}
            </div>
            <div className="flex items-center gap-3">
              <button className="px-4 py-1.5 rounded bg-white/10 text-white text-xs font-semibold hover:bg-white/20 transition">
                Ignore Drift
              </button>
              <button className="px-4 py-1.5 rounded bg-glow-blue text-bg-base text-xs font-bold hover:bg-cyan-300 transition shadow-[0_0_10px_rgba(34,211,238,0.5)]">
                Propose Healing
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
