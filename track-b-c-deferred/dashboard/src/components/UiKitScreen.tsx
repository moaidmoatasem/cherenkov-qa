import React, { useState } from 'react';
import { 
  PageHeader, 
  Panel, 
  Card, 
  SeverityPill, 
  StatusDot, 
  ProvenanceChip, 
  EmptyState, 
  Skeleton, 
  Tabs, 
  Drawer, 
  KpiRing, 
  useToast 
} from './ui';
import { Layers, Play, RefreshCw, Eye } from 'lucide-react';

export default function UiKitScreen() {
  const { toast } = useToast();
  const [isDrawerOpen, setIsDrawerOpen] = useState(false);
  const [activeTab, setActiveTab] = useState('tab-1');
  const [isSkeletonLoading, setIsSkeletonLoading] = useState(false);

  const tabItems = [
    { id: 'tab-1', label: 'Overview', count: 12 },
    { id: 'tab-2', label: 'Divergences', count: 3 },
    { id: 'tab-3', label: 'Settings' }
  ];

  return (
    <div className="flex-1 flex flex-col h-full overflow-hidden bg-bg-base text-text-primary">
      <PageHeader
        title="UI Kit Consistency Gallery"
        description="Verify all shared design tokens, primitives, and interaction states for compliance with the §6 Consistency Contract."
        primaryAction={
          <button 
            onClick={() => toast('Triggered primary page action', 'info')}
            className="px-4 py-2 text-sm font-semibold rounded-lg bg-glow-blue text-bg-base hover:bg-glow-bright hover:shadow-[0_0_12px_rgba(34,211,238,0.5)] transition-all cursor-pointer"
          >
            Page Action
          </button>
        }
      />

      <div className="flex-1 overflow-y-auto p-6 space-y-8 max-w-7xl mx-auto w-full">
        {/* Section 1: Page shell (Panel & Card) */}
        <section className="space-y-4">
          <h2 className="text-lg font-bold font-display text-glow-blue flex items-center gap-2">
            <Layers className="w-5 h-5" /> Panels & Cards
          </h2>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <Panel className="flex flex-col gap-3">
              <h3 className="text-base font-semibold text-text-primary">Standard Panel</h3>
              <p className="text-sm text-text-muted">
                Using the <code>.cherenkov-panel</code> class providing 20px blur glassmorphism and 1px white border at 10% opacity.
              </p>
            </Panel>
            
            <Card hoverable className="flex flex-col gap-3">
              <h3 className="text-base font-semibold text-text-primary">Hoverable Card</h3>
              <p className="text-sm text-text-muted">
                Using the <code>.cherenkov-card</code> class. Hovering activates cyan borders and a subtle cyan drop-shadow.
              </p>
            </Card>
          </div>
        </section>

        {/* Section 2: Pills, Chips, & Dots */}
        <section className="space-y-4">
          <h2 className="text-lg font-bold font-display text-glow-blue">Pills, Chips & Dots</h2>
          <Card className="grid grid-cols-1 md:grid-cols-3 gap-6">
            {/* SeverityPill */}
            <div className="space-y-3">
              <h4 className="text-sm font-bold tracking-wider uppercase text-text-muted">SeverityPills</h4>
              <div className="flex flex-wrap gap-2">
                <SeverityPill severity="critical" />
                <SeverityPill severity="high" />
                <SeverityPill severity="medium" />
                <SeverityPill severity="low" />
                <SeverityPill severity="info" />
              </div>
            </div>

            {/* StatusDot */}
            <div className="space-y-3">
              <h4 className="text-sm font-bold tracking-wider uppercase text-text-muted">StatusDots</h4>
              <div className="flex flex-col gap-2">
                <StatusDot status="reproduced" showLabel />
                <StatusDot status="pending" showLabel />
                <StatusDot status="rejected" showLabel />
                <StatusDot status="live" showLabel />
              </div>
            </div>

            {/* ProvenanceChip */}
            <div className="space-y-3">
              <h4 className="text-sm font-bold tracking-wider uppercase text-text-muted">Provenance Chips</h4>
              <div className="flex flex-wrap gap-2">
                <ProvenanceChip type="spec" />
                <ProvenanceChip type="code" />
                <ProvenanceChip type="traffic" />
                <ProvenanceChip type="db" />
              </div>
            </div>
          </Card>
        </section>

        {/* Section 3: Interactive elements (Tabs, Drawer, Toasts) */}
        <section className="space-y-4">
          <h2 className="text-lg font-bold font-display text-glow-blue">Interactive Elements & Modals</h2>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            <Card className="flex flex-col gap-4">
              <h3 className="text-sm font-bold tracking-wider uppercase text-text-muted">Tabs Navigation</h3>
              <Tabs items={tabItems} activeId={activeTab} onChange={setActiveTab} />
              <div className="text-sm text-text-muted mt-2">
                Active tab index: <span className="font-mono text-text-primary">{activeTab}</span>. (Supports arrow key focus).
              </div>
            </Card>

            <Card className="flex flex-col gap-4">
              <h3 className="text-sm font-bold tracking-wider uppercase text-text-muted">Detail Drawer</h3>
              <p className="text-sm text-text-muted">
                Slides in from the right with blur backdrops and focus trap. ESC closes.
              </p>
              <button 
                onClick={() => setIsDrawerOpen(true)}
                className="w-full mt-auto py-2 text-sm font-semibold rounded-lg border border-border-custom bg-white/5 text-text-primary hover:bg-white/10 transition-all cursor-pointer flex items-center justify-center gap-2"
              >
                <Eye className="w-4 h-4" /> Open Detail Drawer
              </button>
            </Card>

            <Card className="flex flex-col gap-4">
              <h3 className="text-sm font-bold tracking-wider uppercase text-text-muted">Toasts Feedback</h3>
              <div className="grid grid-cols-2 gap-2">
                <button 
                  onClick={() => toast('Successfully recorded decision to memory!', 'success')}
                  className="py-1.5 px-3 text-xs font-semibold rounded bg-success-custom/10 text-success-custom border border-success-custom/20 hover:bg-success-custom/20 transition-all cursor-pointer"
                >
                  Success Toast
                </button>
                <button 
                  onClick={() => toast('Model response taking longer than usual', 'warning')}
                  className="py-1.5 px-3 text-xs font-semibold rounded bg-warning-custom/10 text-warning-custom border border-warning-custom/20 hover:bg-warning-custom/20 transition-all cursor-pointer"
                >
                  Warning Toast
                </button>
                <button 
                  onClick={() => toast('Failed to connect to backend', 'danger', { actionLabel: 'Retry', onAction: () => toast('Retrying now...', 'info') })}
                  className="py-1.5 px-3 text-xs font-semibold rounded bg-danger-custom/10 text-danger-custom border border-danger-custom/20 hover:bg-danger-custom/20 transition-all cursor-pointer"
                >
                  Danger Toast
                </button>
                <button 
                  onClick={() => toast('Sovereign local security mode is active', 'info')}
                  className="py-1.5 px-3 text-xs font-semibold rounded bg-glow-blue/10 text-glow-blue border border-glow-blue/20 hover:bg-glow-blue/20 transition-all cursor-pointer"
                >
                  Info Toast
                </button>
              </div>
            </Card>
          </div>
        </section>

        {/* Section 4: KPI Metrics & Empty States */}
        <section className="grid grid-cols-1 md:grid-cols-2 gap-6">
          <div className="space-y-4">
            <h2 className="text-lg font-bold font-display text-glow-blue">KPI Gauges (SVG Rings)</h2>
            <Card className="grid grid-cols-2 gap-4">
              <KpiRing value={88} title="Release Readiness" subtext="88% certified" glowColor="success" />
              <KpiRing value={12} title="False Positive Rate" subtext="12% noise" glowColor="danger" />
            </Card>
          </div>

          <div className="space-y-4">
            <h2 className="text-lg font-bold font-display text-glow-blue">Skeletons (Shimmer Loading)</h2>
            <Card className="flex flex-col gap-3">
              <div className="flex items-center justify-between mb-2">
                <span className="text-sm font-semibold text-text-primary">Preview Shimmer State</span>
                <button 
                  onClick={() => setIsSkeletonLoading(!isSkeletonLoading)}
                  className="py-1 px-3 text-xs font-bold font-mono rounded bg-white/5 border border-border-custom hover:bg-white/10 flex items-center gap-1.5 cursor-pointer text-text-primary"
                >
                  <RefreshCw className={`w-3.5 h-3.5 ${isSkeletonLoading ? 'animate-spin' : ''}`} /> 
                  Toggle Load View
                </button>
              </div>
              {isSkeletonLoading ? (
                <Skeleton variant="card" />
              ) : (
                <div className="bg-white/5 border border-border-custom p-4 rounded-xl">
                  <h4 className="text-sm font-semibold mb-1">Interactive Content Ready</h4>
                  <p className="text-xs text-text-muted">Click toggle above to check the glow-skeleton placeholder layout.</p>
                </div>
              )}
            </Card>
          </div>
        </section>

        {/* Section 5: Full Empty State */}
        <section className="space-y-4">
          <h2 className="text-lg font-bold font-display text-glow-blue">Empty States</h2>
          <EmptyState 
            title="No Divergences Discovered"
            description="All claims match perfectly across specifications, codebase, traffic logs and databases. Ready for release."
            primaryAction={{
              label: 'Trigger Scanner',
              onClick: () => toast('Launching full divergence crawl...', 'success')
            }}
            secondaryAction={{
              label: 'Configure Egress Policies',
              onClick: () => toast('Opening local configuration...', 'info')
            }}
          />
        </section>
      </div>

      {/* Shared Drawer Component Test */}
      <Drawer isOpen={isDrawerOpen} onClose={() => setIsDrawerOpen(false)} title="Divergence Details [D-401]">
        <div className="space-y-6">
          <div className="flex items-center gap-3">
            <SeverityPill severity="critical" />
            <StatusDot status="live" showLabel />
            <ProvenanceChip type="spec" />
          </div>
          <div>
            <h3 className="text-sm font-bold tracking-wider text-text-muted uppercase mb-1">Description</h3>
            <p className="text-sm text-text-primary">
              Mismatch identified: Specification defines field <code>user_id</code> as an Integer, but runtime traffic demonstrates String uuid representation.
            </p>
          </div>
          <div>
            <h3 className="text-sm font-bold tracking-wider text-text-muted uppercase mb-2">Claim Discrepancy Evidence</h3>
            <div className="border border-border-custom rounded-xl p-4 bg-bg-panel font-mono text-xs text-danger-custom whitespace-pre overflow-x-auto">
              {`- "user_id": 409605\n+ "user_id": "8fa8d39f-eead-43df-818f-a9cb84f68d6f"`}
            </div>
          </div>
          <button 
            onClick={() => {
              setIsDrawerOpen(false);
              toast('Divergence marked intended.', 'success');
            }}
            className="w-full py-2 text-sm font-semibold rounded-lg bg-glow-blue text-bg-base hover:bg-glow-bright hover:shadow-[0_0_12px_rgba(34,211,238,0.5)] transition-all cursor-pointer"
          >
            Mark Intended (Triage)
          </button>
        </div>
      </Drawer>
    </div>
  );
}
