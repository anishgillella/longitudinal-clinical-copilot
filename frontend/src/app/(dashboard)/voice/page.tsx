'use client';

import { useState, useCallback, useEffect, useRef } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
  Mic,
  MicOff,
  Phone,
  PhoneOff,
  Settings,
  User,
  Clock,
  AlertCircle,
  CheckCircle2,
  Loader2,
  ChevronRight,
  FileText,
  BarChart3,
  Brain,
  ArrowLeft,
  Calendar,
  MessageSquare,
  Target,
  Sparkles,
  ListChecks,
  Info,
  Lightbulb,
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Card } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Progress } from '@/components/ui/progress';
import { Textarea } from '@/components/ui/textarea';
import { Label } from '@/components/ui/label';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { VoiceVisualizer } from '@/components/voice/voice-visualizer';
import { TranscriptPanel } from '@/components/voice/transcript-panel';
import { useVapi } from '@/hooks/use-vapi';
import { ClinicalAnalyticsDashboard, SignalDetailModal } from '@/components/analytics';

interface Message {
  id: string;
  role: 'assistant' | 'user';
  content: string;
  timestamp: Date;
  isFinal: boolean;
}

interface Signal {
  id: string;
  signal_type: string;
  signal_name: string;
  evidence: string;
  evidence_type: string;
  reasoning: string;
  maps_to_domain: string;
  intensity: number;
  confidence: number;
  clinical_significance: string;
  clinician_verified: boolean | null;
}

interface DomainScore {
  domain_code: string;
  domain_name: string;
  raw_score: number;
  normalized_score: number;
  confidence: number;
  evidence_count: number;
  previous_score: number | null;
  score_change: number | null;
}

interface Hypothesis {
  id: string;
  condition_code: string;
  condition_name: string;
  evidence_strength: number;
  uncertainty: number;
  trend: string;
  explanation: string;
}

interface AnalysisResult {
  session_id: string;
  patient_id: string;
  processing_status: {
    status: string;
    has_signals: boolean;
    has_domain_scores: boolean;
    has_summary: boolean;
  };
  signals: Signal[];
  domain_scores: DomainScore[];
  summary: {
    brief_summary: string | null;
    detailed_summary: string | null;
    key_topics: { topics: string[] } | null;
    emotional_tone: string | null;
    clinical_observations: string | null;
    follow_up_suggestions: { suggestions: string[] } | null;
    concerns: string[] | null;
  } | null;
  hypotheses: Hypothesis[];
}

interface PreSessionCheckIn {
  patientStatus: 'worse' | 'same' | 'okay' | 'good' | 'great';
  notableEvents: string;
  focusArea: string;
}

type SessionPhase = 'setup' | 'checkin' | 'active' | 'processing' | 'review';
type ReviewTab = 'analytics' | 'transcript' | 'summary' | 'actions';

// Patient interface for type safety
interface Patient {
  id: string;
  name: string;
  age: number;
  lastSession: string | null;
}

// Domain display names
const domainNames: Record<string, string> = {
  A1: 'Social-Emotional Reciprocity',
  A2: 'Nonverbal Communication',
  A3: 'Relationships',
  B1: 'Stereotyped/Repetitive Behaviors',
  B2: 'Insistence on Sameness',
  B3: 'Restricted Interests',
  B4: 'Sensory Processing',
};

// Focus areas for sessions
const focusAreas = [
  { value: 'general', label: 'General check-in' },
  { value: 'school', label: 'School/social situations' },
  { value: 'sensory', label: 'Sensory concerns' },
  { value: 'routines', label: 'Routines/transitions' },
  { value: 'communication', label: 'Communication patterns' },
  { value: 'behavior', label: 'Behavioral concerns' },
];

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

export default function VoiceSessionPage() {
  const [phase, setPhase] = useState<SessionPhase>('setup');
  const [patients, setPatients] = useState<Patient[]>([]);
  const [selectedPatient, setSelectedPatient] = useState<Patient | null>(null);
  const [sessionType, setSessionType] = useState<'intake' | 'checkin' | 'targeted_probe'>('checkin');
  const [messages, setMessages] = useState<Message[]>([]);
  const [isMuted, setIsMuted] = useState(false);
  const [callDuration, setCallDuration] = useState(0);
  const [sessionId, setSessionId] = useState<string | null>(null);
  const sessionIdRef = useRef<string | null>(null); // Ref to access sessionId in callbacks
  const isPollingRef = useRef<boolean>(false); // Track if polling is active
  const isMountedRef = useRef<boolean>(true); // Track if component is mounted
  const [analysisResult, setAnalysisResult] = useState<AnalysisResult | null>(null);
  const [processingProgress, setProcessingProgress] = useState(0);
  const [clinicianNotes, setClinicianNotes] = useState('');
  const [verifiedSignals, setVerifiedSignals] = useState<Set<string>>(new Set());
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [patientsLoading, setPatientsLoading] = useState(true);

  // Signal detail modal state
  const [selectedSignal, setSelectedSignal] = useState<Signal | null>(null);
  const [isSignalModalOpen, setIsSignalModalOpen] = useState(false);

  // Review phase tab state
  const [reviewTab, setReviewTab] = useState<ReviewTab>('analytics');

  // Pre-session check-in state
  const [checkIn, setCheckIn] = useState<PreSessionCheckIn>({
    patientStatus: 'okay',
    notableEvents: '',
    focusArea: 'general',
  });

  // Track component mount/unmount for cleanup
  useEffect(() => {
    isMountedRef.current = true;
    return () => {
      isMountedRef.current = false;
      isPollingRef.current = false; // Stop any active polling
    };
  }, []);

  // Fetch patients from API on mount
  useEffect(() => {
    const fetchPatients = async () => {
      try {
        const response = await fetch(`${API_BASE_URL}/api/v1/patients`);
        if (response.ok) {
          const data = await response.json();
          // Transform API response to Patient interface
          const transformedPatients: Patient[] = data.map((p: {
            id: string;
            first_name: string;
            last_name: string;
            date_of_birth: string;
          }) => {
            const birthDate = new Date(p.date_of_birth);
            const age = Math.floor((Date.now() - birthDate.getTime()) / (365.25 * 24 * 60 * 60 * 1000));
            return {
              id: p.id,
              name: `${p.first_name} ${p.last_name}`,
              age,
              lastSession: null, // TODO: fetch from sessions API
            };
          });
          setPatients(transformedPatients);

          // If no patients exist, create a test patient
          if (transformedPatients.length === 0) {
            await createTestPatient();
          }
        } else {
          console.error('Failed to fetch patients:', response.status);
          // Create test patient if API fails
          await createTestPatient();
        }
      } catch (err) {
        console.error('Error fetching patients:', err);
        // Create test patient on error
        await createTestPatient();
      } finally {
        setPatientsLoading(false);
      }
    };

    const createTestPatient = async () => {
      try {
        const response = await fetch(`${API_BASE_URL}/api/v1/patients`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            first_name: 'Alex',
            last_name: 'Thompson',
            date_of_birth: '2011-06-15', // Makes them ~13 years old
            gender: 'male',
            primary_concern: 'Social communication difficulties',
            status: 'active',
          }),
        });

        if (response.ok) {
          const newPatient = await response.json();
          setPatients([{
            id: newPatient.id,
            name: `${newPatient.first_name} ${newPatient.last_name}`,
            age: 13,
            lastSession: null,
          }]);
        }
      } catch (err) {
        console.error('Failed to create test patient:', err);
      }
    };

    fetchPatients();
  }, []);

  const handleTranscript = useCallback(
    (role: 'assistant' | 'user', text: string, isFinal: boolean) => {
      setMessages((prev) => {
        const existingIndex = prev.findIndex(
          (m) => m.role === role && !m.isFinal
        );

        if (existingIndex >= 0) {
          const updated = [...prev];
          updated[existingIndex] = {
            ...updated[existingIndex],
            content: text,
            isFinal,
          };
          return updated;
        }

        return [
          ...prev,
          {
            id: `${Date.now()}-${role}`,
            role,
            content: text,
            timestamp: new Date(),
            isFinal,
          },
        ];
      });
    },
    []
  );

  const handleCallStart = useCallback(() => {
    setMessages([]);
    setCallDuration(0);
    setPhase('active');
    const interval = setInterval(() => {
      setCallDuration((d) => d + 1);
    }, 1000);
    return () => clearInterval(interval);
  }, []);

  const handleCallEnd = useCallback(() => {
    setPhase('processing');
    setProcessingProgress(0);

    // Simulate processing progress while waiting for real analysis
    let progress = 0;
    const interval = setInterval(() => {
      progress += 5;
      setProcessingProgress(Math.min(progress, 95));
      if (progress >= 95) {
        clearInterval(interval);
      }
    }, 300);

    // Poll for analysis results
    pollForAnalysisResults();
  }, [sessionId]);

  const pollForAnalysisResults = async () => {
    // Use ref to get the current session ID (state may be stale in callbacks)
    const currentSessionId = sessionIdRef.current;

    if (!currentSessionId) {
      console.warn('[Analytics] No session ID - using mock data');
      await fetchMockAnalysisResults();
      return;
    }

    // Prevent multiple polling loops
    if (isPollingRef.current) {
      console.log('[Analytics] Already polling, skipping');
      return;
    }

    isPollingRef.current = true;
    console.log('[Analytics] Starting polling for session:', currentSessionId);
    const maxAttempts = 60; // Wait up to 2 minutes (60 * 2s)
    let attempts = 0;

    const poll = async () => {
      // Stop polling if component unmounted or polling was cancelled
      if (!isMountedRef.current || !isPollingRef.current) {
        console.log('[Analytics] Polling stopped (unmounted or cancelled)');
        return;
      }

      attempts++;
      try {
        const response = await fetch(`${API_BASE_URL}/api/v1/sessions/${currentSessionId}/analysis`);

        if (response.ok) {
          const data = await response.json();
          const status = data.processing_status?.status;

          if (status === 'processed') {
            console.log('[Analytics] Processing complete - signals:', data.signals?.length || 0);
            isPollingRef.current = false;
            if (isMountedRef.current) {
              setProcessingProgress(100);
              setAnalysisResult(data);
              setPhase('review');
            }
            return;
          } else {
            // Log progress every 5 attempts
            if (attempts % 5 === 0) {
              console.log('[Analytics] Still processing... attempt', attempts, 'status:', status);
            }
          }
        } else if (response.status === 404) {
          console.warn('[Analytics] Session not found');
        }

        if (attempts < maxAttempts && isMountedRef.current && isPollingRef.current) {
          setTimeout(poll, 2000);
        } else if (attempts >= maxAttempts) {
          console.warn('[Analytics] Timeout after', maxAttempts, 'attempts - using mock data');
          isPollingRef.current = false;
          await fetchMockAnalysisResults();
        }
      } catch (err) {
        console.error('[Analytics] Polling error:', err);
        if (attempts >= maxAttempts) {
          isPollingRef.current = false;
          await fetchMockAnalysisResults();
        } else if (isMountedRef.current && isPollingRef.current) {
          setTimeout(poll, 2000);
        }
      }
    };

    poll();
  };

  const fetchMockAnalysisResults = async () => {
    // Simulate processing delay
    await new Promise(resolve => setTimeout(resolve, 2000));

    // Don't update state if component unmounted
    if (!isMountedRef.current) return;

    setProcessingProgress(100);

    const mockAnalysis: AnalysisResult = {
      session_id: sessionId || 'mock-session-id',
      patient_id: selectedPatient?.id || '1',
      processing_status: {
        status: 'processed',
        has_signals: true,
        has_domain_scores: true,
        has_summary: true,
      },
      signals: [
        {
          id: '1',
          signal_type: 'behavioral',
          signal_name: 'Distress at routine changes',
          evidence: 'When they moved his desk at school, he had a complete meltdown',
          evidence_type: 'self_reported',
          reasoning: 'Parent describes significant distress response to environmental change, consistent with insistence on sameness',
          maps_to_domain: 'B2',
          intensity: 0.8,
          confidence: 0.85,
          clinical_significance: 'high',
          clinician_verified: null,
        },
        {
          id: '2',
          signal_type: 'sensory',
          signal_name: 'Auditory hypersensitivity',
          evidence: 'He covers his ears during fire drills and can\'t handle the cafeteria noise',
          evidence_type: 'self_reported',
          reasoning: 'Multiple examples of auditory sensitivity affecting daily functioning',
          maps_to_domain: 'B4',
          intensity: 0.75,
          confidence: 0.8,
          clinical_significance: 'high',
          clinician_verified: null,
        },
        {
          id: '3',
          signal_type: 'social',
          signal_name: 'Limited peer interaction',
          evidence: 'He prefers to play alone at recess',
          evidence_type: 'self_reported',
          reasoning: 'Preference for solitary play may indicate social interaction difficulties',
          maps_to_domain: 'A3',
          intensity: 0.5,
          confidence: 0.6,
          clinical_significance: 'moderate',
          clinician_verified: null,
        },
      ],
      domain_scores: [
        { domain_code: 'A1', domain_name: 'Social-Emotional Reciprocity', raw_score: 0.45, normalized_score: 0.45, confidence: 0.7, evidence_count: 2, previous_score: 0.42, score_change: 0.03 },
        { domain_code: 'A2', domain_name: 'Nonverbal Communication', raw_score: 0.38, normalized_score: 0.38, confidence: 0.6, evidence_count: 1, previous_score: null, score_change: null },
        { domain_code: 'A3', domain_name: 'Relationships', raw_score: 0.52, normalized_score: 0.52, confidence: 0.65, evidence_count: 3, previous_score: 0.48, score_change: 0.04 },
        { domain_code: 'B1', domain_name: 'Stereotyped Behaviors', raw_score: 0.32, normalized_score: 0.32, confidence: 0.5, evidence_count: 1, previous_score: null, score_change: null },
        { domain_code: 'B2', domain_name: 'Insistence on Sameness', raw_score: 0.82, normalized_score: 0.82, confidence: 0.85, evidence_count: 5, previous_score: 0.70, score_change: 0.12 },
        { domain_code: 'B3', domain_name: 'Restricted Interests', raw_score: 0.48, normalized_score: 0.48, confidence: 0.6, evidence_count: 2, previous_score: null, score_change: null },
        { domain_code: 'B4', domain_name: 'Sensory Processing', raw_score: 0.75, normalized_score: 0.75, confidence: 0.8, evidence_count: 4, previous_score: 0.68, score_change: 0.07 },
      ],
      summary: {
        brief_summary: 'Parent reports significant escalation in transition difficulties following a schedule change at school. Recovery time after meltdowns has increased (now ~2 hours). Sensory sensitivities in cafeteria continue.',
        detailed_summary: 'This check-in session focused on recent changes in the patient\'s behavior at school. The parent reported that a desk move triggered a prolonged meltdown, with recovery taking approximately two hours. Sensory sensitivities remain a significant challenge, particularly auditory stimuli in the cafeteria and during fire drills. Some positive notes include improved morning routine compliance at home.',
        key_topics: { topics: ['School transitions', 'Sensory sensitivities', 'Meltdown duration', 'Morning routines'] },
        emotional_tone: 'Parent appeared stressed but engaged',
        clinical_observations: 'Consistent pattern of difficulty with environmental changes. Sensory profile suggests auditory hypersensitivity.',
        follow_up_suggestions: { suggestions: ['Explore transition strategies', 'Consider occupational therapy evaluation', 'Discuss sensory accommodations with school'] },
        concerns: null,
      },
      hypotheses: [
        {
          id: '1',
          condition_code: 'asd_level_1',
          condition_name: 'ASD Level 1',
          evidence_strength: 0.78,
          uncertainty: 0.15,
          trend: 'stable',
          explanation: 'Pattern of restricted/repetitive behaviors and sensory sensitivities consistent with ASD Level 1. Social communication differences present but functional.',
        },
        {
          id: '2',
          condition_code: 'sensory_processing',
          condition_name: 'Sensory Processing Differences',
          evidence_strength: 0.72,
          uncertainty: 0.18,
          trend: 'increasing',
          explanation: 'Multiple sensory sensitivities affecting daily functioning, particularly auditory.',
        },
      ],
    };

    if (isMountedRef.current) {
      setAnalysisResult(mockAnalysis);
      setPhase('review');
    }
  };

  const { isCallActive, isSpeaking, volumeLevel, startCall, endCall, toggleMute, callId } =
    useVapi({
      onTranscript: handleTranscript,
      onCallStart: handleCallStart,
      onCallEnd: handleCallEnd,
    });

  const handleProceedToCheckIn = () => {
    if (!selectedPatient) return;
    setPhase('checkin');
  };

  const handleStartCall = async () => {
    if (!selectedPatient) return;
    setError(null);
    setIsLoading(true);

    // Determine interview mode based on patient age
    const interviewMode: 'teen' | 'parent' | 'adult' = selectedPatient.age >= 18 ? 'adult' : selectedPatient.age >= 13 ? 'teen' : 'parent';

    // Store session ID locally since setState is async
    let createdSessionId: string | null = null;

    try {
      // Create session in backend
      const response = await fetch(`${API_BASE_URL}/api/v1/sessions`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          patient_id: selectedPatient.id,
          session_type: sessionType,
          interview_mode: interviewMode,
          vapi_assistant_id: process.env.NEXT_PUBLIC_VAPI_ASSISTANT_ID,
          pre_session_notes: JSON.stringify(checkIn),
        }),
      });

      if (response.ok) {
        const session = await response.json();
        createdSessionId = session.id;
        setSessionId(session.id);
        sessionIdRef.current = session.id; // Update ref for callbacks
        console.log('[Session] Created with ID:', createdSessionId);
      } else {
        console.error('[Session] Failed to create:', response.status);
      }
    } catch (err) {
      console.error('[Session] Creation error:', err);
    }

    try {
      // Build VAPI template variables
      // Get focus area label for display
      const focusAreaLabel = focusAreas.find(f => f.value === checkIn.focusArea)?.label || checkIn.focusArea;

      const vapiVariables = {
        // Interviewee context
        interviewee_type: interviewMode,
        interviewee_is_parent: interviewMode === 'parent',
        interviewee_is_teen: interviewMode === 'teen',
        interviewee_is_adult: interviewMode === 'adult',

        // Patient information
        patient_name: selectedPatient.name.split(' ')[0], // First name
        patient_full_name: selectedPatient.name,
        patient_age: selectedPatient.age,

        // Session context
        session_type: sessionType,
        is_first_session: !selectedPatient.lastSession,
        focus_area: checkIn.focusArea,

        // These match the VAPI prompt template variables
        focus_areas: focusAreaLabel,
        previous_session_summary: selectedPatient.lastSession
          ? `Last session was on ${selectedPatient.lastSession}. ${checkIn.notableEvents ? `Notable events since then: ${checkIn.notableEvents}` : ''}`
          : 'This is the first session.',
        missing_information: 'Explore all domains - social communication, restricted interests, sensory sensitivities, developmental history.',

        // Behavioral adaptations
        use_concrete_language: interviewMode === 'teen',
        use_parent_perspective: interviewMode === 'parent',
      };

      const vapiCallId = await startCall({
        variables: vapiVariables,
      });

      // Link the VAPI call ID to the session (use local variable, not state)
      if (createdSessionId && vapiCallId) {
        try {
          const linkResponse = await fetch(`${API_BASE_URL}/api/v1/sessions/${createdSessionId}/link/${vapiCallId}`, {
            method: 'POST',
            headers: {
              'Content-Type': 'application/json',
            },
          });

          if (linkResponse.ok) {
            console.log('[Session] Linked to VAPI call:', vapiCallId);
          } else {
            console.error('[Session] Link failed:', linkResponse.status);
          }
        } catch (linkErr) {
          console.error('[Session] Link error:', linkErr);
        }
      } else {
        console.warn('[Session] Cannot link - missing IDs:', { createdSessionId, vapiCallId });
      }
    } catch (err) {
      console.error('[VAPI] Failed to start call:', err);
      setError('Failed to start voice session. Please check your microphone permissions.');
    } finally {
      setIsLoading(false);
    }
  };

  const handleEndCall = () => {
    endCall();
  };

  const handleToggleMute = () => {
    const newMutedState = toggleMute();
    setIsMuted(newMutedState ?? false);
  };

  const handleVerifySignal = async (signalId: string, verified: boolean) => {
    setVerifiedSignals(prev => {
      const newSet = new Set(prev);
      if (verified) {
        newSet.add(signalId);
      } else {
        newSet.delete(signalId);
      }
      return newSet;
    });

    // Send to backend
    if (sessionId) {
      try {
        await fetch(`${API_BASE_URL}/api/v1/sessions/${sessionId}/signals/${signalId}/verify`, {
          method: 'PATCH',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({ verified }),
        });
      } catch (err) {
        console.error('Failed to verify signal:', err);
      }
    }
  };

  const handleSaveAndComplete = async () => {
    setIsLoading(true);

    // Save clinician notes and verified signals using batch endpoint
    if (sessionId && verifiedSignals.size > 0) {
      try {
        // Use batch verification endpoint for much better performance
        await fetch(`${API_BASE_URL}/api/v1/sessions/${sessionId}/signals/verify-batch`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({
            signal_ids: Array.from(verifiedSignals),
            verified: true,
            clinician_notes: clinicianNotes,
          }),
        });
      } catch (err) {
        console.error('Failed to save:', err);
      }
    }

    // Reset state for next session
    setPhase('setup');
    setSelectedPatient(null);
    setMessages([]);
    setAnalysisResult(null);
    setClinicianNotes('');
    setVerifiedSignals(new Set());
    setCheckIn({ patientStatus: 'okay', notableEvents: '', focusArea: 'general' });
    setSessionId(null);
    setIsLoading(false);
  };

  const formatDuration = (seconds: number) => {
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
  };

  const sessionTypeLabels = {
    intake: 'Initial Intake',
    checkin: 'Check-in',
    targeted_probe: 'Targeted Probe',
  };

  const getScoreColor = (score: number) => {
    if (score >= 0.7) return 'bg-red-500';
    if (score >= 0.5) return 'bg-yellow-500';
    if (score >= 0.3) return 'bg-blue-500';
    return 'bg-gray-300';
  };

  const getSignificanceBadge = (significance: string) => {
    switch (significance) {
      case 'high':
        return <Badge className="bg-red-100 text-red-700">High</Badge>;
      case 'moderate':
        return <Badge className="bg-yellow-100 text-yellow-700">Moderate</Badge>;
      default:
        return <Badge className="bg-gray-100 text-gray-700">Low</Badge>;
    }
  };

  const statusEmojis = [
    { value: 'worse', emoji: '😟', label: 'Worse' },
    { value: 'same', emoji: '😐', label: 'Same' },
    { value: 'okay', emoji: '🙂', label: 'Okay' },
    { value: 'good', emoji: '😊', label: 'Good' },
    { value: 'great', emoji: '🌟', label: 'Great' },
  ];

  return (
    <div className="flex h-[calc(100vh-8rem)] gap-6">
      {/* Main Area */}
      <div className="flex flex-1 flex-col">
        <AnimatePresence mode="wait">
          {/* Setup Phase - Patient Selection */}
          {phase === 'setup' && (
            <motion.div
              key="setup"
              initial={{ opacity: 0, scale: 0.95 }}
              animate={{ opacity: 1, scale: 1 }}
              exit={{ opacity: 0, scale: 0.95 }}
              className="flex flex-1 flex-col items-center justify-center"
            >
              <Card className="w-full max-w-lg border-neutral-200 bg-white p-8 text-center dark:border-neutral-800 dark:bg-neutral-900">
                <div className="mx-auto mb-6 flex h-24 w-24 items-center justify-center rounded-full bg-gradient-to-br from-blue-500 to-purple-600 shadow-2xl shadow-blue-500/25">
                  <Mic className="h-12 w-12 text-white" />
                </div>

                <h2 className="text-2xl font-bold text-neutral-900 dark:text-white">
                  Start Voice Session
                </h2>
                <p className="mt-2 text-neutral-500">
                  Select a patient and session type to begin
                </p>

                {/* Patient Selection */}
                <div className="mt-6 space-y-4">
                  <DropdownMenu>
                    <DropdownMenuTrigger asChild>
                      <Button
                        variant="outline"
                        className="w-full justify-between gap-2"
                        disabled={patientsLoading}
                      >
                        <div className="flex items-center gap-2">
                          <User className="h-4 w-4" />
                          {patientsLoading
                            ? 'Loading patients...'
                            : selectedPatient
                              ? `${selectedPatient.name} (${selectedPatient.age} yrs)`
                              : patients.length === 0
                                ? 'No patients - creating...'
                                : 'Select Patient'}
                        </div>
                      </Button>
                    </DropdownMenuTrigger>
                    <DropdownMenuContent className="w-full min-w-[300px]">
                      {patients.length === 0 ? (
                        <DropdownMenuItem disabled>
                          <span className="text-neutral-500">No patients available</span>
                        </DropdownMenuItem>
                      ) : patients.map((patient) => (
                        <DropdownMenuItem
                          key={patient.id}
                          onClick={() => setSelectedPatient(patient)}
                        >
                          <div className="flex items-center gap-3">
                            <div className="flex h-8 w-8 items-center justify-center rounded-full bg-neutral-100 text-sm font-medium dark:bg-neutral-800">
                              {patient.name
                                .split(' ')
                                .map((n) => n[0])
                                .join('')}
                            </div>
                            <div>
                              <p className="font-medium">{patient.name}</p>
                              <p className="text-xs text-neutral-500">
                                {patient.age} years old
                                {patient.lastSession && ` • Last: ${patient.lastSession}`}
                              </p>
                            </div>
                          </div>
                        </DropdownMenuItem>
                      ))}
                    </DropdownMenuContent>
                  </DropdownMenu>

                  {/* Session Type */}
                  <div className="flex gap-2">
                    {(['checkin', 'intake', 'targeted_probe'] as const).map(
                      (type) => (
                        <Button
                          key={type}
                          variant={sessionType === type ? 'default' : 'outline'}
                          className={`flex-1 ${
                            sessionType === type
                              ? 'bg-blue-600 hover:bg-blue-700'
                              : ''
                          }`}
                          onClick={() => setSessionType(type)}
                        >
                          {sessionTypeLabels[type]}
                        </Button>
                      )
                    )}
                  </div>
                </div>

                {/* Continue Button */}
                <Button
                  size="lg"
                  className="mt-8 w-full gap-2 bg-blue-600 py-6 text-lg hover:bg-blue-700"
                  disabled={!selectedPatient}
                  onClick={handleProceedToCheckIn}
                >
                  <ChevronRight className="h-5 w-5" />
                  Continue to Check-in
                </Button>

                {!selectedPatient && (
                  <p className="mt-4 flex items-center justify-center gap-2 text-sm text-orange-600">
                    <AlertCircle className="h-4 w-4" />
                    Please select a patient first
                  </p>
                )}
              </Card>
            </motion.div>
          )}

          {/* Pre-Session Check-in Phase */}
          {phase === 'checkin' && (
            <motion.div
              key="checkin"
              initial={{ opacity: 0, x: 20 }}
              animate={{ opacity: 1, x: 0 }}
              exit={{ opacity: 0, x: -20 }}
              className="flex flex-1 flex-col items-center justify-center"
            >
              <Card className="w-full max-w-lg border-neutral-200 bg-white p-8 dark:border-neutral-800 dark:bg-neutral-900">
                <div className="mb-6 flex items-center gap-3">
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => setPhase('setup')}
                  >
                    <ArrowLeft className="h-4 w-4" />
                  </Button>
                  <div>
                    <h2 className="text-xl font-bold text-neutral-900 dark:text-white">
                      Pre-Session Check-in
                    </h2>
                    <p className="text-sm text-neutral-500">
                      {selectedPatient?.name} • {sessionTypeLabels[sessionType]}
                    </p>
                  </div>
                </div>

                <div className="space-y-6">
                  {/* Patient Status */}
                  <div>
                    <Label className="text-sm font-medium">
                      How has {selectedPatient?.name.split(' ')[0]} been since last session?
                    </Label>
                    <div className="mt-3 flex justify-between">
                      {statusEmojis.map((status) => (
                        <button
                          key={status.value}
                          onClick={() => setCheckIn(prev => ({ ...prev, patientStatus: status.value as PreSessionCheckIn['patientStatus'] }))}
                          className={`flex flex-col items-center gap-1 rounded-lg p-3 transition-all ${
                            checkIn.patientStatus === status.value
                              ? 'bg-blue-100 ring-2 ring-blue-500 dark:bg-blue-950'
                              : 'hover:bg-neutral-100 dark:hover:bg-neutral-800'
                          }`}
                        >
                          <span className="text-2xl">{status.emoji}</span>
                          <span className="text-xs text-neutral-600 dark:text-neutral-400">
                            {status.label}
                          </span>
                        </button>
                      ))}
                    </div>
                  </div>

                  {/* Notable Events */}
                  <div>
                    <Label htmlFor="notable-events" className="text-sm font-medium">
                      Any notable events since last session?
                    </Label>
                    <Textarea
                      id="notable-events"
                      placeholder="Started new medication, school event, family change, etc."
                      value={checkIn.notableEvents}
                      onChange={(e) => setCheckIn(prev => ({ ...prev, notableEvents: e.target.value }))}
                      className="mt-2"
                      rows={3}
                    />
                  </div>

                  {/* Focus Area */}
                  <div>
                    <Label htmlFor="focus-area" className="text-sm font-medium">
                      Focus area for today
                    </Label>
                    <Select
                      value={checkIn.focusArea}
                      onValueChange={(value) => setCheckIn(prev => ({ ...prev, focusArea: value }))}
                    >
                      <SelectTrigger className="mt-2">
                        <SelectValue placeholder="Select focus area" />
                      </SelectTrigger>
                      <SelectContent>
                        {focusAreas.map((area) => (
                          <SelectItem key={area.value} value={area.value}>
                            {area.label}
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  </div>

                  {/* AI Recommendation (if applicable) */}
                  {selectedPatient?.lastSession && (
                    <div className="rounded-lg bg-blue-50 p-4 dark:bg-blue-950">
                      <div className="flex items-start gap-2">
                        <Brain className="h-5 w-5 text-blue-600 mt-0.5" />
                        <div>
                          <p className="text-sm font-medium text-blue-900 dark:text-blue-100">
                            AI Recommendation
                          </p>
                          <p className="text-sm text-blue-700 dark:text-blue-300">
                            Last session showed elevated B2 (insistence on sameness). Consider exploring
                            transition difficulties in more depth.
                          </p>
                        </div>
                      </div>
                    </div>
                  )}
                </div>

                {/* Start Session Button */}
                <Button
                  size="lg"
                  className="mt-8 w-full gap-2 bg-green-600 py-6 text-lg hover:bg-green-700"
                  onClick={handleStartCall}
                  disabled={isLoading}
                >
                  {isLoading ? (
                    <Loader2 className="h-5 w-5 animate-spin" />
                  ) : (
                    <Phone className="h-5 w-5" />
                  )}
                  Start Voice Session
                </Button>

                {error && (
                  <p className="mt-4 flex items-center justify-center gap-2 text-sm text-red-600">
                    <AlertCircle className="h-4 w-4" />
                    {error}
                  </p>
                )}
              </Card>
            </motion.div>
          )}

          {/* Active Call Phase */}
          {phase === 'active' && (
            <motion.div
              key="active"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              className="flex flex-1 flex-col"
            >
              {/* Active Call Header */}
              <div className="mb-6 flex items-center justify-between">
                <div className="flex items-center gap-4">
                  <div className="flex h-12 w-12 items-center justify-center rounded-full bg-gradient-to-br from-blue-500 to-purple-600 text-lg font-semibold text-white">
                    {selectedPatient?.name
                      .split(' ')
                      .map((n) => n[0])
                      .join('')}
                  </div>
                  <div>
                    <h2 className="text-xl font-semibold text-neutral-900 dark:text-white">
                      {selectedPatient?.name}
                    </h2>
                    <div className="flex items-center gap-2">
                      <Badge
                        variant="secondary"
                        className="bg-green-100 text-green-700 dark:bg-green-950 dark:text-green-300"
                      >
                        {sessionTypeLabels[sessionType]}
                      </Badge>
                      <span className="flex items-center gap-1 text-sm text-neutral-500">
                        <Clock className="h-3 w-3" />
                        {formatDuration(callDuration)}
                      </span>
                    </div>
                  </div>
                </div>

                <div className="flex items-center gap-4">
                  <div className="flex items-center gap-2">
                    <span
                      className={`h-2 w-2 rounded-full ${
                        isSpeaking ? 'animate-pulse bg-green-500' : 'bg-neutral-300'
                      }`}
                    />
                    <span className="text-sm text-neutral-500">
                      {isSpeaking ? 'Speaking...' : 'Listening'}
                    </span>
                  </div>
                </div>
              </div>

              {/* Voice Visualizer */}
              <Card className="mb-6 border-neutral-200 bg-white p-8 dark:border-neutral-800 dark:bg-neutral-900">
                <VoiceVisualizer
                  isActive={isCallActive}
                  isSpeaking={isSpeaking}
                  volumeLevel={volumeLevel}
                />
              </Card>

              {/* Call Controls */}
              <div className="flex items-center justify-center gap-4">
                <motion.button
                  whileHover={{ scale: 1.05 }}
                  whileTap={{ scale: 0.95 }}
                  onClick={handleToggleMute}
                  className={`flex h-14 w-14 items-center justify-center rounded-full transition-colors ${
                    isMuted
                      ? 'bg-red-100 text-red-600 dark:bg-red-950 dark:text-red-400'
                      : 'bg-neutral-100 text-neutral-600 hover:bg-neutral-200 dark:bg-neutral-800 dark:text-neutral-400 dark:hover:bg-neutral-700'
                  }`}
                >
                  {isMuted ? (
                    <MicOff className="h-6 w-6" />
                  ) : (
                    <Mic className="h-6 w-6" />
                  )}
                </motion.button>

                <motion.button
                  whileHover={{ scale: 1.05 }}
                  whileTap={{ scale: 0.95 }}
                  onClick={handleEndCall}
                  className="flex h-16 w-16 items-center justify-center rounded-full bg-red-600 text-white shadow-lg shadow-red-500/25 transition-colors hover:bg-red-700"
                >
                  <PhoneOff className="h-7 w-7" />
                </motion.button>

                <motion.button
                  whileHover={{ scale: 1.05 }}
                  whileTap={{ scale: 0.95 }}
                  className="flex h-14 w-14 items-center justify-center rounded-full bg-neutral-100 text-neutral-600 transition-colors hover:bg-neutral-200 dark:bg-neutral-800 dark:text-neutral-400 dark:hover:bg-neutral-700"
                >
                  <Settings className="h-6 w-6" />
                </motion.button>
              </div>
            </motion.div>
          )}

          {/* Processing Phase */}
          {phase === 'processing' && (
            <motion.div
              key="processing"
              initial={{ opacity: 0, scale: 0.95 }}
              animate={{ opacity: 1, scale: 1 }}
              exit={{ opacity: 0, scale: 0.95 }}
              className="flex flex-1 flex-col items-center justify-center"
            >
              <Card className="w-full max-w-lg border-neutral-200 bg-white p-8 text-center dark:border-neutral-800 dark:bg-neutral-900">
                <div className="mx-auto mb-6 flex h-24 w-24 items-center justify-center rounded-full bg-gradient-to-br from-blue-500 to-purple-600 shadow-2xl shadow-blue-500/25">
                  <Loader2 className="h-12 w-12 animate-spin text-white" />
                </div>

                <h2 className="text-2xl font-bold text-neutral-900 dark:text-white">
                  Session Complete
                </h2>
                <p className="mt-2 text-neutral-500">
                  Analyzing conversation...
                </p>

                <div className="mt-6 space-y-3">
                  <Progress value={processingProgress} className="h-2" />
                  <div className="flex justify-between text-sm text-neutral-500">
                    <span>{processingProgress}%</span>
                    <span>
                      {processingProgress < 30 && 'Processing transcript...'}
                      {processingProgress >= 30 && processingProgress < 60 && 'Extracting signals...'}
                      {processingProgress >= 60 && processingProgress < 90 && 'Scoring domains...'}
                      {processingProgress >= 90 && 'Generating summary...'}
                    </span>
                  </div>
                </div>

                <div className="mt-6 space-y-2 text-left">
                  <div className="flex items-center gap-2 text-sm">
                    {processingProgress >= 30 ? (
                      <CheckCircle2 className="h-4 w-4 text-green-500" />
                    ) : (
                      <Loader2 className="h-4 w-4 animate-spin text-neutral-400" />
                    )}
                    <span className={processingProgress >= 30 ? 'text-green-700' : 'text-neutral-500'}>
                      Transcript processed
                    </span>
                  </div>
                  <div className="flex items-center gap-2 text-sm">
                    {processingProgress >= 60 ? (
                      <CheckCircle2 className="h-4 w-4 text-green-500" />
                    ) : processingProgress >= 30 ? (
                      <Loader2 className="h-4 w-4 animate-spin text-neutral-400" />
                    ) : (
                      <div className="h-4 w-4 rounded-full border-2 border-neutral-300" />
                    )}
                    <span className={processingProgress >= 60 ? 'text-green-700' : 'text-neutral-500'}>
                      Signals extracted
                    </span>
                  </div>
                  <div className="flex items-center gap-2 text-sm">
                    {processingProgress >= 90 ? (
                      <CheckCircle2 className="h-4 w-4 text-green-500" />
                    ) : processingProgress >= 60 ? (
                      <Loader2 className="h-4 w-4 animate-spin text-neutral-400" />
                    ) : (
                      <div className="h-4 w-4 rounded-full border-2 border-neutral-300" />
                    )}
                    <span className={processingProgress >= 90 ? 'text-green-700' : 'text-neutral-500'}>
                      Domains scored
                    </span>
                  </div>
                  <div className="flex items-center gap-2 text-sm">
                    {processingProgress >= 100 ? (
                      <CheckCircle2 className="h-4 w-4 text-green-500" />
                    ) : processingProgress >= 90 ? (
                      <Loader2 className="h-4 w-4 animate-spin text-neutral-400" />
                    ) : (
                      <div className="h-4 w-4 rounded-full border-2 border-neutral-300" />
                    )}
                    <span className={processingProgress >= 100 ? 'text-green-700' : 'text-neutral-500'}>
                      Summary generated
                    </span>
                  </div>
                </div>
              </Card>
            </motion.div>
          )}

          {/* Review Phase - Premium Post-Session Analytics with Tabs */}
          {phase === 'review' && analysisResult && (
            <motion.div
              key="review"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              className="flex flex-1 flex-col overflow-hidden"
            >
              {/* Premium Header */}
              <div className="flex-shrink-0 bg-gradient-to-r from-slate-900 via-slate-800 to-slate-900 text-white px-6 py-4 rounded-t-2xl">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-4">
                    <button
                      onClick={() => setPhase('setup')}
                      className="p-2 rounded-lg hover:bg-white/10 transition-colors"
                    >
                      <ArrowLeft className="h-5 w-5" />
                    </button>
                    <div>
                      <div className="flex items-center gap-2">
                        <Sparkles className="h-4 w-4 text-amber-400" />
                        <span className="text-xs font-medium text-amber-400 uppercase tracking-wider">
                          Session Complete
                        </span>
                      </div>
                      <h1 className="text-xl font-semibold">
                        {selectedPatient?.name || 'Session'} Analysis
                      </h1>
                    </div>
                  </div>

                  <div className="flex items-center gap-3">
                    <div className="text-right mr-4">
                      <p className="text-sm text-slate-400">{sessionTypeLabels[sessionType]}</p>
                      <p className="text-lg font-semibold">{analysisResult.signals.length} signals</p>
                    </div>
                    <Button
                      onClick={handleSaveAndComplete}
                      className="gap-2 bg-gradient-to-r from-emerald-500 to-teal-500 hover:from-emerald-600 hover:to-teal-600 text-white border-0"
                      disabled={isLoading}
                    >
                      {isLoading ? (
                        <Loader2 className="h-4 w-4 animate-spin" />
                      ) : (
                        <CheckCircle2 className="h-4 w-4" />
                      )}
                      Complete Session
                    </Button>
                  </div>
                </div>

                {/* Tab Navigation */}
                <div className="flex items-center gap-1 mt-4 -mb-4 px-2">
                  {[
                    { id: 'analytics' as ReviewTab, label: 'Analytics', icon: BarChart3 },
                    { id: 'transcript' as ReviewTab, label: 'Transcript', icon: FileText },
                    { id: 'summary' as ReviewTab, label: 'Summary', icon: Brain },
                    { id: 'actions' as ReviewTab, label: 'Actions', icon: ListChecks },
                  ].map((tab) => (
                    <button
                      key={tab.id}
                      onClick={() => setReviewTab(tab.id)}
                      className={`
                        flex items-center gap-2 px-4 py-3 rounded-t-xl text-sm font-medium transition-all
                        ${reviewTab === tab.id
                          ? 'bg-white text-slate-900'
                          : 'text-slate-400 hover:text-white hover:bg-white/10'
                        }
                      `}
                    >
                      <tab.icon className="h-4 w-4" />
                      {tab.label}
                    </button>
                  ))}
                </div>
              </div>

              {/* Tab Content */}
              <div className="flex-1 overflow-auto bg-white dark:bg-neutral-900 rounded-b-2xl border border-t-0 border-neutral-200 dark:border-neutral-800">
                <AnimatePresence mode="wait">
                  {/* Analytics Tab */}
                  {reviewTab === 'analytics' && (
                    <motion.div
                      key="analytics-tab"
                      initial={{ opacity: 0, y: 10 }}
                      animate={{ opacity: 1, y: 0 }}
                      exit={{ opacity: 0, y: -10 }}
                      className="p-6"
                    >
                      <ClinicalAnalyticsDashboard
                        data={{
                          signals: analysisResult.signals.map((s, idx) => ({
                            id: s.id || `signal-${idx}`,
                            signal_name: s.signal_name,
                            signal_type: s.signal_type,
                            evidence: s.evidence,
                            reasoning: s.reasoning,
                            dsm5_criteria: (s as { dsm5_criteria?: string }).dsm5_criteria,
                            maps_to_domain: s.maps_to_domain,
                            clinical_significance: s.clinical_significance as 'low' | 'moderate' | 'high',
                            confidence: s.confidence,
                            verbatim_quote: (s as { verbatim_quote?: string }).verbatim_quote,
                          })),
                          domainScores: analysisResult.domain_scores.map((d, idx) => ({
                            domain_code: `${d.domain_code}-${idx}`,
                            domain_name: d.domain_name || domainNames[d.domain_code] || d.domain_code,
                            score: d.normalized_score,
                            confidence: d.confidence,
                            evidence_count: d.evidence_count,
                          })),
                          hypotheses: analysisResult.hypotheses.map((h, idx) => ({
                            condition_code: `${h.condition_code}-${idx}`,
                            condition_name: h.condition_name,
                            evidence_strength: h.evidence_strength,
                            uncertainty: h.uncertainty,
                            supporting_count: analysisResult.signals.length,
                            explanation: h.explanation,
                          })),
                          dsm5Coverage: analysisResult.signals.reduce((acc, s) => {
                            const criterion = (s as { dsm5_criteria?: string }).dsm5_criteria || s.maps_to_domain;
                            if (criterion) {
                              acc[criterion] = (acc[criterion] || 0) + 1;
                            }
                            return acc;
                          }, {} as Record<string, number>),
                          dsm5Gaps: ['A1', 'A2', 'A3', 'B1', 'B2', 'B3', 'B4'].filter(c => {
                            return !analysisResult.signals.some(s => {
                              const criterion = (s as { dsm5_criteria?: string }).dsm5_criteria || s.maps_to_domain;
                              return criterion === c;
                            });
                          }),
                          summary: analysisResult.summary?.brief_summary || undefined,
                        }}
                        patientName={selectedPatient?.name || 'Patient'}
                        sessionType={sessionTypeLabels[sessionType]}
                        onSignalClick={(signal) => {
                          const originalSignal = analysisResult.signals.find(s => signal.id.startsWith(s.id));
                          setSelectedSignal(originalSignal || null);
                          setIsSignalModalOpen(true);
                        }}
                      />
                    </motion.div>
                  )}

                  {/* Transcript Tab */}
                  {reviewTab === 'transcript' && (
                    <motion.div
                      key="transcript-tab"
                      initial={{ opacity: 0, y: 10 }}
                      animate={{ opacity: 1, y: 0 }}
                      exit={{ opacity: 0, y: -10 }}
                      className="h-full flex flex-col"
                    >
                      <div className="p-4 border-b border-neutral-200 dark:border-neutral-700 bg-neutral-50 dark:bg-neutral-800/50">
                        <div className="flex items-center justify-between">
                          <div>
                            <h3 className="font-semibold text-neutral-900 dark:text-white">
                              Session Transcript
                            </h3>
                            <p className="text-sm text-neutral-500">
                              {messages.length} messages · {formatDuration(callDuration)} duration
                            </p>
                          </div>
                          <Badge variant="secondary" className="bg-emerald-100 text-emerald-700">
                            <CheckCircle2 className="h-3 w-3 mr-1" />
                            Processed
                          </Badge>
                        </div>
                      </div>
                      <div className="flex-1 overflow-auto">
                        {messages.length > 0 ? (
                          <TranscriptPanel messages={messages} />
                        ) : (
                          <div className="flex flex-col items-center justify-center h-full p-8 text-center">
                            <div className="w-16 h-16 rounded-full bg-neutral-100 dark:bg-neutral-800 flex items-center justify-center mb-4">
                              <FileText className="h-8 w-8 text-neutral-400" />
                            </div>
                            <p className="text-neutral-500">No transcript available</p>
                            <p className="text-sm text-neutral-400 mt-1">
                              The session transcript will appear here after a voice session
                            </p>
                          </div>
                        )}
                      </div>
                    </motion.div>
                  )}

                  {/* Summary Tab */}
                  {reviewTab === 'summary' && (
                    <motion.div
                      key="summary-tab"
                      initial={{ opacity: 0, y: 10 }}
                      animate={{ opacity: 1, y: 0 }}
                      exit={{ opacity: 0, y: -10 }}
                      className="p-6 space-y-6"
                    >
                      {/* Brief Summary */}
                      <div className="bg-gradient-to-br from-sky-50 to-indigo-50 dark:from-sky-950/30 dark:to-indigo-950/30 rounded-2xl p-6 border border-sky-100 dark:border-sky-900">
                        <div className="flex items-center gap-2 mb-3">
                          <Sparkles className="h-5 w-5 text-sky-600" />
                          <h3 className="font-semibold text-sky-900 dark:text-sky-100">Session Summary</h3>
                        </div>
                        <p className="text-neutral-700 dark:text-neutral-300 leading-relaxed">
                          {analysisResult.summary?.brief_summary || 'No summary available for this session.'}
                        </p>
                      </div>

                      {/* Detailed Summary */}
                      {analysisResult.summary?.detailed_summary && (
                        <div className="bg-white dark:bg-neutral-800 rounded-2xl p-6 border border-neutral-200 dark:border-neutral-700">
                          <div className="flex items-center gap-2 mb-3">
                            <Brain className="h-5 w-5 text-purple-500" />
                            <h3 className="font-semibold text-neutral-900 dark:text-white">Detailed Analysis</h3>
                          </div>
                          <p className="text-neutral-600 dark:text-neutral-400 leading-relaxed">
                            {analysisResult.summary.detailed_summary}
                          </p>
                        </div>
                      )}

                      {/* Key Topics */}
                      {analysisResult.summary?.key_topics?.topics && analysisResult.summary.key_topics.topics.length > 0 && (
                        <div className="bg-white dark:bg-neutral-800 rounded-2xl p-6 border border-neutral-200 dark:border-neutral-700">
                          <div className="flex items-center gap-2 mb-4">
                            <Target className="h-5 w-5 text-amber-500" />
                            <h3 className="font-semibold text-neutral-900 dark:text-white">Key Topics Discussed</h3>
                          </div>
                          <div className="flex flex-wrap gap-2">
                            {analysisResult.summary.key_topics.topics.map((topic, i) => (
                              <span
                                key={i}
                                className="px-3 py-1.5 bg-amber-100 dark:bg-amber-900/30 text-amber-800 dark:text-amber-200 rounded-full text-sm font-medium"
                              >
                                {topic}
                              </span>
                            ))}
                          </div>
                        </div>
                      )}

                      {/* Clinical Observations */}
                      {analysisResult.summary?.clinical_observations && (
                        <div className="bg-white dark:bg-neutral-800 rounded-2xl p-6 border border-neutral-200 dark:border-neutral-700">
                          <div className="flex items-center gap-2 mb-3">
                            <Info className="h-5 w-5 text-blue-500" />
                            <h3 className="font-semibold text-neutral-900 dark:text-white">Clinical Observations</h3>
                          </div>
                          <p className="text-neutral-600 dark:text-neutral-400 leading-relaxed">
                            {analysisResult.summary.clinical_observations}
                          </p>
                        </div>
                      )}

                      {/* Emotional Tone */}
                      {analysisResult.summary?.emotional_tone && (
                        <div className="bg-white dark:bg-neutral-800 rounded-2xl p-6 border border-neutral-200 dark:border-neutral-700">
                          <div className="flex items-center gap-2 mb-3">
                            <MessageSquare className="h-5 w-5 text-pink-500" />
                            <h3 className="font-semibold text-neutral-900 dark:text-white">Emotional Tone</h3>
                          </div>
                          <p className="text-neutral-600 dark:text-neutral-400">
                            {analysisResult.summary.emotional_tone}
                          </p>
                        </div>
                      )}
                    </motion.div>
                  )}

                  {/* Actions Tab */}
                  {reviewTab === 'actions' && (
                    <motion.div
                      key="actions-tab"
                      initial={{ opacity: 0, y: 10 }}
                      animate={{ opacity: 1, y: 0 }}
                      exit={{ opacity: 0, y: -10 }}
                      className="p-6 space-y-6"
                    >
                      {/* Follow-up Suggestions */}
                      {analysisResult.summary?.follow_up_suggestions?.suggestions && analysisResult.summary.follow_up_suggestions.suggestions.length > 0 && (
                        <div className="bg-gradient-to-br from-emerald-50 to-teal-50 dark:from-emerald-950/30 dark:to-teal-950/30 rounded-2xl p-6 border border-emerald-100 dark:border-emerald-900">
                          <div className="flex items-center gap-2 mb-4">
                            <Lightbulb className="h-5 w-5 text-emerald-600" />
                            <h3 className="font-semibold text-emerald-900 dark:text-emerald-100">Follow-up Suggestions</h3>
                          </div>
                          <ul className="space-y-3">
                            {analysisResult.summary.follow_up_suggestions.suggestions.map((suggestion, i) => (
                              <li
                                key={i}
                                className="flex items-start gap-3 text-neutral-700 dark:text-neutral-300"
                              >
                                <div className="w-6 h-6 rounded-full bg-emerald-200 dark:bg-emerald-800 flex items-center justify-center flex-shrink-0 mt-0.5">
                                  <span className="text-xs font-semibold text-emerald-700 dark:text-emerald-200">{i + 1}</span>
                                </div>
                                <span>{suggestion}</span>
                              </li>
                            ))}
                          </ul>
                        </div>
                      )}

                      {/* Concerns */}
                      {analysisResult.summary?.concerns && analysisResult.summary.concerns.length > 0 && (
                        <div className="bg-gradient-to-br from-rose-50 to-orange-50 dark:from-rose-950/30 dark:to-orange-950/30 rounded-2xl p-6 border border-rose-100 dark:border-rose-900">
                          <div className="flex items-center gap-2 mb-4">
                            <AlertCircle className="h-5 w-5 text-rose-600" />
                            <h3 className="font-semibold text-rose-900 dark:text-rose-100">Areas of Concern</h3>
                          </div>
                          <ul className="space-y-2">
                            {analysisResult.summary.concerns.map((concern, i) => (
                              <li
                                key={i}
                                className="flex items-start gap-2 text-neutral-700 dark:text-neutral-300"
                              >
                                <span className="text-rose-500 mt-1">•</span>
                                <span>{concern}</span>
                              </li>
                            ))}
                          </ul>
                        </div>
                      )}

                      {/* Clinician Notes */}
                      <div className="bg-white dark:bg-neutral-800 rounded-2xl p-6 border border-neutral-200 dark:border-neutral-700">
                        <div className="flex items-center gap-2 mb-4">
                          <MessageSquare className="h-5 w-5 text-purple-500" />
                          <h3 className="font-semibold text-neutral-900 dark:text-white">Your Clinical Notes</h3>
                        </div>
                        <Textarea
                          placeholder="Add your clinical observations, impressions, and notes for this session..."
                          value={clinicianNotes}
                          onChange={(e) => setClinicianNotes(e.target.value)}
                          className="min-h-[150px] rounded-xl border-neutral-200 dark:border-neutral-700 resize-none text-base"
                        />
                        <p className="text-xs text-neutral-500 mt-2">
                          These notes will be saved with the session record
                        </p>
                      </div>

                      {/* Quick Actions */}
                      <div className="grid grid-cols-2 gap-4">
                        <button className="p-4 rounded-xl border-2 border-dashed border-neutral-200 dark:border-neutral-700 hover:border-sky-300 dark:hover:border-sky-700 hover:bg-sky-50 dark:hover:bg-sky-950/30 transition-all text-left group">
                          <Calendar className="h-6 w-6 text-neutral-400 group-hover:text-sky-500 mb-2" />
                          <h4 className="font-medium text-neutral-900 dark:text-white">Schedule Follow-up</h4>
                          <p className="text-sm text-neutral-500">Book the next session</p>
                        </button>
                        <button className="p-4 rounded-xl border-2 border-dashed border-neutral-200 dark:border-neutral-700 hover:border-purple-300 dark:hover:border-purple-700 hover:bg-purple-50 dark:hover:bg-purple-950/30 transition-all text-left group">
                          <FileText className="h-6 w-6 text-neutral-400 group-hover:text-purple-500 mb-2" />
                          <h4 className="font-medium text-neutral-900 dark:text-white">Export Report</h4>
                          <p className="text-sm text-neutral-500">Download session PDF</p>
                        </button>
                      </div>
                    </motion.div>
                  )}
                </AnimatePresence>
              </div>
            </motion.div>
          )}

          {/* Signal Detail Modal */}
          <SignalDetailModal
            signal={selectedSignal ? {
              id: selectedSignal.id,
              signal_name: selectedSignal.signal_name,
              signal_type: selectedSignal.signal_type,
              evidence: selectedSignal.evidence,
              reasoning: selectedSignal.reasoning,
              dsm5_criteria: (selectedSignal as { dsm5_criteria?: string }).dsm5_criteria,
              maps_to_domain: selectedSignal.maps_to_domain,
              clinical_significance: selectedSignal.clinical_significance as 'low' | 'moderate' | 'high',
              confidence: selectedSignal.confidence,
              verbatim_quote: (selectedSignal as { verbatim_quote?: string }).verbatim_quote,
            } : null}
            isOpen={isSignalModalOpen}
            onClose={() => setIsSignalModalOpen(false)}
            onVerify={(signalId) => {
              handleVerifySignal(signalId, true);
              setIsSignalModalOpen(false);
            }}
          />
        </AnimatePresence>
      </div>

      {/* Transcript Panel - shown only during active call phase */}
      {phase === 'active' && (
        <motion.div
          initial={{ opacity: 0, x: 20 }}
          animate={{ opacity: 1, x: 0 }}
          className="w-96"
        >
          <Card className="flex h-full flex-col border-neutral-200 bg-white dark:border-neutral-800 dark:bg-neutral-900">
            <div className="border-b border-neutral-200 p-4 dark:border-neutral-800">
              <h3 className="font-semibold text-neutral-900 dark:text-white">
                Live Transcript
              </h3>
              <p className="text-sm text-neutral-500">
                Real-time conversation transcript
              </p>
            </div>

            <div className="flex-1 overflow-hidden">
              {messages.length > 0 ? (
                <TranscriptPanel messages={messages} />
              ) : (
                <div className="flex h-full flex-col items-center justify-center p-8 text-center">
                  <div className="flex h-16 w-16 items-center justify-center rounded-full bg-neutral-100 dark:bg-neutral-800">
                    <Mic className="h-8 w-8 text-neutral-400" />
                  </div>
                  <p className="mt-4 text-neutral-500">
                    Waiting for speech...
                  </p>
                </div>
              )}
            </div>
          </Card>
        </motion.div>
      )}
    </div>
  );
}
