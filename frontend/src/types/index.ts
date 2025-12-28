// Core Types for Clinical Copilot

export interface Clinician {
  id: string;
  email: string;
  first_name: string;
  last_name: string;
  license_number?: string;
  specialty?: string;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface Patient {
  id: string;
  clinician_id: string;
  first_name: string;
  last_name: string;
  date_of_birth: string;
  gender?: string;
  email?: string;
  phone?: string;
  primary_concern?: string;
  referral_source?: string;
  intake_date?: string;
  status: 'active' | 'inactive' | 'archived';
  created_at: string;
  updated_at: string;
}

export interface VoiceSession {
  id: string;
  patient_id: string;
  clinician_id: string;
  vapi_call_id?: string;
  vapi_assistant_id: string;
  session_type: 'intake' | 'checkin' | 'targeted_probe';
  status: 'pending' | 'active' | 'completed' | 'failed';
  scheduled_at?: string;
  started_at?: string;
  ended_at?: string;
  duration_seconds?: number;
  completion_reason?: string;
  summary?: string;
  key_topics?: Record<string, unknown>;
  created_at: string;
  updated_at: string;
}

export interface Transcript {
  id: string;
  session_id: string;
  role: 'assistant' | 'user';
  content: string;
  timestamp_ms?: number;
  speech_speed?: number;
  pause_duration_ms?: number;
  energy_level?: number;
  created_at: string;
}

// Reasoning chain step for clinical transparency
export interface ReasoningStep {
  step: string;
  contribution: number;
  running_total: number;
  signals_used?: string[];
  explanation: string;
}

// DSM-5 criterion status
export interface CriterionDetail {
  status: 'met' | 'partial' | 'not_met' | 'not_assessed';
  evidence: string;
}

export interface DSM5CriteriaStatus {
  criterion_a_met: boolean | null;
  criterion_a_details: {
    A1_status: string;
    A1_evidence: string;
    A2_status: string;
    A2_evidence: string;
    A3_status: string;
    A3_evidence: string;
  };
  criterion_b_met: boolean | null;
  criterion_b_details: {
    B1_status: string;
    B1_evidence: string;
    B2_status: string;
    B2_evidence: string;
    B3_status: string;
    B3_evidence: string;
    B4_status: string;
    B4_evidence: string;
  };
  functional_impairment_documented: boolean;
  functional_impairment_evidence: string;
  developmental_period_documented: boolean;
  developmental_period_evidence: string;
}

// Differential diagnosis consideration
export interface DifferentialConsideration {
  condition: string;
  likelihood: number;
  confidence_interval: [number, number];
  reasoning: string;
  key_differentiating_features: string[];
  assessment_recommendations: string[];
}

export interface DiagnosticHypothesis {
  id: string;
  patient_id: string;
  condition_code: string;
  condition_name: string;
  evidence_strength: number;
  uncertainty: number;
  // NEW: Confidence interval (95% CI)
  confidence_interval_lower: number;
  confidence_interval_upper: number;
  // NEW: Reasoning chain for clinical transparency
  reasoning_chain?: { steps: ReasoningStep[] };
  // NEW: Evidence quality metrics
  evidence_quality_score?: number;
  gold_standard_evidence_count?: number;
  // NEW: DSM-5 criteria tracking
  criterion_a_met?: boolean | null;
  criterion_a_count?: number;
  criterion_b_met?: boolean | null;
  criterion_b_count?: number;
  functional_impairment_documented?: boolean;
  developmental_period_documented?: boolean;
  // NEW: Session delta tracking
  last_session_delta?: number;
  sessions_since_stable?: number;
  // NEW: Differential diagnosis
  differential_considerations?: DifferentialConsideration[];
  supporting_signals: number;
  contradicting_signals: number;
  trend?: 'increasing' | 'stable' | 'decreasing';
  explanation?: string;
  limitations?: string;
  created_at: string;
  updated_at: string;
}

// Hypothesis history for trajectory visualization
export interface HypothesisHistoryEntry {
  date: string;
  evidence_strength: number;
  uncertainty: number;
  confidence_interval_lower: number;
  confidence_interval_upper: number;
  delta?: number;
  session_id?: string;
}

export interface AssessmentProgress {
  id: string;
  patient_id: string;
  status: 'not_started' | 'initial_assessment' | 'ongoing' | 'near_completion' | 'completed' | 'on_hold';
  overall_completeness: number;
  total_sessions: number;
  intake_completed: boolean;
  last_session_date?: string;
  domains_explored: number;
  domains_total: number;
  signals_collected: number;
}

export interface DashboardMetrics {
  total_patients: number;
  active_patients: number;
  sessions_this_week: number;
  sessions_this_month: number;
  assessments_in_progress: number;
  high_confidence_hypotheses: number;
  active_concerns: number;
  urgent_concerns: number;
}

export interface TimelineEvent {
  id: string;
  patient_id: string;
  session_id?: string;
  event_type: string;
  category: string;
  title: string;
  description: string;
  occurred_at: string;
  significance: 'low' | 'moderate' | 'high' | 'critical';
  created_at: string;
}
