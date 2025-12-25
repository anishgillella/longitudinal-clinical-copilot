'use client';

/**
 * Clinical Analytics Dashboard
 *
 * A stunning, Apple-inspired analytics visualization component
 * that presents clinical data with elegance and clarity.
 *
 * "Design is not just what it looks like and feels like.
 *  Design is how it works." - Steve Jobs
 */

import React, { useEffect, useState, useMemo, useRef } from 'react';
import { motion, AnimatePresence, useSpring, useTransform } from 'framer-motion';
import {
  Brain,
  Activity,
  Target,
  TrendingUp,
  AlertTriangle,
  CheckCircle2,
  ChevronRight,
  Sparkles,
  Eye,
  MessageSquareQuote,
  Lightbulb,
  Zap,
  Shield,
  ArrowUpRight,
  Info,
} from 'lucide-react';
import { Badge } from '@/components/ui/badge';
import { Progress } from '@/components/ui/progress';

// Types
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
}

interface DomainScore {
  domain_code: string;
  domain_name: string;
  score: number;
  confidence: number;
  evidence_count: number;
}

interface Hypothesis {
  condition_code: string;
  condition_name: string;
  evidence_strength: number;
  uncertainty: number;
  supporting_count: number;
  explanation?: string;
}

interface AnalyticsData {
  signals: Signal[];
  domainScores: DomainScore[];
  hypotheses: Hypothesis[];
  dsm5Coverage: Record<string, number>;
  dsm5Gaps: string[];
  summary?: string;
}

interface ClinicalAnalyticsDashboardProps {
  data: AnalyticsData;
  patientName: string;
  sessionType: string;
  onSignalClick?: (signal: Signal) => void;
  onHypothesisClick?: (hypothesis: Hypothesis) => void;
}

// DSM-5 Criteria Labels
const DSM5_LABELS: Record<string, string> = {
  A1: 'Social-Emotional Reciprocity',
  A2: 'Nonverbal Communication',
  A3: 'Relationships',
  B1: 'Stereotyped Behaviors',
  B2: 'Insistence on Sameness',
  B3: 'Restricted Interests',
  B4: 'Sensory Reactivity',
};

// Color schemes - Apple-inspired
const COLORS = {
  primary: {
    gradient: 'from-blue-500 via-purple-500 to-pink-500',
    solid: '#007AFF',
  },
  success: {
    gradient: 'from-green-400 to-emerald-500',
    solid: '#34C759',
  },
  warning: {
    gradient: 'from-orange-400 to-amber-500',
    solid: '#FF9500',
  },
  danger: {
    gradient: 'from-red-400 to-rose-500',
    solid: '#FF3B30',
  },
  neutral: {
    gradient: 'from-gray-400 to-gray-500',
    solid: '#8E8E93',
  },
};

// Animated number component - optimized with Framer Motion spring
// Uses GPU-accelerated animations instead of setInterval
const AnimatedNumber: React.FC<{ value: number; suffix?: string; decimals?: number }> = ({
  value,
  suffix = '',
  decimals = 0
}) => {
  const springValue = useSpring(0, { stiffness: 100, damping: 30 });
  const displayValue = useTransform(springValue, (v) => v.toFixed(decimals));
  const nodeRef = useRef<HTMLSpanElement>(null);

  useEffect(() => {
    springValue.set(value);
  }, [springValue, value]);

  useEffect(() => {
    const unsubscribe = displayValue.on('change', (v) => {
      if (nodeRef.current) {
        nodeRef.current.textContent = v + suffix;
      }
    });
    return () => unsubscribe();
  }, [displayValue, suffix]);

  return <span ref={nodeRef}>{value.toFixed(decimals)}{suffix}</span>;
};

// Circular progress indicator - Apple Watch style
const CircularProgress: React.FC<{
  value: number;
  size?: number;
  strokeWidth?: number;
  color?: string;
  label?: string;
  sublabel?: string;
}> = ({ value, size = 120, strokeWidth = 8, color = COLORS.primary.solid, label, sublabel }) => {
  const radius = (size - strokeWidth) / 2;
  const circumference = radius * 2 * Math.PI;
  const offset = circumference - (value / 100) * circumference;

  return (
    <div className="relative inline-flex items-center justify-center">
      <svg width={size} height={size} className="-rotate-90">
        {/* Background circle */}
        <circle
          cx={size / 2}
          cy={size / 2}
          r={radius}
          stroke="currentColor"
          strokeWidth={strokeWidth}
          fill="none"
          className="text-neutral-200 dark:text-neutral-700"
        />
        {/* Progress circle */}
        <motion.circle
          cx={size / 2}
          cy={size / 2}
          r={radius}
          stroke={color}
          strokeWidth={strokeWidth}
          fill="none"
          strokeLinecap="round"
          initial={{ strokeDashoffset: circumference }}
          animate={{ strokeDashoffset: offset }}
          transition={{ duration: 1.5, ease: 'easeOut' }}
          style={{
            strokeDasharray: circumference,
          }}
        />
      </svg>
      <div className="absolute flex flex-col items-center justify-center">
        <span className="text-2xl font-bold text-neutral-900 dark:text-white">
          <AnimatedNumber value={value} suffix="%" decimals={0} />
        </span>
        {label && (
          <span className="text-xs font-medium text-neutral-500">{label}</span>
        )}
        {sublabel && (
          <span className="text-[10px] text-neutral-400">{sublabel}</span>
        )}
      </div>
    </div>
  );
};

// Domain bar with Apple-style animation
const DomainBar: React.FC<{
  domain: DomainScore;
  delay?: number;
  onClick?: () => void;
}> = ({ domain, delay = 0, onClick }) => {
  const getColorByScore = (score: number) => {
    if (score >= 0.7) return 'from-red-500 to-orange-500';
    if (score >= 0.4) return 'from-amber-500 to-yellow-500';
    return 'from-green-500 to-emerald-500';
  };

  return (
    <motion.div
      initial={{ opacity: 0, x: -20 }}
      animate={{ opacity: 1, x: 0 }}
      transition={{ delay, duration: 0.5, ease: 'easeOut' }}
      className="group cursor-pointer"
      onClick={onClick}
    >
      <div className="flex items-center justify-between mb-2">
        <div className="flex items-center gap-2">
          <span className="text-sm font-medium text-neutral-700 dark:text-neutral-300 group-hover:text-neutral-900 dark:group-hover:text-white transition-colors">
            {domain.domain_name}
          </span>
          <Badge
            variant="outline"
            className="text-[10px] px-1.5 py-0 opacity-0 group-hover:opacity-100 transition-opacity"
          >
            {domain.evidence_count} signals
          </Badge>
        </div>
        <div className="flex items-center gap-2">
          <span className="text-sm font-semibold text-neutral-900 dark:text-white">
            {(domain.score * 100).toFixed(0)}%
          </span>
          <ChevronRight className="h-4 w-4 text-neutral-400 opacity-0 group-hover:opacity-100 transition-opacity" />
        </div>
      </div>
      <div className="relative h-2 w-full overflow-hidden rounded-full bg-neutral-100 dark:bg-neutral-800">
        <motion.div
          initial={{ width: 0 }}
          animate={{ width: `${domain.score * 100}%` }}
          transition={{ delay: delay + 0.2, duration: 0.8, ease: 'easeOut' }}
          className={`absolute inset-y-0 left-0 rounded-full bg-gradient-to-r ${getColorByScore(domain.score)}`}
        />
      </div>
      <div className="mt-1 flex items-center justify-between text-[10px] text-neutral-400">
        <span>Confidence: {(domain.confidence * 100).toFixed(0)}%</span>
      </div>
    </motion.div>
  );
};

// Signal card with elegant design
const SignalCard: React.FC<{
  signal: Signal;
  index: number;
  onClick?: () => void;
}> = ({ signal, index, onClick }) => {
  const getSignificanceStyle = (significance: string) => {
    switch (significance) {
      case 'high':
        return {
          bg: 'bg-red-50 dark:bg-red-950/30',
          border: 'border-red-200 dark:border-red-800',
          badge: 'bg-red-100 text-red-700 dark:bg-red-900/50 dark:text-red-300',
          icon: <AlertTriangle className="h-3 w-3" />,
        };
      case 'moderate':
        return {
          bg: 'bg-amber-50 dark:bg-amber-950/30',
          border: 'border-amber-200 dark:border-amber-800',
          badge: 'bg-amber-100 text-amber-700 dark:bg-amber-900/50 dark:text-amber-300',
          icon: <Activity className="h-3 w-3" />,
        };
      default:
        return {
          bg: 'bg-green-50 dark:bg-green-950/30',
          border: 'border-green-200 dark:border-green-800',
          badge: 'bg-green-100 text-green-700 dark:bg-green-900/50 dark:text-green-300',
          icon: <CheckCircle2 className="h-3 w-3" />,
        };
    }
  };

  const style = getSignificanceStyle(signal.clinical_significance);

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: index * 0.05, duration: 0.4 }}
      whileHover={{ scale: 1.02, y: -2 }}
      whileTap={{ scale: 0.98 }}
      onClick={onClick}
      className={`group relative cursor-pointer rounded-2xl border ${style.border} ${style.bg} p-4 transition-all duration-300 hover:shadow-lg hover:shadow-neutral-200/50 dark:hover:shadow-neutral-900/50`}
    >
      {/* Significance indicator */}
      <div className="absolute -left-1 top-4 h-8 w-1 rounded-full bg-gradient-to-b from-current to-transparent opacity-60"
           style={{ color: signal.clinical_significance === 'high' ? '#EF4444' : signal.clinical_significance === 'moderate' ? '#F59E0B' : '#22C55E' }}
      />

      <div className="flex items-start justify-between gap-3">
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 mb-2">
            <span className="font-semibold text-neutral-900 dark:text-white truncate">
              {signal.signal_name}
            </span>
          </div>

          <div className="flex flex-wrap items-center gap-2 mb-3">
            {signal.dsm5_criteria && (
              <Badge variant="outline" className="text-[10px] font-medium">
                {signal.dsm5_criteria}
              </Badge>
            )}
            <Badge variant="outline" className="text-[10px] capitalize">
              {signal.signal_type}
            </Badge>
            <span className={`inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-[10px] font-medium ${style.badge}`}>
              {style.icon}
              {signal.clinical_significance}
            </span>
          </div>

          {/* Quote */}
          <div className="relative pl-3 border-l-2 border-neutral-200 dark:border-neutral-700">
            <MessageSquareQuote className="absolute -left-2.5 top-0 h-4 w-4 bg-white dark:bg-neutral-900 text-neutral-400" />
            <p className="text-sm text-neutral-600 dark:text-neutral-400 italic line-clamp-2">
              "{signal.evidence}"
            </p>
          </div>

          {/* Reasoning - shown on hover */}
          {signal.reasoning && (
            <motion.div
              initial={{ opacity: 0, height: 0 }}
              whileHover={{ opacity: 1, height: 'auto' }}
              className="mt-3 overflow-hidden"
            >
              <div className="flex items-start gap-2 text-xs text-neutral-500 dark:text-neutral-400">
                <Lightbulb className="h-3.5 w-3.5 mt-0.5 flex-shrink-0 text-amber-500" />
                <span className="line-clamp-2">{signal.reasoning}</span>
              </div>
            </motion.div>
          )}
        </div>

        {/* Confidence indicator */}
        <div className="flex flex-col items-center">
          <CircularProgress
            value={signal.confidence * 100}
            size={48}
            strokeWidth={4}
            color={signal.confidence > 0.7 ? COLORS.success.solid : signal.confidence > 0.4 ? COLORS.warning.solid : COLORS.neutral.solid}
          />
        </div>
      </div>
    </motion.div>
  );
};

// Hypothesis card - Hero style
const HypothesisCard: React.FC<{
  hypothesis: Hypothesis;
  isPrimary?: boolean;
  index: number;
  onClick?: () => void;
}> = ({ hypothesis, isPrimary = false, index, onClick }) => {
  const getStrengthColor = (strength: number) => {
    if (strength >= 0.7) return 'from-blue-500 to-indigo-600';
    if (strength >= 0.4) return 'from-purple-500 to-violet-600';
    return 'from-gray-400 to-gray-500';
  };

  return (
    <motion.div
      initial={{ opacity: 0, scale: 0.95 }}
      animate={{ opacity: 1, scale: 1 }}
      transition={{ delay: index * 0.1, duration: 0.5 }}
      whileHover={{ y: -4 }}
      onClick={onClick}
      className={`relative overflow-hidden rounded-3xl cursor-pointer transition-all duration-300 ${
        isPrimary
          ? 'bg-gradient-to-br from-neutral-900 to-neutral-800 dark:from-neutral-100 dark:to-neutral-200 text-white dark:text-neutral-900 shadow-2xl'
          : 'bg-white dark:bg-neutral-900 border border-neutral-200 dark:border-neutral-800 hover:shadow-xl'
      }`}
    >
      {/* Decorative gradient orb */}
      {isPrimary && (
        <div className="absolute -top-20 -right-20 h-40 w-40 rounded-full bg-gradient-to-br from-blue-500/30 to-purple-500/30 blur-3xl" />
      )}

      <div className="relative p-6">
        {/* Header */}
        <div className="flex items-start justify-between mb-4">
          <div className="flex items-center gap-3">
            <div className={`flex h-12 w-12 items-center justify-center rounded-2xl bg-gradient-to-br ${getStrengthColor(hypothesis.evidence_strength)} shadow-lg`}>
              <Brain className="h-6 w-6 text-white" />
            </div>
            <div>
              {isPrimary && (
                <Badge className="mb-1 bg-white/20 text-white dark:bg-neutral-900/20 dark:text-neutral-900 border-0">
                  <Sparkles className="h-3 w-3 mr-1" />
                  Primary Hypothesis
                </Badge>
              )}
              <h3 className={`font-bold text-lg ${isPrimary ? '' : 'text-neutral-900 dark:text-white'}`}>
                {hypothesis.condition_name}
              </h3>
            </div>
          </div>
          <ArrowUpRight className={`h-5 w-5 ${isPrimary ? 'text-white/60' : 'text-neutral-400'} opacity-0 group-hover:opacity-100 transition-opacity`} />
        </div>

        {/* Metrics */}
        <div className="grid grid-cols-3 gap-4 mb-4">
          <div>
            <p className={`text-[10px] uppercase tracking-wide ${isPrimary ? 'text-white/60' : 'text-neutral-500'}`}>
              Evidence
            </p>
            <p className={`text-2xl font-bold ${isPrimary ? '' : 'text-neutral-900 dark:text-white'}`}>
              <AnimatedNumber value={hypothesis.evidence_strength * 100} suffix="%" decimals={0} />
            </p>
          </div>
          <div>
            <p className={`text-[10px] uppercase tracking-wide ${isPrimary ? 'text-white/60' : 'text-neutral-500'}`}>
              Certainty
            </p>
            <p className={`text-2xl font-bold ${isPrimary ? '' : 'text-neutral-900 dark:text-white'}`}>
              <AnimatedNumber value={(1 - hypothesis.uncertainty) * 100} suffix="%" decimals={0} />
            </p>
          </div>
          <div>
            <p className={`text-[10px] uppercase tracking-wide ${isPrimary ? 'text-white/60' : 'text-neutral-500'}`}>
              Signals
            </p>
            <p className={`text-2xl font-bold ${isPrimary ? '' : 'text-neutral-900 dark:text-white'}`}>
              {hypothesis.supporting_count}
            </p>
          </div>
        </div>

        {/* Progress bar */}
        <div className="relative h-2 w-full overflow-hidden rounded-full bg-white/20 dark:bg-neutral-800">
          <motion.div
            initial={{ width: 0 }}
            animate={{ width: `${hypothesis.evidence_strength * 100}%` }}
            transition={{ delay: 0.5, duration: 1, ease: 'easeOut' }}
            className={`absolute inset-y-0 left-0 rounded-full bg-gradient-to-r ${getStrengthColor(hypothesis.evidence_strength)}`}
          />
        </div>

        {/* Explanation */}
        {hypothesis.explanation && isPrimary && (
          <p className="mt-4 text-sm text-white/70 dark:text-neutral-600 line-clamp-2">
            {hypothesis.explanation}
          </p>
        )}
      </div>
    </motion.div>
  );
};

// DSM-5 Coverage visualization
const DSM5CoverageGrid: React.FC<{
  coverage: Record<string, number>;
  gaps: string[];
}> = ({ coverage, gaps }) => {
  const criteria = ['A1', 'A2', 'A3', 'B1', 'B2', 'B3', 'B4'];

  return (
    <div className="grid grid-cols-7 gap-2">
      {criteria.map((criterion, index) => {
        const count = coverage[criterion] || 0;
        const isGap = gaps.includes(criterion);
        const intensity = Math.min(count / 5, 1); // Normalize to max 5 signals

        return (
          <motion.div
            key={criterion}
            initial={{ opacity: 0, scale: 0 }}
            animate={{ opacity: 1, scale: 1 }}
            transition={{ delay: index * 0.05, duration: 0.3 }}
            className="relative group"
          >
            <div
              className={`aspect-square rounded-xl flex flex-col items-center justify-center transition-all duration-300 cursor-pointer hover:scale-110 ${
                isGap
                  ? 'bg-neutral-100 dark:bg-neutral-800 border-2 border-dashed border-neutral-300 dark:border-neutral-600'
                  : 'border border-transparent'
              }`}
              style={{
                background: isGap ? undefined : `rgba(59, 130, 246, ${0.1 + intensity * 0.6})`,
              }}
            >
              <span className={`text-xs font-bold ${isGap ? 'text-neutral-400' : 'text-blue-600 dark:text-blue-400'}`}>
                {criterion}
              </span>
              <span className={`text-lg font-bold ${isGap ? 'text-neutral-300 dark:text-neutral-600' : 'text-blue-700 dark:text-blue-300'}`}>
                {count}
              </span>
            </div>

            {/* Tooltip */}
            <div className="absolute -top-12 left-1/2 -translate-x-1/2 px-3 py-1.5 bg-neutral-900 dark:bg-white text-white dark:text-neutral-900 text-xs rounded-lg opacity-0 group-hover:opacity-100 transition-opacity pointer-events-none whitespace-nowrap z-10">
              {DSM5_LABELS[criterion]}
              <div className="absolute -bottom-1 left-1/2 -translate-x-1/2 w-2 h-2 bg-neutral-900 dark:bg-white rotate-45" />
            </div>
          </motion.div>
        );
      })}
    </div>
  );
};

// Main Dashboard Component
export const ClinicalAnalyticsDashboard: React.FC<ClinicalAnalyticsDashboardProps> = ({
  data,
  patientName,
  sessionType,
  onSignalClick,
  onHypothesisClick,
}) => {
  const [activeTab, setActiveTab] = useState<'overview' | 'signals' | 'domains' | 'hypotheses'>('overview');

  // Computed metrics
  const metrics = useMemo(() => ({
    totalSignals: data.signals.length,
    highSignificance: data.signals.filter(s => s.clinical_significance === 'high').length,
    averageConfidence: data.signals.length > 0
      ? data.signals.reduce((acc, s) => acc + s.confidence, 0) / data.signals.length
      : 0,
    coveragePercent: ((7 - data.dsm5Gaps.length) / 7) * 100,
  }), [data]);

  const primaryHypothesis = data.hypotheses[0];

  return (
    <div className="space-y-6">
      {/* Header with gradient background */}
      <motion.div
        initial={{ opacity: 0, y: -20 }}
        animate={{ opacity: 1, y: 0 }}
        className="relative overflow-hidden rounded-3xl bg-gradient-to-r from-neutral-900 via-neutral-800 to-neutral-900 dark:from-white dark:via-neutral-100 dark:to-white p-8"
      >
        {/* Decorative elements */}
        <div className="absolute top-0 right-0 w-96 h-96 bg-gradient-to-br from-blue-500/20 to-purple-500/20 rounded-full blur-3xl" />
        <div className="absolute bottom-0 left-0 w-64 h-64 bg-gradient-to-tr from-pink-500/20 to-orange-500/20 rounded-full blur-3xl" />

        <div className="relative">
          <div className="flex items-center gap-3 mb-2">
            <div className="flex h-10 w-10 items-center justify-center rounded-full bg-white/10 dark:bg-neutral-900/10">
              <Sparkles className="h-5 w-5 text-white dark:text-neutral-900" />
            </div>
            <div>
              <p className="text-sm text-white/60 dark:text-neutral-500">Clinical Analysis</p>
              <h1 className="text-2xl font-bold text-white dark:text-neutral-900">
                {patientName}
              </h1>
            </div>
          </div>

          {/* Quick stats */}
          <div className="mt-6 grid grid-cols-4 gap-6">
            <div>
              <p className="text-xs text-white/60 dark:text-neutral-500 uppercase tracking-wide">Signals</p>
              <p className="text-3xl font-bold text-white dark:text-neutral-900">
                <AnimatedNumber value={metrics.totalSignals} />
              </p>
            </div>
            <div>
              <p className="text-xs text-white/60 dark:text-neutral-500 uppercase tracking-wide">High Priority</p>
              <p className="text-3xl font-bold text-red-400 dark:text-red-500">
                <AnimatedNumber value={metrics.highSignificance} />
              </p>
            </div>
            <div>
              <p className="text-xs text-white/60 dark:text-neutral-500 uppercase tracking-wide">Avg Confidence</p>
              <p className="text-3xl font-bold text-white dark:text-neutral-900">
                <AnimatedNumber value={metrics.averageConfidence * 100} suffix="%" decimals={0} />
              </p>
            </div>
            <div>
              <p className="text-xs text-white/60 dark:text-neutral-500 uppercase tracking-wide">DSM-5 Coverage</p>
              <p className="text-3xl font-bold text-white dark:text-neutral-900">
                <AnimatedNumber value={metrics.coveragePercent} suffix="%" decimals={0} />
              </p>
            </div>
          </div>
        </div>
      </motion.div>

      {/* Tab navigation - iOS style */}
      <div className="flex items-center gap-1 p-1 bg-neutral-100 dark:bg-neutral-800 rounded-xl">
        {(['overview', 'signals', 'domains', 'hypotheses'] as const).map((tab) => (
          <button
            key={tab}
            onClick={() => setActiveTab(tab)}
            className={`flex-1 py-2.5 px-4 rounded-lg text-sm font-medium transition-all duration-200 ${
              activeTab === tab
                ? 'bg-white dark:bg-neutral-900 text-neutral-900 dark:text-white shadow-sm'
                : 'text-neutral-600 dark:text-neutral-400 hover:text-neutral-900 dark:hover:text-white'
            }`}
          >
            {tab.charAt(0).toUpperCase() + tab.slice(1)}
          </button>
        ))}
      </div>

      {/* Content */}
      <AnimatePresence mode="wait">
        {activeTab === 'overview' && (
          <motion.div
            key="overview"
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -20 }}
            className="grid grid-cols-1 lg:grid-cols-2 gap-6"
          >
            {/* Primary Hypothesis */}
            {primaryHypothesis && (
              <div className="lg:col-span-2">
                <HypothesisCard
                  hypothesis={primaryHypothesis}
                  isPrimary
                  index={0}
                  onClick={() => onHypothesisClick?.(primaryHypothesis)}
                />
              </div>
            )}

            {/* DSM-5 Coverage */}
            <div className="rounded-3xl bg-white dark:bg-neutral-900 border border-neutral-200 dark:border-neutral-800 p-6">
              <div className="flex items-center gap-2 mb-6">
                <Target className="h-5 w-5 text-blue-500" />
                <h3 className="font-semibold text-neutral-900 dark:text-white">DSM-5 Coverage</h3>
                {data.dsm5Gaps.length > 0 && (
                  <Badge variant="outline" className="ml-auto text-amber-600 border-amber-300">
                    {data.dsm5Gaps.length} gaps
                  </Badge>
                )}
              </div>
              <DSM5CoverageGrid coverage={data.dsm5Coverage} gaps={data.dsm5Gaps} />

              {data.dsm5Gaps.length > 0 && (
                <div className="mt-4 p-3 rounded-xl bg-amber-50 dark:bg-amber-950/30 border border-amber-200 dark:border-amber-800">
                  <div className="flex items-start gap-2">
                    <Info className="h-4 w-4 text-amber-600 mt-0.5 flex-shrink-0" />
                    <p className="text-xs text-amber-700 dark:text-amber-300">
                      Consider exploring: {data.dsm5Gaps.map(g => DSM5_LABELS[g]).join(', ')}
                    </p>
                  </div>
                </div>
              )}
            </div>

            {/* Domain Scores */}
            <div className="rounded-3xl bg-white dark:bg-neutral-900 border border-neutral-200 dark:border-neutral-800 p-6">
              <div className="flex items-center gap-2 mb-6">
                <Activity className="h-5 w-5 text-purple-500" />
                <h3 className="font-semibold text-neutral-900 dark:text-white">Domain Analysis</h3>
              </div>
              <div className="space-y-5">
                {data.domainScores.slice(0, 5).map((domain, i) => (
                  <DomainBar key={domain.domain_code} domain={domain} delay={i * 0.1} />
                ))}
              </div>
            </div>

            {/* Top Signals */}
            <div className="lg:col-span-2 rounded-3xl bg-white dark:bg-neutral-900 border border-neutral-200 dark:border-neutral-800 p-6">
              <div className="flex items-center justify-between mb-6">
                <div className="flex items-center gap-2">
                  <Zap className="h-5 w-5 text-amber-500" />
                  <h3 className="font-semibold text-neutral-900 dark:text-white">Key Signals</h3>
                </div>
                <button
                  onClick={() => setActiveTab('signals')}
                  className="text-sm text-blue-500 hover:text-blue-600 font-medium flex items-center gap-1"
                >
                  View all
                  <ChevronRight className="h-4 w-4" />
                </button>
              </div>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {data.signals
                  .filter(s => s.clinical_significance === 'high')
                  .slice(0, 4)
                  .map((signal, i) => (
                    <SignalCard
                      key={signal.id}
                      signal={signal}
                      index={i}
                      onClick={() => onSignalClick?.(signal)}
                    />
                  ))}
              </div>
            </div>
          </motion.div>
        )}

        {activeTab === 'signals' && (
          <motion.div
            key="signals"
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -20 }}
            className="grid grid-cols-1 md:grid-cols-2 gap-4"
          >
            {data.signals.map((signal, i) => (
              <SignalCard
                key={signal.id}
                signal={signal}
                index={i}
                onClick={() => onSignalClick?.(signal)}
              />
            ))}
          </motion.div>
        )}

        {activeTab === 'domains' && (
          <motion.div
            key="domains"
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -20 }}
            className="rounded-3xl bg-white dark:bg-neutral-900 border border-neutral-200 dark:border-neutral-800 p-6"
          >
            <div className="space-y-6">
              {data.domainScores.map((domain, i) => (
                <DomainBar key={domain.domain_code} domain={domain} delay={i * 0.1} />
              ))}
            </div>
          </motion.div>
        )}

        {activeTab === 'hypotheses' && (
          <motion.div
            key="hypotheses"
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -20 }}
            className="grid grid-cols-1 md:grid-cols-2 gap-4"
          >
            {data.hypotheses.map((hypothesis, i) => (
              <HypothesisCard
                key={hypothesis.condition_code}
                hypothesis={hypothesis}
                isPrimary={i === 0}
                index={i}
                onClick={() => onHypothesisClick?.(hypothesis)}
              />
            ))}
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
};

export default ClinicalAnalyticsDashboard;
