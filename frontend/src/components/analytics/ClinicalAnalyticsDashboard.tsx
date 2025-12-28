'use client';

/**
 * Clinical Analytics Dashboard
 *
 * A premium, clinician-focused analytics experience.
 * Design philosophy: Show what matters, hide complexity until needed.
 * Every pixel serves a purpose.
 */

import React, { useState, useMemo } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
  Brain,
  Activity,
  Target,
  TrendingUp,
  TrendingDown,
  Minus,
  ChevronRight,
  ChevronDown,
  Sparkles,
  Zap,
  ArrowRight,
  Check,
  AlertCircle,
  Copy,
  Quote,
  Layers,
} from 'lucide-react';

// ============================================================================
// TYPES
// ============================================================================

interface Signal {
  id: string;
  signal_name: string;
  signal_type: string;
  evidence: string;
  reasoning?: string;
  confidence: number;
  clinical_significance: 'low' | 'moderate' | 'high';
  dsm5_criteria?: string;
  verbatim_quote?: string;
}

interface DomainScore {
  domain_code: string;
  domain_name: string;
  score: number;
  confidence: number;
  evidence_count: number;
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
}

interface EvidenceGap {
  area: string;
  dsm5_criterion: string;
  priority: 'high' | 'medium' | 'low';
  impact_if_positive: string;
  impact_if_negative: string;
  suggested_questions: string[];
  suggested_observations: string[];
}

interface Hypothesis {
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

interface NextSessionFocus {
  primary_objective: string;
  specific_questions: string[];
  observations_needed: string[];
}

interface AnalyticsData {
  signals: Signal[];
  domainScores: DomainScore[];
  hypotheses: Hypothesis[];
  dsm5Coverage: Record<string, number>;
  dsm5Gaps: string[];
  summary?: string;
  evidenceGaps?: EvidenceGap[];
  nextSessionFocus?: NextSessionFocus;
}

interface ClinicalAnalyticsDashboardProps {
  data: AnalyticsData;
  patientName: string;
  sessionType: string;
  onSignalClick?: (signal: Signal) => void;
  onHypothesisClick?: (hypothesis: Hypothesis) => void;
}

// ============================================================================
// DESIGN TOKENS
// ============================================================================

const colors = {
  // Primary palette - subtle, professional
  primary: {
    50: '#f0f9ff',
    100: '#e0f2fe',
    500: '#0ea5e9',
    600: '#0284c7',
    700: '#0369a1',
  },
  // Success - for met criteria, positive trends
  success: {
    light: '#ecfdf5',
    DEFAULT: '#10b981',
    dark: '#059669',
  },
  // Warning - for partial, attention needed
  warning: {
    light: '#fffbeb',
    DEFAULT: '#f59e0b',
    dark: '#d97706',
  },
  // Neutral - text, borders
  neutral: {
    50: '#fafafa',
    100: '#f5f5f5',
    200: '#e5e5e5',
    300: '#d4d4d4',
    400: '#a3a3a3',
    500: '#737373',
    600: '#525252',
    700: '#404040',
    800: '#262626',
    900: '#171717',
  },
};

// Animation variants for consistent feel
const fadeIn = {
  initial: { opacity: 0, y: 8 },
  animate: { opacity: 1, y: 0 },
  exit: { opacity: 0, y: -8 },
};

const stagger = {
  animate: {
    transition: {
      staggerChildren: 0.05,
    },
  },
};

// ============================================================================
// CONFIDENCE GAUGE - The hero visualization
// ============================================================================

interface ConfidenceGaugeProps {
  value: number;
  lower: number;
  upper: number;
  size?: 'sm' | 'md' | 'lg';
  showLabel?: boolean;
  label?: string;
}

const ConfidenceGauge: React.FC<ConfidenceGaugeProps> = ({
  value,
  lower,
  upper,
  size = 'md',
  showLabel = true,
  label,
}) => {
  const sizes = {
    sm: { width: 120, stroke: 8, fontSize: 18 },
    md: { width: 160, stroke: 10, fontSize: 28 },
    lg: { width: 200, stroke: 12, fontSize: 36 },
  };

  const { width, stroke, fontSize } = sizes[size];
  const radius = (width - stroke) / 2;
  const circumference = 2 * Math.PI * radius;

  // Arc calculations (270 degrees, starting from bottom-left)
  const arcLength = circumference * 0.75;
  const valueOffset = arcLength * (1 - value);
  const lowerOffset = arcLength * (1 - lower);
  const upperOffset = arcLength * (1 - upper);

  return (
    <div className="relative inline-flex flex-col items-center">
      <svg width={width} height={width * 0.85} className="transform -rotate-[135deg]">
        {/* Background track */}
        <circle
          cx={width / 2}
          cy={width / 2}
          r={radius}
          fill="none"
          stroke={colors.neutral[100]}
          strokeWidth={stroke}
          strokeDasharray={`${arcLength} ${circumference}`}
          strokeLinecap="round"
        />

        {/* Confidence interval band */}
        <motion.circle
          cx={width / 2}
          cy={width / 2}
          r={radius}
          fill="none"
          stroke={colors.primary[100]}
          strokeWidth={stroke + 4}
          strokeDasharray={`${arcLength * (upper - lower)} ${circumference}`}
          strokeDashoffset={-arcLength * lower}
          strokeLinecap="round"
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 0.3, duration: 0.5 }}
        />

        {/* Value arc */}
        <motion.circle
          cx={width / 2}
          cy={width / 2}
          r={radius}
          fill="none"
          stroke={colors.primary[500]}
          strokeWidth={stroke}
          strokeDasharray={`${arcLength} ${circumference}`}
          strokeLinecap="round"
          initial={{ strokeDashoffset: arcLength }}
          animate={{ strokeDashoffset: valueOffset }}
          transition={{ duration: 1, ease: 'easeOut', delay: 0.2 }}
        />
      </svg>

      {/* Center content */}
      <div className="absolute inset-0 flex flex-col items-center justify-center" style={{ paddingTop: width * 0.15 }}>
        <motion.span
          className="font-semibold text-neutral-900"
          style={{ fontSize }}
          initial={{ opacity: 0, scale: 0.8 }}
          animate={{ opacity: 1, scale: 1 }}
          transition={{ delay: 0.5, duration: 0.3 }}
        >
          {Math.round(value * 100)}%
        </motion.span>
        {showLabel && (
          <span className="text-xs text-neutral-500 mt-1">
            {label || `${Math.round(lower * 100)}–${Math.round(upper * 100)}%`}
          </span>
        )}
      </div>
    </div>
  );
};

// ============================================================================
// CRITERIA PROGRESS - Simple, scannable
// ============================================================================

interface CriteriaProgressProps {
  label: string;
  current: number;
  total: number;
  met: boolean | null | undefined;
}

const CriteriaProgress: React.FC<CriteriaProgressProps> = ({ label, current, total, met }) => {
  const percentage = (current / total) * 100;

  return (
    <div className="space-y-1.5">
      <div className="flex items-center justify-between">
        <span className="text-sm font-medium text-neutral-700">{label}</span>
        <div className="flex items-center gap-2">
          <span className="text-sm text-neutral-500">{current}/{total}</span>
          {met === true && <Check className="w-4 h-4 text-emerald-500" />}
          {met === false && <AlertCircle className="w-4 h-4 text-amber-500" />}
        </div>
      </div>
      <div className="h-2 bg-neutral-100 rounded-full overflow-hidden">
        <motion.div
          className={`h-full rounded-full ${met ? 'bg-emerald-500' : 'bg-sky-500'}`}
          initial={{ width: 0 }}
          animate={{ width: `${percentage}%` }}
          transition={{ duration: 0.8, ease: 'easeOut', delay: 0.2 }}
        />
      </div>
    </div>
  );
};

// ============================================================================
// TREND BADGE - Subtle, informative
// ============================================================================

interface TrendBadgeProps {
  delta: number | null | undefined;
  trend?: 'increasing' | 'stable' | 'decreasing';
}

const TrendBadge: React.FC<TrendBadgeProps> = ({ delta, trend }) => {
  if (delta === null || delta === undefined) return null;

  const isPositive = delta > 0.02;
  const isNegative = delta < -0.02;

  return (
    <span className={`
      inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium
      ${isPositive ? 'bg-emerald-50 text-emerald-700' : ''}
      ${isNegative ? 'bg-rose-50 text-rose-700' : ''}
      ${!isPositive && !isNegative ? 'bg-neutral-100 text-neutral-600' : ''}
    `}>
      {isPositive && <TrendingUp className="w-3 h-3" />}
      {isNegative && <TrendingDown className="w-3 h-3" />}
      {!isPositive && !isNegative && <Minus className="w-3 h-3" />}
      {delta > 0 ? '+' : ''}{Math.round(delta * 100)}%
    </span>
  );
};

// ============================================================================
// REASONING STEP - Clean, expandable
// ============================================================================

interface ReasoningStepItemProps {
  step: ReasoningStep;
  index: number;
  isLast: boolean;
}

const ReasoningStepItem: React.FC<ReasoningStepItemProps> = ({ step, index, isLast }) => {
  const isPositive = step.contribution > 0;
  const isNegative = step.contribution < 0;

  const formatStepName = (name: string) => {
    return name.split('_').map(w => w.charAt(0).toUpperCase() + w.slice(1)).join(' ');
  };

  return (
    <motion.div
      initial={{ opacity: 0, x: -10 }}
      animate={{ opacity: 1, x: 0 }}
      transition={{ delay: index * 0.05 }}
      className="relative"
    >
      {/* Connector line */}
      {!isLast && (
        <div className="absolute left-3 top-8 bottom-0 w-px bg-neutral-200" />
      )}

      <div className="flex items-start gap-3">
        {/* Step indicator */}
        <div className={`
          w-6 h-6 rounded-full flex items-center justify-center text-xs font-medium shrink-0
          ${step.step === 'final_posterior' ? 'bg-sky-500 text-white' : 'bg-neutral-100 text-neutral-600'}
        `}>
          {step.step === 'final_posterior' ? <Check className="w-3 h-3" /> : index + 1}
        </div>

        {/* Content */}
        <div className="flex-1 pb-4">
          <div className="flex items-center justify-between">
            <span className="text-sm font-medium text-neutral-900">
              {formatStepName(step.step)}
            </span>
            <div className="flex items-center gap-2 text-sm">
              <span className={`font-medium ${
                isPositive ? 'text-emerald-600' : isNegative ? 'text-rose-600' : 'text-neutral-500'
              }`}>
                {isPositive ? '+' : ''}{Math.round(step.contribution * 100)}%
              </span>
              <ArrowRight className="w-3 h-3 text-neutral-400" />
              <span className="font-semibold text-neutral-900">
                {Math.round(step.running_total * 100)}%
              </span>
            </div>
          </div>
          <p className="text-xs text-neutral-500 mt-0.5">{step.explanation}</p>
        </div>
      </div>
    </motion.div>
  );
};

// ============================================================================
// QUESTION CARD - For actionable gaps
// ============================================================================

interface QuestionCardProps {
  gap: EvidenceGap;
  onCopy: () => void;
  copied: boolean;
}

const QuestionCard: React.FC<QuestionCardProps> = ({ gap, onCopy, copied }) => {
  const priorityColors = {
    high: 'border-l-rose-500 bg-rose-50/30',
    medium: 'border-l-amber-500 bg-amber-50/30',
    low: 'border-l-neutral-300 bg-neutral-50/30',
  };

  return (
    <motion.div
      layout
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      className={`border-l-4 rounded-r-xl p-4 ${priorityColors[gap.priority]}`}
    >
      <div className="flex items-start justify-between mb-2">
        <div>
          <span className="text-xs font-medium text-neutral-500 uppercase tracking-wide">
            {gap.dsm5_criterion}
          </span>
          <h4 className="font-medium text-neutral-900">{gap.area}</h4>
        </div>
        <button
          onClick={onCopy}
          className="p-2 rounded-lg hover:bg-white/50 transition-colors"
          title="Copy questions"
        >
          {copied ? (
            <Check className="w-4 h-4 text-emerald-500" />
          ) : (
            <Copy className="w-4 h-4 text-neutral-400" />
          )}
        </button>
      </div>

      <div className="space-y-2">
        {gap.suggested_questions.slice(0, 2).map((q, i) => (
          <div key={i} className="flex items-start gap-2 text-sm text-neutral-600">
            <Quote className="w-3 h-3 mt-1 text-neutral-400 shrink-0" />
            <span>{q}</span>
          </div>
        ))}
      </div>
    </motion.div>
  );
};

// ============================================================================
// SIGNAL PILL - Compact, meaningful
// ============================================================================

interface SignalPillProps {
  signal: Signal;
  onClick?: () => void;
}

const SignalPill: React.FC<SignalPillProps> = ({ signal, onClick }) => {
  const significanceColors = {
    high: 'bg-rose-100 text-rose-700 border-rose-200',
    moderate: 'bg-amber-100 text-amber-700 border-amber-200',
    low: 'bg-neutral-100 text-neutral-600 border-neutral-200',
  };

  return (
    <motion.button
      onClick={onClick}
      whileHover={{ scale: 1.02 }}
      whileTap={{ scale: 0.98 }}
      className={`
        px-3 py-1.5 rounded-full border text-sm font-medium
        transition-shadow hover:shadow-sm
        ${significanceColors[signal.clinical_significance]}
      `}
    >
      {signal.signal_name}
    </motion.button>
  );
};

// ============================================================================
// DOMAIN BAR - Clean horizontal progress
// ============================================================================

interface DomainBarProps {
  domain: DomainScore;
  delay?: number;
}

const DomainBar: React.FC<DomainBarProps> = ({ domain, delay = 0 }) => {
  const getColor = (score: number) => {
    if (score >= 0.7) return 'bg-rose-500';
    if (score >= 0.4) return 'bg-amber-500';
    return 'bg-emerald-500';
  };

  return (
    <motion.div
      initial={{ opacity: 0, x: -10 }}
      animate={{ opacity: 1, x: 0 }}
      transition={{ delay }}
      className="group"
    >
      <div className="flex items-center justify-between mb-1.5">
        <span className="text-sm font-medium text-neutral-700 group-hover:text-neutral-900 transition-colors">
          {domain.domain_name}
        </span>
        <div className="flex items-center gap-2">
          <span className="text-sm text-neutral-500">{domain.evidence_count} signals</span>
          <span className="text-sm font-semibold text-neutral-900">
            {Math.round(domain.score * 100)}%
          </span>
        </div>
      </div>
      <div className="h-2 bg-neutral-100 rounded-full overflow-hidden">
        <motion.div
          className={`h-full rounded-full ${getColor(domain.score)}`}
          initial={{ width: 0 }}
          animate={{ width: `${domain.score * 100}%` }}
          transition={{ duration: 0.8, ease: 'easeOut', delay: delay + 0.1 }}
        />
      </div>
    </motion.div>
  );
};

// ============================================================================
// TRAJECTORY MINI - Sparkline-style chart
// ============================================================================

interface TrajectoryMiniProps {
  history: HypothesisHistoryEntry[];
}

const TrajectoryMini: React.FC<TrajectoryMiniProps> = ({ history }) => {
  if (history.length < 2) return null;

  const width = 120;
  const height = 40;
  const padding = 4;

  const values = history.map(h => h.evidence_strength);
  const min = Math.min(...values) - 0.1;
  const max = Math.max(...values) + 0.1;
  const range = max - min;

  const points = history.map((h, i) => ({
    x: padding + (i / (history.length - 1)) * (width - 2 * padding),
    y: padding + (1 - (h.evidence_strength - min) / range) * (height - 2 * padding),
  }));

  const pathD = points.map((p, i) => `${i === 0 ? 'M' : 'L'} ${p.x} ${p.y}`).join(' ');

  return (
    <svg width={width} height={height} className="text-sky-500">
      {/* Line */}
      <motion.path
        d={pathD}
        fill="none"
        stroke="currentColor"
        strokeWidth={2}
        strokeLinecap="round"
        strokeLinejoin="round"
        initial={{ pathLength: 0 }}
        animate={{ pathLength: 1 }}
        transition={{ duration: 1, ease: 'easeOut' }}
      />
      {/* End dot */}
      <motion.circle
        cx={points[points.length - 1].x}
        cy={points[points.length - 1].y}
        r={3}
        fill="currentColor"
        initial={{ scale: 0 }}
        animate={{ scale: 1 }}
        transition={{ delay: 0.8 }}
      />
    </svg>
  );
};

// ============================================================================
// DSM-5 GRID - Visual criteria coverage
// ============================================================================

interface DSM5GridProps {
  coverage: Record<string, number>;
  gaps: string[];
}

const DSM5Grid: React.FC<DSM5GridProps> = ({ coverage, gaps }) => {
  const criteria = [
    { code: 'A1', label: 'Reciprocity' },
    { code: 'A2', label: 'Nonverbal' },
    { code: 'A3', label: 'Relationships' },
    { code: 'B1', label: 'Stereotyped' },
    { code: 'B2', label: 'Sameness' },
    { code: 'B3', label: 'Interests' },
    { code: 'B4', label: 'Sensory' },
  ];

  return (
    <div className="grid grid-cols-7 gap-2">
      {criteria.map(({ code, label }) => {
        const count = coverage[code] || 0;
        const isGap = gaps.includes(code);

        return (
          <div
            key={code}
            className={`
              aspect-square rounded-lg flex flex-col items-center justify-center p-1
              transition-all duration-200
              ${count > 0 ? 'bg-sky-100 text-sky-700' : ''}
              ${isGap ? 'bg-amber-50 border-2 border-dashed border-amber-300 text-amber-600' : ''}
              ${count === 0 && !isGap ? 'bg-neutral-50 text-neutral-400' : ''}
            `}
          >
            <span className="text-xs font-bold">{code}</span>
            <span className="text-[10px] leading-tight text-center opacity-70">{label}</span>
            {count > 0 && (
              <span className="text-[10px] font-semibold mt-0.5">{count}</span>
            )}
          </div>
        );
      })}
    </div>
  );
};

// ============================================================================
// MAIN DASHBOARD
// ============================================================================

export const ClinicalAnalyticsDashboard: React.FC<ClinicalAnalyticsDashboardProps> = ({
  data,
  patientName,
  sessionType,
  onSignalClick,
  onHypothesisClick,
}) => {
  const [view, setView] = useState<'summary' | 'details'>('summary');
  const [expandedSection, setExpandedSection] = useState<string | null>(null);
  const [copiedGapIndex, setCopiedGapIndex] = useState<number | null>(null);

  // Primary hypothesis
  const primaryHypothesis = useMemo(() => {
    if (!data.hypotheses.length) return null;
    return [...data.hypotheses].sort((a, b) => b.evidence_strength - a.evidence_strength)[0];
  }, [data.hypotheses]);

  // High significance signals
  const keySignals = useMemo(() => {
    return data.signals.filter(s => s.clinical_significance === 'high').slice(0, 6);
  }, [data.signals]);

  // Top domains
  const topDomains = useMemo(() => {
    return [...data.domainScores].sort((a, b) => b.score - a.score).slice(0, 5);
  }, [data.domainScores]);

  // Copy questions to clipboard
  const handleCopyQuestions = (gap: EvidenceGap, index: number) => {
    const text = gap.suggested_questions.map(q => `• ${q}`).join('\n');
    navigator.clipboard.writeText(text);
    setCopiedGapIndex(index);
    setTimeout(() => setCopiedGapIndex(null), 2000);
  };

  // Calculate CI bounds
  const ciLower = primaryHypothesis?.confidence_interval_lower ??
    Math.max(0, (primaryHypothesis?.evidence_strength || 0) - (primaryHypothesis?.uncertainty || 0.2));
  const ciUpper = primaryHypothesis?.confidence_interval_upper ??
    Math.min(1, (primaryHypothesis?.evidence_strength || 0) + (primaryHypothesis?.uncertainty || 0.2));

  return (
    <div className="space-y-6 pb-8">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-semibold text-neutral-900">{patientName}</h1>
          <p className="text-neutral-500">{sessionType} Analysis</p>
        </div>

        {/* View Toggle */}
        <div className="flex items-center gap-1 p-1 bg-neutral-100 rounded-lg">
          <button
            onClick={() => setView('summary')}
            className={`px-4 py-2 rounded-md text-sm font-medium transition-all ${
              view === 'summary'
                ? 'bg-white text-neutral-900 shadow-sm'
                : 'text-neutral-600 hover:text-neutral-900'
            }`}
          >
            Summary
          </button>
          <button
            onClick={() => setView('details')}
            className={`px-4 py-2 rounded-md text-sm font-medium transition-all ${
              view === 'details'
                ? 'bg-white text-neutral-900 shadow-sm'
                : 'text-neutral-600 hover:text-neutral-900'
            }`}
          >
            Details
          </button>
        </div>
      </div>

      <AnimatePresence mode="wait">
        {view === 'summary' ? (
          <motion.div
            key="summary"
            {...fadeIn}
            className="space-y-6"
          >
            {/* Hero Card - Primary Hypothesis */}
            {primaryHypothesis && (
              <motion.div
                className="bg-white rounded-2xl border border-neutral-200 shadow-sm overflow-hidden"
                whileHover={{ boxShadow: '0 4px 20px rgba(0,0,0,0.08)' }}
              >
                <div className="p-6">
                  <div className="flex items-start justify-between">
                    {/* Left: Gauge + Info */}
                    <div className="flex items-start gap-6">
                      <ConfidenceGauge
                        value={primaryHypothesis.evidence_strength}
                        lower={ciLower}
                        upper={ciUpper}
                        size="lg"
                      />

                      <div className="pt-4">
                        <div className="flex items-center gap-2 mb-1">
                          <Sparkles className="w-4 h-4 text-sky-500" />
                          <span className="text-xs font-medium text-sky-600 uppercase tracking-wide">
                            Primary Hypothesis
                          </span>
                        </div>
                        <h2 className="text-xl font-semibold text-neutral-900 mb-2">
                          {primaryHypothesis.condition_name}
                        </h2>

                        <div className="flex items-center gap-3 mb-4">
                          <TrendBadge
                            delta={primaryHypothesis.last_session_delta}
                            trend={primaryHypothesis.trend}
                          />
                          {primaryHypothesis.history && primaryHypothesis.history.length >= 2 && (
                            <TrajectoryMini history={primaryHypothesis.history} />
                          )}
                        </div>

                        {/* Criteria Progress */}
                        <div className="grid grid-cols-2 gap-4 max-w-md">
                          <CriteriaProgress
                            label="Criterion A"
                            current={primaryHypothesis.criterion_a_count ?? 0}
                            total={3}
                            met={primaryHypothesis.criterion_a_met}
                          />
                          <CriteriaProgress
                            label="Criterion B"
                            current={primaryHypothesis.criterion_b_count ?? 0}
                            total={4}
                            met={primaryHypothesis.criterion_b_met}
                          />
                        </div>
                      </div>
                    </div>

                    {/* Right: Supporting counts */}
                    <div className="text-right">
                      <div className="text-3xl font-semibold text-neutral-900">
                        {primaryHypothesis.supporting_count}
                      </div>
                      <div className="text-sm text-neutral-500">signals</div>
                    </div>
                  </div>

                  {/* Explanation */}
                  {primaryHypothesis.explanation && (
                    <p className="mt-6 text-neutral-600 border-t border-neutral-100 pt-4">
                      {primaryHypothesis.explanation}
                    </p>
                  )}
                </div>

                {/* Expandable Reasoning Chain */}
                {primaryHypothesis.reasoning_chain?.steps && primaryHypothesis.reasoning_chain.steps.length > 0 && (
                  <div className="border-t border-neutral-100">
                    <button
                      onClick={() => setExpandedSection(expandedSection === 'reasoning' ? null : 'reasoning')}
                      className="w-full px-6 py-3 flex items-center justify-between text-sm font-medium text-neutral-600 hover:text-neutral-900 hover:bg-neutral-50 transition-colors"
                    >
                      <span className="flex items-center gap-2">
                        <Brain className="w-4 h-4" />
                        View Reasoning Chain
                      </span>
                      <ChevronDown
                        className={`w-4 h-4 transition-transform ${expandedSection === 'reasoning' ? 'rotate-180' : ''}`}
                      />
                    </button>

                    <AnimatePresence>
                      {expandedSection === 'reasoning' && (
                        <motion.div
                          initial={{ height: 0, opacity: 0 }}
                          animate={{ height: 'auto', opacity: 1 }}
                          exit={{ height: 0, opacity: 0 }}
                          transition={{ duration: 0.2 }}
                          className="overflow-hidden"
                        >
                          <div className="px-6 pb-6 space-y-0">
                            {primaryHypothesis.reasoning_chain.steps.map((step, i) => (
                              <ReasoningStepItem
                                key={step.step}
                                step={step}
                                index={i}
                                isLast={i === primaryHypothesis.reasoning_chain!.steps.length - 1}
                              />
                            ))}
                          </div>
                        </motion.div>
                      )}
                    </AnimatePresence>
                  </div>
                )}
              </motion.div>
            )}

            {/* Two-Column Layout */}
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
              {/* Left: What to Ask Next */}
              {data.evidenceGaps && data.evidenceGaps.length > 0 && (
                <div className="bg-white rounded-2xl border border-neutral-200 p-6">
                  <div className="flex items-center gap-2 mb-4">
                    <Target className="w-5 h-5 text-purple-500" />
                    <h3 className="font-semibold text-neutral-900">What to Ask Next</h3>
                  </div>

                  <div className="space-y-3">
                    {data.evidenceGaps
                      .sort((a, b) => {
                        const order = { high: 0, medium: 1, low: 2 };
                        return order[a.priority] - order[b.priority];
                      })
                      .slice(0, 3)
                      .map((gap, i) => (
                        <QuestionCard
                          key={i}
                          gap={gap}
                          onCopy={() => handleCopyQuestions(gap, i)}
                          copied={copiedGapIndex === i}
                        />
                      ))}
                  </div>
                </div>
              )}

              {/* Right: DSM-5 Coverage */}
              <div className="bg-white rounded-2xl border border-neutral-200 p-6">
                <div className="flex items-center justify-between mb-4">
                  <div className="flex items-center gap-2">
                    <Layers className="w-5 h-5 text-sky-500" />
                    <h3 className="font-semibold text-neutral-900">DSM-5 Coverage</h3>
                  </div>
                  {data.dsm5Gaps.length > 0 && (
                    <span className="text-xs font-medium px-2 py-1 bg-amber-100 text-amber-700 rounded-full">
                      {data.dsm5Gaps.length} gaps
                    </span>
                  )}
                </div>

                <DSM5Grid coverage={data.dsm5Coverage} gaps={data.dsm5Gaps} />

                {data.dsm5Gaps.length > 0 && (
                  <p className="mt-4 text-sm text-neutral-500">
                    Explore: {data.dsm5Gaps.join(', ')}
                  </p>
                )}
              </div>
            </div>

            {/* Key Signals */}
            {keySignals.length > 0 && (
              <div className="bg-white rounded-2xl border border-neutral-200 p-6">
                <div className="flex items-center justify-between mb-4">
                  <div className="flex items-center gap-2">
                    <Zap className="w-5 h-5 text-amber-500" />
                    <h3 className="font-semibold text-neutral-900">Key Signals</h3>
                  </div>
                  <button
                    onClick={() => setView('details')}
                    className="text-sm text-sky-600 hover:text-sky-700 font-medium flex items-center gap-1"
                  >
                    View all
                    <ChevronRight className="w-4 h-4" />
                  </button>
                </div>

                <div className="flex flex-wrap gap-2">
                  {keySignals.map((signal, i) => (
                    <SignalPill
                      key={`key-${signal.id}-${i}`}
                      signal={signal}
                      onClick={() => onSignalClick?.(signal)}
                    />
                  ))}
                </div>
              </div>
            )}
          </motion.div>
        ) : (
          <motion.div
            key="details"
            {...fadeIn}
            className="space-y-6"
          >
            {/* Domains */}
            <div className="bg-white rounded-2xl border border-neutral-200 p-6">
              <div className="flex items-center gap-2 mb-6">
                <Activity className="w-5 h-5 text-purple-500" />
                <h3 className="font-semibold text-neutral-900">Domain Analysis</h3>
              </div>

              <div className="space-y-4">
                {data.domainScores.map((domain, i) => (
                  <DomainBar key={`${domain.domain_code}-${i}`} domain={domain} delay={i * 0.05} />
                ))}
              </div>
            </div>

            {/* All Signals */}
            <div className="bg-white rounded-2xl border border-neutral-200 p-6">
              <div className="flex items-center gap-2 mb-4">
                <Zap className="w-5 h-5 text-amber-500" />
                <h3 className="font-semibold text-neutral-900">All Signals ({data.signals.length})</h3>
              </div>

              <div className="flex flex-wrap gap-2">
                {data.signals.map((signal, i) => (
                  <SignalPill
                    key={`${signal.id}-${i}`}
                    signal={signal}
                    onClick={() => onSignalClick?.(signal)}
                  />
                ))}
              </div>
            </div>

            {/* All Hypotheses */}
            {data.hypotheses.length > 1 && (
              <div className="bg-white rounded-2xl border border-neutral-200 p-6">
                <div className="flex items-center gap-2 mb-4">
                  <Brain className="w-5 h-5 text-sky-500" />
                  <h3 className="font-semibold text-neutral-900">All Hypotheses</h3>
                </div>

                <div className="space-y-3">
                  {data.hypotheses.map((hypothesis, i) => (
                    <motion.button
                      key={`${hypothesis.condition_code}-${i}`}
                      initial={{ opacity: 0, y: 10 }}
                      animate={{ opacity: 1, y: 0 }}
                      transition={{ delay: i * 0.05 }}
                      onClick={() => onHypothesisClick?.(hypothesis)}
                      className="w-full p-4 rounded-xl border border-neutral-200 hover:border-sky-200 hover:bg-sky-50/50 transition-all text-left group"
                    >
                      <div className="flex items-center justify-between">
                        <div>
                          <h4 className="font-medium text-neutral-900 group-hover:text-sky-700">
                            {hypothesis.condition_name}
                          </h4>
                          <p className="text-sm text-neutral-500">
                            {hypothesis.supporting_count} supporting signals
                          </p>
                        </div>
                        <div className="flex items-center gap-3">
                          <TrendBadge delta={hypothesis.last_session_delta} trend={hypothesis.trend} />
                          <ConfidenceGauge
                            value={hypothesis.evidence_strength}
                            lower={hypothesis.confidence_interval_lower ?? hypothesis.evidence_strength - hypothesis.uncertainty}
                            upper={hypothesis.confidence_interval_upper ?? hypothesis.evidence_strength + hypothesis.uncertainty}
                            size="sm"
                            showLabel={false}
                          />
                        </div>
                      </div>
                    </motion.button>
                  ))}
                </div>
              </div>
            )}
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
};

export default ClinicalAnalyticsDashboard;
