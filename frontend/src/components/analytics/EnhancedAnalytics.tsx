'use client';

/**
 * Enhanced Clinical Analytics Components
 *
 * These components provide:
 * - Confidence interval visualization with clinical-grade accuracy
 * - Reasoning chain drill-down for transparency
 * - Session delta tracking for longitudinal analysis
 * - Quick View / Full Analytics toggle
 * - Actionable gap suggestions with specific questions
 * - Trajectory charts for hypothesis evolution
 *
 * Follows clinical documentation standards and medical protocols.
 */

import React, { useState, useMemo } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
  ChevronDown,
  ChevronUp,
  TrendingUp,
  TrendingDown,
  Minus,
  AlertCircle,
  CheckCircle,
  HelpCircle,
  Clipboard,
  Brain,
  Target,
  FileText,
  Activity,
  ArrowRight,
  Info,
  Copy,
  Check,
} from 'lucide-react';
import { Badge } from '@/components/ui/badge';
// Local interface to match dashboard's Hypothesis type
interface LocalHypothesis {
  condition_code: string;
  condition_name: string;
  evidence_strength: number;
  uncertainty: number;
  confidence_interval_lower?: number;
  confidence_interval_upper?: number;
  reasoning_chain?: { steps: ReasoningStep[] };
  criterion_a_met?: boolean | null;
  criterion_a_count?: number;
  criterion_b_met?: boolean | null;
  criterion_b_count?: number;
  functional_impairment_documented?: boolean;
  developmental_period_documented?: boolean;
  last_session_delta?: number;
  sessions_since_stable?: number;
  supporting_count: number;
  explanation?: string;
  limitations?: string;
  trend?: 'increasing' | 'stable' | 'decreasing';
  history?: HypothesisHistoryEntry[];
}

interface ReasoningStep {
  step: string;
  contribution: number;
  running_total: number;
  signals_used?: string[];
  explanation: string;
}

interface HypothesisHistoryEntry {
  date: string;
  evidence_strength: number;
  uncertainty: number;
  confidence_interval_lower: number;
  confidence_interval_upper: number;
  delta?: number;
  session_id?: string;
}

// ============================================================================
// CONFIDENCE INTERVAL VISUALIZATION
// ============================================================================

interface ConfidenceIntervalBarProps {
  value: number;           // Point estimate (0-1)
  lower: number;           // Lower bound of CI (0-1)
  upper: number;           // Upper bound of CI (0-1)
  label?: string;
  showLabels?: boolean;
  height?: number;
  colorScheme?: 'blue' | 'green' | 'amber' | 'red';
}

export const ConfidenceIntervalBar: React.FC<ConfidenceIntervalBarProps> = ({
  value,
  lower,
  upper,
  label,
  showLabels = true,
  height = 24,
  colorScheme = 'blue',
}) => {
  const colors = {
    blue: { bar: 'bg-blue-500', range: 'bg-blue-200', text: 'text-blue-700' },
    green: { bar: 'bg-green-500', range: 'bg-green-200', text: 'text-green-700' },
    amber: { bar: 'bg-amber-500', range: 'bg-amber-200', text: 'text-amber-700' },
    red: { bar: 'bg-red-500', range: 'bg-red-200', text: 'text-red-700' },
  };

  const c = colors[colorScheme];

  return (
    <div className="w-full">
      {label && (
        <div className="flex items-center justify-between mb-1">
          <span className="text-sm font-medium text-neutral-700 dark:text-neutral-300">
            {label}
          </span>
          <span className={`text-sm font-semibold ${c.text}`}>
            {(value * 100).toFixed(0)}%
            <span className="text-xs font-normal text-neutral-500 ml-1">
              (95% CI: {(lower * 100).toFixed(0)}-{(upper * 100).toFixed(0)}%)
            </span>
          </span>
        </div>
      )}
      <div
        className="relative w-full bg-neutral-100 dark:bg-neutral-800 rounded-full overflow-hidden"
        style={{ height }}
      >
        {/* Confidence interval range (shaded area) */}
        <motion.div
          initial={{ width: 0, left: 0 }}
          animate={{
            width: `${(upper - lower) * 100}%`,
            left: `${lower * 100}%`
          }}
          transition={{ duration: 0.8, ease: 'easeOut' }}
          className={`absolute inset-y-0 ${c.range} opacity-60`}
        />

        {/* Point estimate line */}
        <motion.div
          initial={{ left: 0 }}
          animate={{ left: `${value * 100}%` }}
          transition={{ duration: 0.8, ease: 'easeOut' }}
          className={`absolute inset-y-0 w-1 ${c.bar} -ml-0.5`}
        />

        {/* Point estimate marker */}
        <motion.div
          initial={{ left: 0 }}
          animate={{ left: `${value * 100}%` }}
          transition={{ duration: 0.8, ease: 'easeOut' }}
          className={`absolute top-1/2 -translate-y-1/2 -translate-x-1/2 w-4 h-4 rounded-full ${c.bar} border-2 border-white shadow-md`}
        />

        {showLabels && (
          <>
            {/* Lower bound marker */}
            <motion.div
              initial={{ left: 0 }}
              animate={{ left: `${lower * 100}%` }}
              transition={{ duration: 0.8, ease: 'easeOut' }}
              className="absolute top-1/2 -translate-y-1/2 -translate-x-1/2"
            >
              <div className={`w-0.5 h-3 ${c.bar} opacity-50`} />
            </motion.div>

            {/* Upper bound marker */}
            <motion.div
              initial={{ left: 0 }}
              animate={{ left: `${upper * 100}%` }}
              transition={{ duration: 0.8, ease: 'easeOut' }}
              className="absolute top-1/2 -translate-y-1/2 -translate-x-1/2"
            >
              <div className={`w-0.5 h-3 ${c.bar} opacity-50`} />
            </motion.div>
          </>
        )}
      </div>
    </div>
  );
};

// ============================================================================
// REASONING CHAIN PANEL (Expandable drill-down)
// ============================================================================

interface ReasoningChainPanelProps {
  reasoningChain: ReasoningStep[];
  isExpanded?: boolean;
  onToggle?: () => void;
}

export const ReasoningChainPanel: React.FC<ReasoningChainPanelProps> = ({
  reasoningChain,
  isExpanded = false,
  onToggle,
}) => {
  const getStepColor = (contribution: number) => {
    if (contribution > 0) return 'text-green-600 bg-green-50 border-green-200';
    if (contribution < 0) return 'text-red-600 bg-red-50 border-red-200';
    return 'text-neutral-600 bg-neutral-50 border-neutral-200';
  };

  const getStepIcon = (step: string) => {
    switch (step) {
      case 'base_rate': return <Target className="h-4 w-4" />;
      case 'criterion_A_evidence': return <Brain className="h-4 w-4" />;
      case 'criterion_B_evidence': return <Activity className="h-4 w-4" />;
      case 'contradicting_evidence': return <AlertCircle className="h-4 w-4" />;
      case 'evidence_quality_adjustment': return <FileText className="h-4 w-4" />;
      case 'final_posterior': return <CheckCircle className="h-4 w-4" />;
      default: return <HelpCircle className="h-4 w-4" />;
    }
  };

  const formatStepName = (step: string) => {
    return step
      .replace(/_/g, ' ')
      .replace(/\b\w/g, c => c.toUpperCase());
  };

  return (
    <div className="rounded-xl border border-neutral-200 dark:border-neutral-700 overflow-hidden">
      <button
        onClick={onToggle}
        className="w-full flex items-center justify-between p-4 bg-neutral-50 dark:bg-neutral-800 hover:bg-neutral-100 dark:hover:bg-neutral-750 transition-colors"
      >
        <div className="flex items-center gap-2">
          <Brain className="h-5 w-5 text-purple-500" />
          <span className="font-medium text-neutral-900 dark:text-white">
            Clinical Reasoning Chain
          </span>
          <Badge variant="outline" className="text-xs">
            {reasoningChain.length} steps
          </Badge>
        </div>
        {isExpanded ? (
          <ChevronUp className="h-5 w-5 text-neutral-500" />
        ) : (
          <ChevronDown className="h-5 w-5 text-neutral-500" />
        )}
      </button>

      <AnimatePresence>
        {isExpanded && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: 'auto', opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.3 }}
            className="overflow-hidden"
          >
            <div className="p-4 space-y-3">
              {reasoningChain.map((step, index) => (
                <motion.div
                  key={step.step}
                  initial={{ x: -20, opacity: 0 }}
                  animate={{ x: 0, opacity: 1 }}
                  transition={{ delay: index * 0.1 }}
                  className={`flex items-start gap-3 p-3 rounded-lg border ${getStepColor(step.contribution)}`}
                >
                  <div className="mt-0.5">
                    {getStepIcon(step.step)}
                  </div>
                  <div className="flex-1">
                    <div className="flex items-center justify-between mb-1">
                      <span className="font-medium text-sm">
                        {formatStepName(step.step)}
                      </span>
                      <div className="flex items-center gap-2">
                        <span className={`text-sm font-semibold ${
                          step.contribution > 0 ? 'text-green-600' :
                          step.contribution < 0 ? 'text-red-600' : 'text-neutral-600'
                        }`}>
                          {step.contribution > 0 ? '+' : ''}{(step.contribution * 100).toFixed(0)}%
                        </span>
                        <ArrowRight className="h-3 w-3 text-neutral-400" />
                        <span className="text-sm font-bold text-neutral-900 dark:text-white">
                          {(step.running_total * 100).toFixed(0)}%
                        </span>
                      </div>
                    </div>
                    <p className="text-xs text-neutral-600 dark:text-neutral-400">
                      {step.explanation}
                    </p>
                    {step.signals_used && step.signals_used.length > 0 && (
                      <div className="mt-2 flex items-center gap-1 flex-wrap">
                        <span className="text-xs text-neutral-500">Signals:</span>
                        {step.signals_used.slice(0, 3).map((signalId, i) => (
                          <Badge key={i} variant="outline" className="text-[10px]">
                            {signalId.substring(0, 8)}...
                          </Badge>
                        ))}
                        {step.signals_used.length > 3 && (
                          <Badge variant="outline" className="text-[10px]">
                            +{step.signals_used.length - 3} more
                          </Badge>
                        )}
                      </div>
                    )}
                  </div>
                </motion.div>
              ))}
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
};

// ============================================================================
// DSM-5 CRITERIA CHECKLIST (Clinical readiness indicator)
// ============================================================================

interface DSM5ChecklistProps {
  criterionAMet: boolean | null;
  criterionACount: number;
  criterionBMet: boolean | null;
  criterionBCount: number;
  functionalImpairmentDocumented: boolean;
  developmentalPeriodDocumented: boolean;
}

export const DSM5Checklist: React.FC<DSM5ChecklistProps> = ({
  criterionAMet,
  criterionACount,
  criterionBMet,
  criterionBCount,
  functionalImpairmentDocumented,
  developmentalPeriodDocumented,
}) => {
  const getStatusIcon = (met: boolean | null | undefined, required: boolean = true) => {
    if (met === true) return <CheckCircle className="h-4 w-4 text-green-500" />;
    if (met === false) return <AlertCircle className="h-4 w-4 text-red-500" />;
    return <HelpCircle className="h-4 w-4 text-amber-500" />;
  };

  const getStatusText = (met: boolean | null | undefined) => {
    if (met === true) return 'Met';
    if (met === false) return 'Not met';
    return 'Pending';
  };

  const items = [
    {
      label: 'Criterion A (Social Communication)',
      sublabel: `${criterionACount}/3 areas documented`,
      required: '3/3 required',
      met: criterionAMet,
    },
    {
      label: 'Criterion B (Restricted/Repetitive)',
      sublabel: `${criterionBCount}/4 areas documented`,
      required: '2/4 required',
      met: criterionBMet,
    },
    {
      label: 'Functional Impairment',
      sublabel: 'Symptoms cause clinically significant impairment',
      required: 'Required',
      met: functionalImpairmentDocumented,
    },
    {
      label: 'Developmental Period',
      sublabel: 'Symptoms present in early development',
      required: 'Required',
      met: developmentalPeriodDocumented,
    },
  ];

  const allMet = items.every(item => item.met === true);
  const anyMissing = items.some(item => item.met !== true);

  return (
    <div className="rounded-xl border border-neutral-200 dark:border-neutral-700 p-4">
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-2">
          <FileText className="h-5 w-5 text-blue-500" />
          <span className="font-medium text-neutral-900 dark:text-white">
            DSM-5 Criteria Status
          </span>
        </div>
        <Badge
          variant="outline"
          className={allMet ? 'border-green-300 text-green-700' : 'border-amber-300 text-amber-700'}
        >
          {allMet ? 'Ready for diagnosis' : 'Assessment in progress'}
        </Badge>
      </div>

      <div className="space-y-3">
        {items.map((item, index) => (
          <div
            key={index}
            className="flex items-start gap-3 p-2 rounded-lg hover:bg-neutral-50 dark:hover:bg-neutral-800 transition-colors"
          >
            {getStatusIcon(item.met)}
            <div className="flex-1">
              <div className="flex items-center justify-between">
                <span className="text-sm font-medium text-neutral-900 dark:text-white">
                  {item.label}
                </span>
                <span className={`text-xs font-medium ${
                  item.met === true ? 'text-green-600' :
                  item.met === false ? 'text-red-600' : 'text-amber-600'
                }`}>
                  {getStatusText(item.met)}
                </span>
              </div>
              <div className="flex items-center justify-between mt-0.5">
                <span className="text-xs text-neutral-500">{item.sublabel}</span>
                <span className="text-xs text-neutral-400">{item.required}</span>
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};

// ============================================================================
// SESSION DELTA INDICATOR (What changed this session)
// ============================================================================

interface SessionDeltaProps {
  delta: number | null | undefined;
  sessionsSinceStable: number;
  trend: 'increasing' | 'stable' | 'decreasing' | undefined;
}

export const SessionDeltaIndicator: React.FC<SessionDeltaProps> = ({
  delta,
  sessionsSinceStable,
  trend,
}) => {
  if (delta === null || delta === undefined) {
    return (
      <div className="flex items-center gap-2 text-neutral-500">
        <Minus className="h-4 w-4" />
        <span className="text-sm">First session</span>
      </div>
    );
  }

  const isSignificant = Math.abs(delta) >= 0.05;
  const isPositive = delta > 0;

  return (
    <div className="flex items-center gap-3">
      <div className={`flex items-center gap-1 px-2 py-1 rounded-full text-sm font-medium ${
        isSignificant && isPositive ? 'bg-green-100 text-green-700' :
        isSignificant && !isPositive ? 'bg-red-100 text-red-700' :
        'bg-neutral-100 text-neutral-600'
      }`}>
        {trend === 'increasing' ? <TrendingUp className="h-4 w-4" /> :
         trend === 'decreasing' ? <TrendingDown className="h-4 w-4" /> :
         <Minus className="h-4 w-4" />}
        <span>
          {isPositive ? '+' : ''}{(delta * 100).toFixed(1)}%
        </span>
      </div>

      {sessionsSinceStable > 0 && (
        <span className="text-xs text-neutral-500">
          Stable for {sessionsSinceStable} session{sessionsSinceStable > 1 ? 's' : ''}
        </span>
      )}
    </div>
  );
};

// ============================================================================
// ACTIONABLE GAP SUGGESTIONS (What to ask next)
// ============================================================================

interface EvidenceGap {
  area: string;
  dsm5_criterion: string;
  priority: 'high' | 'medium' | 'low';
  impact_if_positive: string;
  impact_if_negative: string;
  suggested_questions: string[];
  suggested_observations: string[];
}

interface ActionableGapSuggestionsProps {
  gaps: EvidenceGap[];
  onCopyQuestions?: (questions: string[]) => void;
}

export const ActionableGapSuggestions: React.FC<ActionableGapSuggestionsProps> = ({
  gaps,
  onCopyQuestions,
}) => {
  const [copiedIndex, setCopiedIndex] = useState<number | null>(null);

  const handleCopy = (questions: string[], index: number) => {
    const text = questions.join('\n• ');
    navigator.clipboard.writeText('• ' + text);
    setCopiedIndex(index);
    setTimeout(() => setCopiedIndex(null), 2000);
    onCopyQuestions?.(questions);
  };

  const priorityColors = {
    high: 'border-red-200 bg-red-50 dark:border-red-800 dark:bg-red-950/30',
    medium: 'border-amber-200 bg-amber-50 dark:border-amber-800 dark:bg-amber-950/30',
    low: 'border-neutral-200 bg-neutral-50 dark:border-neutral-700 dark:bg-neutral-800',
  };

  const priorityBadge = {
    high: 'bg-red-100 text-red-700',
    medium: 'bg-amber-100 text-amber-700',
    low: 'bg-neutral-100 text-neutral-600',
  };

  // Sort by priority
  const sortedGaps = [...gaps].sort((a, b) => {
    const order = { high: 0, medium: 1, low: 2 };
    return order[a.priority] - order[b.priority];
  });

  return (
    <div className="space-y-3">
      <div className="flex items-center gap-2 mb-4">
        <Target className="h-5 w-5 text-purple-500" />
        <span className="font-medium text-neutral-900 dark:text-white">
          What to Explore Next
        </span>
        <Badge variant="outline" className="text-xs">
          {gaps.length} gap{gaps.length !== 1 ? 's' : ''}
        </Badge>
      </div>

      {sortedGaps.slice(0, 3).map((gap, index) => (
        <motion.div
          key={index}
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: index * 0.1 }}
          className={`rounded-xl border p-4 ${priorityColors[gap.priority]}`}
        >
          <div className="flex items-start justify-between mb-2">
            <div>
              <div className="flex items-center gap-2 mb-1">
                <Badge variant="outline" className="text-xs">
                  {gap.dsm5_criterion}
                </Badge>
                <Badge className={`text-xs ${priorityBadge[gap.priority]}`}>
                  {gap.priority} priority
                </Badge>
              </div>
              <h4 className="font-medium text-neutral-900 dark:text-white">
                {gap.area}
              </h4>
            </div>
            <button
              onClick={() => handleCopy(gap.suggested_questions, index)}
              className="p-2 rounded-lg hover:bg-white/50 dark:hover:bg-black/20 transition-colors"
              title="Copy questions to clipboard"
            >
              {copiedIndex === index ? (
                <Check className="h-4 w-4 text-green-500" />
              ) : (
                <Copy className="h-4 w-4 text-neutral-400" />
              )}
            </button>
          </div>

          <div className="space-y-2 text-sm">
            <div className="flex items-start gap-2">
              <span className="text-neutral-500 shrink-0">If positive:</span>
              <span className="text-green-700 dark:text-green-400">{gap.impact_if_positive}</span>
            </div>
            <div className="flex items-start gap-2">
              <span className="text-neutral-500 shrink-0">If negative:</span>
              <span className="text-red-700 dark:text-red-400">{gap.impact_if_negative}</span>
            </div>
          </div>

          {gap.suggested_questions.length > 0 && (
            <div className="mt-3 pt-3 border-t border-neutral-200/50 dark:border-neutral-700/50">
              <span className="text-xs font-medium text-neutral-500 uppercase tracking-wide">
                Suggested Questions
              </span>
              <ul className="mt-2 space-y-1">
                {gap.suggested_questions.slice(0, 3).map((q, i) => (
                  <li key={i} className="text-sm text-neutral-700 dark:text-neutral-300 flex items-start gap-2">
                    <span className="text-neutral-400">•</span>
                    <span>{q}</span>
                  </li>
                ))}
              </ul>
            </div>
          )}
        </motion.div>
      ))}
    </div>
  );
};

// ============================================================================
// TRAJECTORY CHART (Hypothesis evolution over sessions)
// ============================================================================

interface TrajectoryChartProps {
  history: HypothesisHistoryEntry[];
  conditionName: string;
}

export const TrajectoryChart: React.FC<TrajectoryChartProps> = ({
  history,
  conditionName,
}) => {
  if (history.length < 2) {
    return (
      <div className="flex items-center justify-center h-32 text-neutral-500 text-sm">
        Need at least 2 sessions to show trajectory
      </div>
    );
  }

  const maxValue = Math.max(...history.map(h => h.confidence_interval_upper || h.evidence_strength + 0.1));
  const minValue = Math.min(...history.map(h => h.confidence_interval_lower || h.evidence_strength - 0.1));
  const range = Math.max(maxValue - minValue, 0.2);

  const width = 100 / (history.length - 1);

  const scaleY = (value: number) => {
    return 100 - ((value - minValue) / range) * 80 - 10; // 10% padding top/bottom
  };

  return (
    <div className="rounded-xl border border-neutral-200 dark:border-neutral-700 p-4">
      <div className="flex items-center gap-2 mb-4">
        <Activity className="h-5 w-5 text-blue-500" />
        <span className="font-medium text-neutral-900 dark:text-white">
          {conditionName} - Evidence Trajectory
        </span>
      </div>

      <div className="relative h-40 w-full">
        {/* Y-axis labels */}
        <div className="absolute left-0 top-0 bottom-0 w-10 flex flex-col justify-between text-xs text-neutral-400">
          <span>{(maxValue * 100).toFixed(0)}%</span>
          <span>{((maxValue + minValue) / 2 * 100).toFixed(0)}%</span>
          <span>{(minValue * 100).toFixed(0)}%</span>
        </div>

        {/* Chart area */}
        <svg className="absolute left-12 right-0 top-0 bottom-0" viewBox="0 0 100 100" preserveAspectRatio="none">
          {/* Confidence interval band */}
          <path
            d={`
              M 0 ${scaleY(history[0].confidence_interval_upper || history[0].evidence_strength + history[0].uncertainty)}
              ${history.map((h, i) =>
                `L ${i * width} ${scaleY(h.confidence_interval_upper || h.evidence_strength + h.uncertainty)}`
              ).join(' ')}
              ${[...history].reverse().map((h, i) =>
                `L ${(history.length - 1 - i) * width} ${scaleY(h.confidence_interval_lower || h.evidence_strength - h.uncertainty)}`
              ).join(' ')}
              Z
            `}
            fill="rgba(59, 130, 246, 0.15)"
            stroke="none"
          />

          {/* Main line */}
          <path
            d={`
              M 0 ${scaleY(history[0].evidence_strength)}
              ${history.map((h, i) => `L ${i * width} ${scaleY(h.evidence_strength)}`).join(' ')}
            `}
            fill="none"
            stroke="rgb(59, 130, 246)"
            strokeWidth="2"
            vectorEffect="non-scaling-stroke"
          />

          {/* Data points */}
          {history.map((h, i) => (
            <circle
              key={i}
              cx={i * width}
              cy={scaleY(h.evidence_strength)}
              r="3"
              fill="white"
              stroke="rgb(59, 130, 246)"
              strokeWidth="2"
              vectorEffect="non-scaling-stroke"
            />
          ))}
        </svg>

        {/* X-axis labels (session numbers) */}
        <div className="absolute left-12 right-0 bottom-0 flex justify-between text-xs text-neutral-400 transform translate-y-4">
          {history.map((_, i) => (
            <span key={i}>S{i + 1}</span>
          ))}
        </div>
      </div>

      <div className="mt-6 flex items-center justify-center gap-4 text-xs text-neutral-500">
        <div className="flex items-center gap-1">
          <div className="w-3 h-3 rounded-full bg-blue-500" />
          <span>Point estimate</span>
        </div>
        <div className="flex items-center gap-1">
          <div className="w-6 h-3 bg-blue-500/20 rounded" />
          <span>95% CI band</span>
        </div>
      </div>
    </div>
  );
};

// ============================================================================
// QUICK VIEW / FULL ANALYTICS TOGGLE
// ============================================================================

interface ViewToggleProps {
  mode: 'quick' | 'full';
  onModeChange: (mode: 'quick' | 'full') => void;
}

export const ViewToggle: React.FC<ViewToggleProps> = ({ mode, onModeChange }) => {
  return (
    <div className="flex items-center gap-1 p-1 bg-neutral-100 dark:bg-neutral-800 rounded-xl">
      <button
        onClick={() => onModeChange('quick')}
        className={`flex-1 py-2 px-4 rounded-lg text-sm font-medium transition-all duration-200 ${
          mode === 'quick'
            ? 'bg-white dark:bg-neutral-900 text-neutral-900 dark:text-white shadow-sm'
            : 'text-neutral-600 dark:text-neutral-400 hover:text-neutral-900 dark:hover:text-white'
        }`}
      >
        Quick View
      </button>
      <button
        onClick={() => onModeChange('full')}
        className={`flex-1 py-2 px-4 rounded-lg text-sm font-medium transition-all duration-200 ${
          mode === 'full'
            ? 'bg-white dark:bg-neutral-900 text-neutral-900 dark:text-white shadow-sm'
            : 'text-neutral-600 dark:text-neutral-400 hover:text-neutral-900 dark:hover:text-white'
        }`}
      >
        Full Analytics
      </button>
    </div>
  );
};

// ============================================================================
// QUICK VIEW SUMMARY (Plain language for clinicians)
// ============================================================================

interface QuickViewSummaryProps {
  hypothesis: LocalHypothesis;
  nextSessionFocus?: {
    primary_objective: string;
    specific_questions: string[];
    observations_needed: string[];
  };
}

export const QuickViewSummary: React.FC<QuickViewSummaryProps> = ({
  hypothesis,
  nextSessionFocus,
}) => {
  const getStrengthLabel = (strength: number) => {
    if (strength >= 0.7) return 'Strong';
    if (strength >= 0.5) return 'Moderate';
    if (strength >= 0.3) return 'Limited';
    return 'Minimal';
  };

  const getReadinessStatus = () => {
    const criteriaCount = (hypothesis.criterion_a_count || 0) + (hypothesis.criterion_b_count || 0);
    const hasFunc = hypothesis.functional_impairment_documented;
    const hasDev = hypothesis.developmental_period_documented;

    if (hypothesis.criterion_a_met && hypothesis.criterion_b_met && hasFunc && hasDev) {
      return { status: 'ready', label: 'Ready for clinical decision', color: 'text-green-600' };
    }
    if (criteriaCount >= 3) {
      return { status: 'near', label: 'Nearly complete', color: 'text-amber-600' };
    }
    return { status: 'ongoing', label: 'Assessment ongoing', color: 'text-blue-600' };
  };

  const readiness = getReadinessStatus();

  return (
    <div className="rounded-2xl bg-gradient-to-br from-neutral-50 to-white dark:from-neutral-900 dark:to-neutral-800 border border-neutral-200 dark:border-neutral-700 p-6">
      {/* Header */}
      <div className="flex items-start justify-between mb-4">
        <div>
          <h3 className="text-lg font-semibold text-neutral-900 dark:text-white">
            {hypothesis.condition_name}
          </h3>
          <p className={`text-sm font-medium ${readiness.color}`}>
            {readiness.label}
          </p>
        </div>
        <div className="text-right">
          <div className="text-2xl font-bold text-neutral-900 dark:text-white">
            {(hypothesis.evidence_strength * 100).toFixed(0)}%
          </div>
          <div className="text-xs text-neutral-500">
            {getStrengthLabel(hypothesis.evidence_strength)} evidence
          </div>
        </div>
      </div>

      {/* Confidence Range (simplified) */}
      <div className="mb-4">
        <ConfidenceIntervalBar
          value={hypothesis.evidence_strength}
          lower={hypothesis.confidence_interval_lower ?? Math.max(0, hypothesis.evidence_strength - hypothesis.uncertainty)}
          upper={hypothesis.confidence_interval_upper ?? Math.min(1, hypothesis.evidence_strength + hypothesis.uncertainty)}
          showLabels={false}
          height={8}
        />
        <div className="flex justify-between text-xs text-neutral-500 mt-1">
          <span>Range: {((hypothesis.confidence_interval_lower ?? Math.max(0, hypothesis.evidence_strength - hypothesis.uncertainty)) * 100).toFixed(0)}%</span>
          <span>{((hypothesis.confidence_interval_upper ?? Math.min(1, hypothesis.evidence_strength + hypothesis.uncertainty)) * 100).toFixed(0)}%</span>
        </div>
      </div>

      {/* Key status items */}
      <div className="grid grid-cols-2 gap-3 mb-4">
        <div className="flex items-center gap-2">
          {hypothesis.criterion_a_met ?
            <CheckCircle className="h-4 w-4 text-green-500" /> :
            <HelpCircle className="h-4 w-4 text-amber-500" />
          }
          <span className="text-sm text-neutral-600 dark:text-neutral-400">
            Criterion A ({hypothesis.criterion_a_count || 0}/3)
          </span>
        </div>
        <div className="flex items-center gap-2">
          {hypothesis.criterion_b_met ?
            <CheckCircle className="h-4 w-4 text-green-500" /> :
            <HelpCircle className="h-4 w-4 text-amber-500" />
          }
          <span className="text-sm text-neutral-600 dark:text-neutral-400">
            Criterion B ({hypothesis.criterion_b_count || 0}/4)
          </span>
        </div>
      </div>

      {/* Session delta */}
      {hypothesis.last_session_delta !== undefined && hypothesis.last_session_delta !== null && (
        <div className="mb-4 p-3 rounded-lg bg-neutral-100 dark:bg-neutral-800">
          <span className="text-xs text-neutral-500 uppercase tracking-wide">Last Session</span>
          <SessionDeltaIndicator
            delta={hypothesis.last_session_delta}
            sessionsSinceStable={hypothesis.sessions_since_stable || 0}
            trend={hypothesis.trend}
          />
        </div>
      )}

      {/* Next session focus */}
      {nextSessionFocus && (
        <div className="pt-4 border-t border-neutral-200 dark:border-neutral-700">
          <div className="flex items-center gap-2 mb-2">
            <Target className="h-4 w-4 text-purple-500" />
            <span className="text-sm font-medium text-neutral-900 dark:text-white">
              Next Session Focus
            </span>
          </div>
          <p className="text-sm text-neutral-600 dark:text-neutral-400">
            {nextSessionFocus.primary_objective}
          </p>
        </div>
      )}
    </div>
  );
};

export default {
  ConfidenceIntervalBar,
  ReasoningChainPanel,
  DSM5Checklist,
  SessionDeltaIndicator,
  ActionableGapSuggestions,
  TrajectoryChart,
  ViewToggle,
  QuickViewSummary,
};
