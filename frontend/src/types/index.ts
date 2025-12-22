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

export interface DiagnosticHypothesis {
  id: string;
  patient_id: string;
  condition_code: string;
  condition_name: string;
  evidence_strength: number;
  uncertainty: number;
  supporting_signals: number;
  contradicting_signals: number;
  trend?: 'increasing' | 'stable' | 'decreasing';
  explanation?: string;
  created_at: string;
  updated_at: string;
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
