import React, { useState, useEffect } from 'react';
import { ChevronRight, X, Compass, CheckCircle } from 'lucide-react';
import { WorkspaceId } from './layout/NavigationBar';

interface TourStep {
  title: string;
  description: string;
  tabId: WorkspaceId;
}

// Mirrors the real QA loop -- no scripting knowledge assumed. If you're
// moving from manual testing to automation, this is the whole workflow.
const TOUR_STEPS: TourStep[] = [
  {
    title: '1. Generate',
    description: "Drop in your OpenAPI spec. Cherenkov's AI reads every endpoint and writes a full test suite for you -- no scripting required to get started.",
    tabId: 'authoring',
  },
  {
    title: '2. Validate',
    description: 'Run the generated tests against your real API. Cherenkov checks every response against the spec, so you see actual drift, not just pass/fail.',
    tabId: 'dashboard',
  },
  {
    title: '3. Triage',
    description: "Anything the AI wasn't fully confident about lands here for a quick human call. You approve, edit, or reject -- nothing changes without you.",
    tabId: 'triage',
  },
  {
    title: '4. Knowledge',
    description: 'Cherenkov remembers what it learns about your API across runs, so every generation and review gets sharper over time.',
    tabId: 'intelligence',
  },
];

interface GuidedTourProps {
  onClose: () => void;
  onNavigate: (tabId: WorkspaceId) => void;
}

export default function GuidedTour({ onClose, onNavigate }: GuidedTourProps) {
  const [currentStep, setCurrentStep] = useState(0);

  // Set initial tab on mount only -- onNavigate is not guaranteed to be
  // referentially stable across renders, and re-running this on every
  // identity change causes an infinite navigate -> re-render -> navigate loop.
  useEffect(() => {
    onNavigate(TOUR_STEPS[0].tabId);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const handleNext = () => {
    if (currentStep < TOUR_STEPS.length - 1) {
      const nextStep = currentStep + 1;
      setCurrentStep(nextStep);
      onNavigate(TOUR_STEPS[nextStep].tabId);
    } else {
      onClose();
      onNavigate('authoring');
    }
  };

  const handlePrev = () => {
    if (currentStep > 0) {
      const prevStep = currentStep - 1;
      setCurrentStep(prevStep);
      onNavigate(TOUR_STEPS[prevStep].tabId);
    }
  };

  return (
    <div className="fixed inset-x-0 bottom-12 z-50 flex justify-center pointer-events-none animate-fadeIn">
      <div className="bg-[#131d31] border border-glow-blue/50 p-5 rounded-2xl w-full max-w-lg shadow-[0_0_40px_rgba(34,211,238,0.15)] flex flex-col gap-4 pointer-events-auto backdrop-blur-xl">
        <div className="flex justify-between items-start">
          <div className="flex items-center gap-2">
            <Compass className="w-5 h-5 text-glow-blue" />
            <h3 className="font-display font-bold text-sm text-text-primary uppercase tracking-wider">
              {TOUR_STEPS[currentStep].title}
            </h3>
          </div>
          <button onClick={onClose} className="text-[#7D8DA1] hover:text-white transition">
            <X className="w-4 h-4" />
          </button>
        </div>

        <p className="text-xs text-[#E6EDF3] leading-relaxed font-sans">
          {TOUR_STEPS[currentStep].description}
        </p>

        <div className="flex justify-between items-center mt-2">
          <div className="flex gap-1.5">
            {TOUR_STEPS.map((_, idx) => (
              <div
                key={idx}
                className={`w-2 h-2 rounded-full ${idx === currentStep ? 'bg-glow-blue' : 'bg-white/20'}`}
              />
            ))}
          </div>

          <div className="flex gap-2 text-xs font-mono">
            <button
              onClick={handlePrev}
              disabled={currentStep === 0}
              className="px-3 py-1.5 rounded-lg border border-white/10 text-text-muted hover:text-white hover:bg-white/5 disabled:opacity-30 transition"
            >
              PREV
            </button>
            <button
              onClick={handleNext}
              className="px-4 py-1.5 rounded-lg bg-glow-blue hover:bg-opacity-90 text-slate-950 font-bold transition flex items-center gap-1"
            >
              {currentStep < TOUR_STEPS.length - 1 ? 'NEXT' : 'FINISH'}
              {currentStep < TOUR_STEPS.length - 1 ? <ChevronRight className="w-3.5 h-3.5" /> : <CheckCircle className="w-3.5 h-3.5" />}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
