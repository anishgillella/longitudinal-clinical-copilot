'use client';

/**
 * Signal Detail Modal
 *
 * A beautiful, full-screen modal for deep-diving into clinical signals.
 * Features smooth animations, transcript highlighting, and clinical context.
 */

import React from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
  X,
  MessageSquareQuote,
  Brain,
  Lightbulb,
  Activity,
  CheckCircle2,
  AlertTriangle,
  Target,
  FileText,
  Link2,
  Copy,
  Check,
} from 'lucide-react';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';

interface Signal {
  id: string;
  signal_name: string;
  signal_type: string;
  evidence: string;
  reasoning?: string;
  dsm5_criteria?: string;
  maps_to_domain: string;
  clinical_significance: 'low' | 'moderate' | 'high';
  confidence: number;
  verbatim_quote?: string;
  quote_context?: string;
  transcript_line?: number;
}

interface SignalDetailModalProps {
  signal: Signal | null;
  isOpen: boolean;
  onClose: () => void;
  onNavigateToTranscript?: (line: number) => void;
  onVerify?: (signalId: string) => void;
}

const DSM5_DESCRIPTIONS: Record<string, { title: string; description: string }> = {
  A1: {
    title: 'Social-Emotional Reciprocity',
    description: 'Deficits in back-and-forth conversation, reduced sharing of interests or emotions, failure to initiate or respond to social interactions.',
  },
  A2: {
    title: 'Nonverbal Communication',
    description: 'Deficits in nonverbal communicative behaviors used for social interaction, from poorly integrated verbal and nonverbal communication to abnormalities in eye contact and body language.',
  },
  A3: {
    title: 'Relationships',
    description: 'Deficits in developing, maintaining, and understanding relationships, from difficulties adjusting behavior to difficulties making friends.',
  },
  B1: {
    title: 'Stereotyped/Repetitive Behaviors',
    description: 'Stereotyped or repetitive motor movements, use of objects, or speech (e.g., simple motor stereotypies, lining up toys, echolalia).',
  },
  B2: {
    title: 'Insistence on Sameness',
    description: 'Inflexible adherence to routines, ritualized patterns of verbal or nonverbal behavior, extreme distress at small changes.',
  },
  B3: {
    title: 'Restricted Interests',
    description: 'Highly restricted, fixated interests that are abnormal in intensity or focus.',
  },
  B4: {
    title: 'Sensory Reactivity',
    description: 'Hyper- or hyporeactivity to sensory input or unusual interest in sensory aspects of the environment.',
  },
};

export const SignalDetailModal: React.FC<SignalDetailModalProps> = ({
  signal,
  isOpen,
  onClose,
  onNavigateToTranscript,
  onVerify,
}) => {
  const [copied, setCopied] = React.useState(false);

  if (!signal) return null;

  const handleCopy = () => {
    const text = `Signal: ${signal.signal_name}\nEvidence: "${signal.evidence}"\nReasoning: ${signal.reasoning || 'N/A'}\nDSM-5: ${signal.dsm5_criteria || 'N/A'}`;
    navigator.clipboard.writeText(text);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const getSignificanceConfig = (significance: string) => {
    switch (significance) {
      case 'high':
        return {
          bg: 'bg-gradient-to-r from-red-500 to-rose-500',
          lightBg: 'bg-red-50 dark:bg-red-950/30',
          text: 'text-red-600 dark:text-red-400',
          icon: <AlertTriangle className="h-5 w-5" />,
          label: 'High Significance',
        };
      case 'moderate':
        return {
          bg: 'bg-gradient-to-r from-amber-500 to-orange-500',
          lightBg: 'bg-amber-50 dark:bg-amber-950/30',
          text: 'text-amber-600 dark:text-amber-400',
          icon: <Activity className="h-5 w-5" />,
          label: 'Moderate Significance',
        };
      default:
        return {
          bg: 'bg-gradient-to-r from-green-500 to-emerald-500',
          lightBg: 'bg-green-50 dark:bg-green-950/30',
          text: 'text-green-600 dark:text-green-400',
          icon: <CheckCircle2 className="h-5 w-5" />,
          label: 'Low Significance',
        };
    }
  };

  const config = getSignificanceConfig(signal.clinical_significance);
  const dsm5Info = signal.dsm5_criteria ? DSM5_DESCRIPTIONS[signal.dsm5_criteria] : null;

  return (
    <AnimatePresence>
      {isOpen && (
        <>
          {/* Backdrop */}
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            onClick={onClose}
            className="fixed inset-0 z-50 bg-black/60 backdrop-blur-sm"
          />

          {/* Modal */}
          <motion.div
            initial={{ opacity: 0, scale: 0.95, y: 20 }}
            animate={{ opacity: 1, scale: 1, y: 0 }}
            exit={{ opacity: 0, scale: 0.95, y: 20 }}
            transition={{ type: 'spring', damping: 25, stiffness: 300 }}
            className="fixed inset-4 z-50 m-auto max-w-3xl max-h-[90vh] overflow-hidden rounded-3xl bg-white dark:bg-neutral-900 shadow-2xl"
          >
            {/* Header with gradient */}
            <div className={`relative ${config.bg} p-6 text-white`}>
              {/* Decorative circles */}
              <div className="absolute top-0 right-0 w-32 h-32 bg-white/10 rounded-full blur-2xl" />
              <div className="absolute bottom-0 left-0 w-24 h-24 bg-white/10 rounded-full blur-xl" />

              <div className="relative">
                <div className="flex items-start justify-between">
                  <div className="flex items-center gap-4">
                    <div className="flex h-14 w-14 items-center justify-center rounded-2xl bg-white/20 backdrop-blur-sm">
                      <Brain className="h-7 w-7" />
                    </div>
                    <div>
                      <p className="text-sm text-white/70 uppercase tracking-wide">Clinical Signal</p>
                      <h2 className="text-xl font-bold">{signal.signal_name}</h2>
                    </div>
                  </div>
                  <button
                    onClick={onClose}
                    className="flex h-10 w-10 items-center justify-center rounded-full bg-white/10 hover:bg-white/20 transition-colors"
                  >
                    <X className="h-5 w-5" />
                  </button>
                </div>

                <div className="mt-4 flex flex-wrap items-center gap-2">
                  {signal.dsm5_criteria && (
                    <Badge className="bg-white/20 text-white border-0 font-semibold">
                      {signal.dsm5_criteria}
                    </Badge>
                  )}
                  <Badge className="bg-white/20 text-white border-0 capitalize">
                    {signal.signal_type}
                  </Badge>
                  <Badge className="bg-white/20 text-white border-0">
                    {(signal.confidence * 100).toFixed(0)}% confidence
                  </Badge>
                </div>
              </div>
            </div>

            {/* Content */}
            <div className="overflow-y-auto max-h-[calc(90vh-200px)] p-6 space-y-6">
              {/* Evidence Quote */}
              <div className={`rounded-2xl ${config.lightBg} p-5`}>
                <div className="flex items-start gap-3">
                  <MessageSquareQuote className={`h-6 w-6 ${config.text} flex-shrink-0 mt-1`} />
                  <div className="flex-1">
                    <p className="text-sm font-medium text-neutral-500 dark:text-neutral-400 mb-2">
                      Evidence from Transcript
                    </p>
                    <blockquote className="text-lg text-neutral-800 dark:text-neutral-200 italic leading-relaxed">
                      "{signal.evidence}"
                    </blockquote>
                    {signal.transcript_line && (
                      <button
                        onClick={() => onNavigateToTranscript?.(signal.transcript_line!)}
                        className="mt-3 inline-flex items-center gap-1.5 text-sm text-blue-500 hover:text-blue-600 font-medium"
                      >
                        <Link2 className="h-4 w-4" />
                        View in transcript (Line {signal.transcript_line})
                      </button>
                    )}
                  </div>
                </div>
              </div>

              {/* Clinical Reasoning */}
              {signal.reasoning && (
                <div className="rounded-2xl border border-neutral-200 dark:border-neutral-700 p-5">
                  <div className="flex items-start gap-3">
                    <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-amber-100 dark:bg-amber-900/30">
                      <Lightbulb className="h-5 w-5 text-amber-600 dark:text-amber-400" />
                    </div>
                    <div className="flex-1">
                      <p className="text-sm font-semibold text-neutral-900 dark:text-white mb-2">
                        Clinical Reasoning
                      </p>
                      <p className="text-neutral-600 dark:text-neutral-400 leading-relaxed">
                        {signal.reasoning}
                      </p>
                    </div>
                  </div>
                </div>
              )}

              {/* DSM-5 Criterion Info */}
              {dsm5Info && (
                <div className="rounded-2xl border border-blue-200 dark:border-blue-800 bg-blue-50 dark:bg-blue-950/30 p-5">
                  <div className="flex items-start gap-3">
                    <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-blue-100 dark:bg-blue-900/50">
                      <Target className="h-5 w-5 text-blue-600 dark:text-blue-400" />
                    </div>
                    <div className="flex-1">
                      <p className="text-sm font-semibold text-blue-900 dark:text-blue-100 mb-1">
                        {signal.dsm5_criteria}: {dsm5Info.title}
                      </p>
                      <p className="text-sm text-blue-700 dark:text-blue-300">
                        {dsm5Info.description}
                      </p>
                    </div>
                  </div>
                </div>
              )}

              {/* Metadata Grid */}
              <div className="grid grid-cols-2 gap-4">
                <div className="rounded-2xl bg-neutral-50 dark:bg-neutral-800 p-4">
                  <p className="text-xs text-neutral-500 dark:text-neutral-400 uppercase tracking-wide mb-1">
                    Domain
                  </p>
                  <p className="text-sm font-semibold text-neutral-900 dark:text-white">
                    {signal.maps_to_domain.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase())}
                  </p>
                </div>
                <div className="rounded-2xl bg-neutral-50 dark:bg-neutral-800 p-4">
                  <p className="text-xs text-neutral-500 dark:text-neutral-400 uppercase tracking-wide mb-1">
                    Signal Type
                  </p>
                  <p className="text-sm font-semibold text-neutral-900 dark:text-white capitalize">
                    {signal.signal_type}
                  </p>
                </div>
              </div>

              {/* Confidence Visualization */}
              <div className="rounded-2xl border border-neutral-200 dark:border-neutral-700 p-5">
                <div className="flex items-center justify-between mb-3">
                  <p className="text-sm font-semibold text-neutral-900 dark:text-white">
                    Confidence Level
                  </p>
                  <span className="text-2xl font-bold text-neutral-900 dark:text-white">
                    {(signal.confidence * 100).toFixed(0)}%
                  </span>
                </div>
                <div className="relative h-3 w-full overflow-hidden rounded-full bg-neutral-100 dark:bg-neutral-800">
                  <motion.div
                    initial={{ width: 0 }}
                    animate={{ width: `${signal.confidence * 100}%` }}
                    transition={{ duration: 1, ease: 'easeOut' }}
                    className={`absolute inset-y-0 left-0 rounded-full ${config.bg}`}
                  />
                </div>
                <div className="mt-2 flex justify-between text-xs text-neutral-500">
                  <span>Low</span>
                  <span>High</span>
                </div>
              </div>
            </div>

            {/* Footer Actions */}
            <div className="border-t border-neutral-200 dark:border-neutral-700 p-4 bg-neutral-50 dark:bg-neutral-800/50">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={handleCopy}
                    className="gap-2"
                  >
                    {copied ? (
                      <>
                        <Check className="h-4 w-4 text-green-500" />
                        Copied!
                      </>
                    ) : (
                      <>
                        <Copy className="h-4 w-4" />
                        Copy Details
                      </>
                    )}
                  </Button>
                </div>
                <div className="flex items-center gap-2">
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={onClose}
                  >
                    Close
                  </Button>
                  {onVerify && (
                    <Button
                      size="sm"
                      onClick={() => onVerify(signal.id)}
                      className="gap-2 bg-green-600 hover:bg-green-700"
                    >
                      <CheckCircle2 className="h-4 w-4" />
                      Verify Signal
                    </Button>
                  )}
                </div>
              </div>
            </div>
          </motion.div>
        </>
      )}
    </AnimatePresence>
  );
};

export default SignalDetailModal;
