import React, { useState, useEffect } from 'react';
import { ChevronRight, X, Compass, CheckCircle } from 'lucide-react';

interface TourStep {
  title: string;
  description: string;
  tabId: string;
}

const TOUR_STEPS: TourStep[] = [
  {
    title: '1. Setup & Ingestion',
    description: 'Upload your OpenAPI specification to begin. Cherenkov parses and scores endpoint coverage quality automatically.',
    tabId: 'setup'
  },
  {
    title: '2. Live Generation Pipeline',
    description: 'Watch the models synthesize Playwright specs in real time. Cost & token telemetry is tracked closely.',
    tabId: 'pipeline'
  },
  {
    title: '3. Human-In-The-Loop Review',
    description: 'Reject low-confidence tests, ask AI to explain failures, and manually edit code before approving it into the test suite.',
    tabId: 'review'
  },
  {
    title: '4. Export & Eject',
    description: 'Zero vendor lock-in! Download the fully compliant Playwright configuration and integrate it into your CI/CD.',
    tabId: 'eject'
  }
];

interface GuidedTourProps {
  onClose: () => void;
  onNavigate: (tabId: string) => void;
}

export default function GuidedTour({ onClose, onNavigate }: GuidedTourProps) {
  const [currentStep, setCurrentStep] = useState(0);

  // Set initial tab on mount
  useEffect(() => {
    onNavigate(TOUR_STEPS[0].tabId);
  }, [onNavigate]);

  const handleNext = () => {
    if (currentStep < TOUR_STEPS.length - 1) {
      const nextStep = currentStep + 1;
      setCurrentStep(nextStep);
      onNavigate(TOUR_STEPS[nextStep].tabId);
    } else {
      onClose();
      onNavigate('overview');
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
