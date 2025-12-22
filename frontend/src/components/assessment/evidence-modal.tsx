'use client';

import { motion, AnimatePresence } from 'framer-motion';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
} from '@/components/ui/dialog';
import { Badge } from '@/components/ui/badge';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import {
  CheckCircle,
  XCircle,
  AlertCircle,
  MessageSquare,
  Brain,
  Eye,
  User,
  Lightbulb,
  TrendingUp,
  TrendingDown,
  Minus,
  ExternalLink,
} from 'lucide-react';
import { Progress } from '@/components/ui/progress';
import Link from 'next/link';

// Types for hypothesis evidence
interface LinkedEvidence {
  signal_id?: string;
  signal_name: string;
  evidence_type: 'observed' | 'self_reported' | 'inferred';
  quote: string;
  reasoning: string;
  session_id?: string;
  transcript_line?: number;
}

interface HypothesisDetail {
  id: string;
  condition_code: string;
  condition_name: string;
  evidence_strength: number;
  uncertainty: number;
  confidence_low: number;
  confidence_high: number;
  supporting_signals: number;
  contradicting_signals: number;
  trend: 'increasing' | 'stable' | 'decreasing';
  explanation: string;
  limitations?: string;
  supporting_evidence: LinkedEvidence[];
  contradicting_evidence: LinkedEvidence[];
}

interface EvidenceModalProps {
  isOpen: boolean;
  onClose: () => void;
  hypothesis: HypothesisDetail | null;
}

const evidenceTypeConfig = {
  observed: {
    icon: Eye,
    label: 'Observed in Speech',
    color: 'bg-green-100 text-green-700 dark:bg-green-950 dark:text-green-300',
    description: 'Directly observable in how the patient speaks',
  },
  self_reported: {
    icon: User,
    label: 'Self-Reported',
    color: 'bg-blue-100 text-blue-700 dark:bg-blue-950 dark:text-blue-300',
    description: 'Patient described their own experience',
  },
  inferred: {
    icon: Lightbulb,
    label: 'Inferred',
    color: 'bg-yellow-100 text-yellow-700 dark:bg-yellow-950 dark:text-yellow-300',
    description: 'Interpreted from context',
  },
};

const trendConfig = {
  increasing: {
    icon: TrendingUp,
    label: 'Increasing',
    color: 'text-green-500',
  },
  stable: {
    icon: Minus,
    label: 'Stable',
    color: 'text-neutral-400',
  },
  decreasing: {
    icon: TrendingDown,
    label: 'Decreasing',
    color: 'text-red-500',
  },
};

function EvidenceCard({
  evidence,
  type,
}: {
  evidence: LinkedEvidence;
  type: 'supporting' | 'contradicting';
}) {
  const config = evidenceTypeConfig[evidence.evidence_type] || evidenceTypeConfig.inferred;
  const Icon = config.icon;

  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      className="rounded-xl border border-neutral-200 p-4 dark:border-neutral-700"
    >
      <div className="flex items-start justify-between gap-3">
        <div className="flex items-start gap-3">
          <div
            className={`flex h-8 w-8 shrink-0 items-center justify-center rounded-lg ${
              type === 'supporting'
                ? 'bg-green-100 dark:bg-green-950'
                : 'bg-red-100 dark:bg-red-950'
            }`}
          >
            {type === 'supporting' ? (
              <CheckCircle className="h-4 w-4 text-green-600" />
            ) : (
              <XCircle className="h-4 w-4 text-red-600" />
            )}
          </div>
          <div className="flex-1">
            <div className="flex items-center gap-2">
              <span className="font-medium text-neutral-900 dark:text-white">
                {evidence.signal_name}
              </span>
              <Badge variant="secondary" className={config.color}>
                <Icon className="mr-1 h-3 w-3" />
                {config.label}
              </Badge>
            </div>

            {evidence.quote && (
              <blockquote className="mt-2 border-l-2 border-neutral-300 pl-3 text-sm italic text-neutral-600 dark:border-neutral-600 dark:text-neutral-400">
                "{evidence.quote}"
              </blockquote>
            )}

            {evidence.reasoning && (
              <p className="mt-2 text-sm text-neutral-600 dark:text-neutral-400">
                <span className="font-medium">Why this matters: </span>
                {evidence.reasoning}
              </p>
            )}

            {evidence.session_id && (
              <Link
                href={`/sessions/${evidence.session_id}`}
                className="mt-2 inline-flex items-center gap-1 text-xs text-blue-600 hover:underline"
              >
                View in session
                <ExternalLink className="h-3 w-3" />
              </Link>
            )}
          </div>
        </div>
      </div>
    </motion.div>
  );
}

export function EvidenceModal({ isOpen, onClose, hypothesis }: EvidenceModalProps) {
  if (!hypothesis) return null;

  const TrendIcon = hypothesis.trend
    ? trendConfig[hypothesis.trend].icon
    : Minus;
  const trendColor = hypothesis.trend
    ? trendConfig[hypothesis.trend].color
    : 'text-neutral-400';

  const confidencePercent = Math.round(hypothesis.evidence_strength * 100);

  return (
    <Dialog open={isOpen} onOpenChange={onClose}>
      <DialogContent className="max-h-[90vh] max-w-2xl overflow-hidden p-0">
        <DialogHeader className="border-b border-neutral-200 p-6 dark:border-neutral-700">
          <div className="flex items-start justify-between">
            <div>
              <DialogTitle className="flex items-center gap-2 text-xl">
                {hypothesis.condition_name}
                <TrendIcon className={`h-5 w-5 ${trendColor}`} />
              </DialogTitle>
              <DialogDescription className="mt-1">
                Evidence-based hypothesis analysis
              </DialogDescription>
            </div>
            <div className="text-right">
              <div className="text-3xl font-bold text-neutral-900 dark:text-white">
                {confidencePercent}%
              </div>
              <div className="text-xs text-neutral-500">
                confidence ({hypothesis.confidence_low * 100}% - {hypothesis.confidence_high * 100}%)
              </div>
            </div>
          </div>

          <div className="mt-4">
            <Progress value={confidencePercent} className="h-2" />
            <div className="mt-2 flex items-center justify-between text-xs text-neutral-500">
              <span className="flex items-center gap-1 text-green-600">
                <CheckCircle className="h-3 w-3" />
                {hypothesis.supporting_signals} supporting
              </span>
              <span className="flex items-center gap-1 text-red-500">
                <XCircle className="h-3 w-3" />
                {hypothesis.contradicting_signals} contradicting
              </span>
            </div>
          </div>
        </DialogHeader>

        <ScrollArea className="max-h-[calc(90vh-200px)]">
          <div className="p-6">
            {/* Explanation */}
            <div className="mb-6">
              <h4 className="mb-2 flex items-center gap-2 font-semibold text-neutral-900 dark:text-white">
                <Brain className="h-4 w-4 text-purple-500" />
                AI Reasoning
              </h4>
              <p className="text-sm text-neutral-600 dark:text-neutral-400">
                {hypothesis.explanation || 'No detailed explanation available.'}
              </p>
            </div>

            {/* Limitations */}
            {hypothesis.limitations && (
              <div className="mb-6 rounded-lg border border-amber-200 bg-amber-50 p-4 dark:border-amber-900 dark:bg-amber-950">
                <h4 className="mb-1 flex items-center gap-2 font-semibold text-amber-800 dark:text-amber-200">
                  <AlertCircle className="h-4 w-4" />
                  Assessment Limitations
                </h4>
                <p className="text-sm text-amber-700 dark:text-amber-300">
                  {hypothesis.limitations}
                </p>
              </div>
            )}

            {/* Evidence Tabs */}
            <Tabs defaultValue="supporting" className="mt-4">
              <TabsList className="grid w-full grid-cols-2">
                <TabsTrigger value="supporting" className="gap-2">
                  <CheckCircle className="h-4 w-4 text-green-500" />
                  Supporting ({hypothesis.supporting_evidence.length})
                </TabsTrigger>
                <TabsTrigger value="contradicting" className="gap-2">
                  <XCircle className="h-4 w-4 text-red-500" />
                  Contradicting ({hypothesis.contradicting_evidence.length})
                </TabsTrigger>
              </TabsList>

              <TabsContent value="supporting" className="mt-4 space-y-3">
                <AnimatePresence>
                  {hypothesis.supporting_evidence.length > 0 ? (
                    hypothesis.supporting_evidence.map((evidence, index) => (
                      <EvidenceCard
                        key={evidence.signal_id || index}
                        evidence={evidence}
                        type="supporting"
                      />
                    ))
                  ) : (
                    <div className="py-8 text-center text-sm text-neutral-500">
                      No supporting evidence has been recorded yet.
                    </div>
                  )}
                </AnimatePresence>
              </TabsContent>

              <TabsContent value="contradicting" className="mt-4 space-y-3">
                <AnimatePresence>
                  {hypothesis.contradicting_evidence.length > 0 ? (
                    hypothesis.contradicting_evidence.map((evidence, index) => (
                      <EvidenceCard
                        key={evidence.signal_id || index}
                        evidence={evidence}
                        type="contradicting"
                      />
                    ))
                  ) : (
                    <div className="py-8 text-center text-sm text-neutral-500">
                      No contradicting evidence has been recorded.
                    </div>
                  )}
                </AnimatePresence>
              </TabsContent>
            </Tabs>

            {/* Evidence Type Legend */}
            <div className="mt-6 rounded-lg border border-neutral-200 p-4 dark:border-neutral-700">
              <h4 className="mb-3 text-sm font-semibold text-neutral-900 dark:text-white">
                Evidence Types Explained
              </h4>
              <div className="space-y-2">
                {Object.entries(evidenceTypeConfig).map(([key, config]) => {
                  const Icon = config.icon;
                  return (
                    <div key={key} className="flex items-center gap-2 text-xs">
                      <Badge variant="secondary" className={config.color}>
                        <Icon className="mr-1 h-3 w-3" />
                        {config.label}
                      </Badge>
                      <span className="text-neutral-500">{config.description}</span>
                    </div>
                  );
                })}
              </div>
            </div>
          </div>
        </ScrollArea>
      </DialogContent>
    </Dialog>
  );
}

// Export types for use in other components
export type { HypothesisDetail, LinkedEvidence };
