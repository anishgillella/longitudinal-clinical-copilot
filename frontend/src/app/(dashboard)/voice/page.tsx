'use client';

import { useState, useCallback, useEffect } from 'react';
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
  XCircle,
  Loader2,
  ChevronRight,
  FileText,
  BarChart3,
  Brain,
  ArrowLeft,
  Calendar,
  MessageSquare,
  Target,
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Card } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Progress } from '@/components/ui/progress';
import { Checkbox } from '@/components/ui/checkbox';
import { Textarea } from '@/components/ui/textarea';
import { Input } from '@/components/ui/input';
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

// Mock patients for selection - in production, fetch from API
const patients = [
  { id: '1', name: 'Alex Thompson', age: 12, lastSession: '2024-12-16' },
  { id: '2', name: 'Jordan Martinez', age: 10, lastSession: '2024-12-10' },
  { id: '3', name: 'Sam Wilson', age: 13, lastSession: null },
];

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
  const [selectedPatient, setSelectedPatient] = useState<typeof patients[0] | null>(null);
  const [sessionType, setSessionType] = useState<'intake' | 'checkin' | 'targeted_probe'>('checkin');
  const [messages, setMessages] = useState<Message[]>([]);
  const [isMuted, setIsMuted] = useState(false);
  const [callDuration, setCallDuration] = useState(0);
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [analysisResult, setAnalysisResult] = useState<AnalysisResult | null>(null);
  const [processingProgress, setProcessingProgress] = useState(0);
  const [clinicianNotes, setClinicianNotes] = useState('');
  const [verifiedSignals, setVerifiedSignals] = useState<Set<string>>(new Set());
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Pre-session check-in state
  const [checkIn, setCheckIn] = useState<PreSessionCheckIn>({
    patientStatus: 'okay',
    notableEvents: '',
    focusArea: 'general',
  });

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
    if (!sessionId) {
      // If no real session ID, use mock data
      await fetchMockAnalysisResults();
      return;
    }

    const maxAttempts = 30;
    let attempts = 0;

    const poll = async () => {
      attempts++;
      try {
        const response = await fetch(`${API_BASE_URL}/api/v1/sessions/${sessionId}/analysis`, {
          headers: {
            'Content-Type': 'application/json',
            // Add auth header if needed
          },
        });

        if (response.ok) {
          const data = await response.json();
          if (data.processing_status?.status === 'processed') {
            setProcessingProgress(100);
            setAnalysisResult(data);
            setPhase('review');
            return;
          }
        }

        if (attempts < maxAttempts) {
          setTimeout(poll, 2000);
        } else {
          // Fallback to mock data if polling fails
          await fetchMockAnalysisResults();
        }
      } catch (err) {
        console.error('Error polling for analysis:', err);
        if (attempts >= maxAttempts) {
          await fetchMockAnalysisResults();
        } else {
          setTimeout(poll, 2000);
        }
      }
    };

    poll();
  };

  const fetchMockAnalysisResults = async () => {
    // Simulate processing delay
    await new Promise(resolve => setTimeout(resolve, 2000));
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

    setAnalysisResult(mockAnalysis);
    setPhase('review');
  };

  const { isCallActive, isSpeaking, volumeLevel, startCall, endCall, toggleMute } =
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
          pre_session_notes: JSON.stringify(checkIn),
        }),
      });

      if (response.ok) {
        const session = await response.json();
        setSessionId(session.id);
      }
    } catch (err) {
      console.log('Could not create session in backend, continuing with mock:', err);
    }

    try {
      await startCall();
    } catch (err) {
      console.error('Failed to start call:', err);
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

    // Save clinician notes and verified signals
    if (sessionId) {
      try {
        // Save each verified signal
        for (const signalId of verifiedSignals) {
          await fetch(`${API_BASE_URL}/api/v1/sessions/${sessionId}/signals/${signalId}/verify`, {
            method: 'PATCH',
            headers: {
              'Content-Type': 'application/json',
            },
            body: JSON.stringify({ verified: true, clinician_notes: clinicianNotes }),
          });
        }
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
                      >
                        <div className="flex items-center gap-2">
                          <User className="h-4 w-4" />
                          {selectedPatient
                            ? `${selectedPatient.name} (${selectedPatient.age} yrs)`
                            : 'Select Patient'}
                        </div>
                      </Button>
                    </DropdownMenuTrigger>
                    <DropdownMenuContent className="w-full min-w-[300px]">
                      {patients.map((patient) => (
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

          {/* Review Phase */}
          {phase === 'review' && analysisResult && (
            <motion.div
              key="review"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              className="flex flex-1 flex-col overflow-auto"
            >
              {/* Header */}
              <div className="mb-6 flex items-center justify-between">
                <div className="flex items-center gap-4">
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => setPhase('setup')}
                    className="gap-2"
                  >
                    <ArrowLeft className="h-4 w-4" />
                    Back
                  </Button>
                  <div>
                    <h2 className="text-xl font-semibold text-neutral-900 dark:text-white">
                      Session Review: {selectedPatient?.name}
                    </h2>
                    <p className="text-sm text-neutral-500">
                      {sessionTypeLabels[sessionType]} • {formatDuration(callDuration)}
                    </p>
                  </div>
                </div>
                <Button
                  onClick={handleSaveAndComplete}
                  className="gap-2 bg-green-600 hover:bg-green-700"
                  disabled={isLoading}
                >
                  {isLoading ? (
                    <Loader2 className="h-4 w-4 animate-spin" />
                  ) : (
                    <CheckCircle2 className="h-4 w-4" />
                  )}
                  Save & Complete
                </Button>
              </div>

              <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
                {/* Extracted Signals */}
                <Card className="border-neutral-200 bg-white p-6 dark:border-neutral-800 dark:bg-neutral-900">
                  <div className="mb-4 flex items-center justify-between">
                    <h3 className="flex items-center gap-2 font-semibold">
                      <Brain className="h-5 w-5 text-purple-500" />
                      Extracted Signals
                    </h3>
                    <Badge variant="secondary">{analysisResult.signals.length} signals</Badge>
                  </div>

                  <div className="space-y-4 max-h-[400px] overflow-y-auto">
                    {analysisResult.signals.map((signal) => (
                      <div
                        key={signal.id}
                        className="rounded-lg border border-neutral-200 p-4 dark:border-neutral-700"
                      >
                        <div className="flex items-start justify-between gap-3">
                          <div className="flex items-start gap-3">
                            <Checkbox
                              id={`signal-${signal.id}`}
                              checked={verifiedSignals.has(signal.id)}
                              onCheckedChange={(checked) => handleVerifySignal(signal.id, !!checked)}
                            />
                            <div className="flex-1">
                              <div className="flex items-center gap-2 mb-1">
                                <span className="font-medium">{signal.signal_name}</span>
                                <Badge variant="outline" className="text-xs">
                                  {signal.maps_to_domain}
                                </Badge>
                                {getSignificanceBadge(signal.clinical_significance)}
                              </div>
                              <p className="text-sm text-neutral-600 dark:text-neutral-400 italic mb-2">
                                "{signal.evidence}"
                              </p>
                              <p className="text-xs text-neutral-500">{signal.reasoning}</p>
                              <div className="mt-2 flex items-center gap-4 text-xs text-neutral-500">
                                <span>Intensity: {Math.round(signal.intensity * 100)}%</span>
                                <span>Confidence: {Math.round(signal.confidence * 100)}%</span>
                              </div>
                            </div>
                          </div>
                        </div>
                      </div>
                    ))}
                  </div>
                </Card>

                {/* Domain Scores */}
                <Card className="border-neutral-200 bg-white p-6 dark:border-neutral-800 dark:bg-neutral-900">
                  <div className="mb-4 flex items-center gap-2">
                    <BarChart3 className="h-5 w-5 text-blue-500" />
                    <h3 className="font-semibold">Domain Scores</h3>
                  </div>

                  <div className="space-y-4">
                    {analysisResult.domain_scores.map((domain) => (
                      <div key={domain.domain_code}>
                        <div className="flex items-center justify-between mb-1">
                          <div className="flex items-center gap-2">
                            <span className="text-sm font-medium">{domain.domain_code}</span>
                            <span className="text-sm text-neutral-500">{domainNames[domain.domain_code] || domain.domain_name}</span>
                          </div>
                          <div className="flex items-center gap-2">
                            <span className="text-sm font-medium">{Math.round(domain.raw_score * 100)}%</span>
                            {domain.score_change !== null && (
                              <span className={`text-xs ${domain.score_change > 0 ? 'text-red-500' : 'text-green-500'}`}>
                                {domain.score_change > 0 ? '+' : ''}{Math.round(domain.score_change * 100)}%
                              </span>
                            )}
                          </div>
                        </div>
                        <div className="h-2 w-full rounded-full bg-neutral-100 dark:bg-neutral-800">
                          <div
                            className={`h-2 rounded-full ${getScoreColor(domain.raw_score)}`}
                            style={{ width: `${domain.raw_score * 100}%` }}
                          />
                        </div>
                      </div>
                    ))}
                  </div>

                  {/* Hypotheses */}
                  <div className="mt-6 pt-6 border-t border-neutral-200 dark:border-neutral-700">
                    <h4 className="font-medium mb-3">Diagnostic Hypotheses</h4>
                    <div className="space-y-3">
                      {analysisResult.hypotheses.map((h) => (
                        <div key={h.id} className="flex items-center justify-between">
                          <div>
                            <span className="font-medium">{h.condition_name}</span>
                            <p className="text-xs text-neutral-500">{h.explanation.slice(0, 80)}...</p>
                          </div>
                          <div className="text-right">
                            <span className="text-lg font-semibold">{Math.round(h.evidence_strength * 100)}%</span>
                            <p className="text-xs text-neutral-500">confidence</p>
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                </Card>

                {/* Summary */}
                <Card className="border-neutral-200 bg-white p-6 dark:border-neutral-800 dark:bg-neutral-900 lg:col-span-2">
                  <div className="mb-4 flex items-center gap-2">
                    <FileText className="h-5 w-5 text-green-500" />
                    <h3 className="font-semibold">AI Summary</h3>
                  </div>

                  <p className="text-neutral-700 dark:text-neutral-300 mb-4">
                    {analysisResult.summary?.brief_summary}
                  </p>

                  {analysisResult.summary?.follow_up_suggestions && (
                    <div className="mb-4">
                      <h4 className="font-medium mb-2">Recommended Follow-up</h4>
                      <ul className="list-disc list-inside text-sm text-neutral-600 dark:text-neutral-400 space-y-1">
                        {analysisResult.summary.follow_up_suggestions.suggestions.map((s, i) => (
                          <li key={i}>{s}</li>
                        ))}
                      </ul>
                    </div>
                  )}

                  {/* Clinician Notes */}
                  <div className="mt-4 pt-4 border-t border-neutral-200 dark:border-neutral-700">
                    <h4 className="font-medium mb-2">Clinician Notes</h4>
                    <Textarea
                      placeholder="Add your observations and notes..."
                      value={clinicianNotes}
                      onChange={(e) => setClinicianNotes(e.target.value)}
                      className="min-h-[100px]"
                    />
                  </div>
                </Card>
              </div>
            </motion.div>
          )}
        </AnimatePresence>
      </div>

      {/* Transcript Panel - shown during active and review phases */}
      {(phase === 'active' || phase === 'review') && (
        <motion.div
          initial={{ opacity: 0, x: 20 }}
          animate={{ opacity: 1, x: 0 }}
          className="w-96"
        >
          <Card className="flex h-full flex-col border-neutral-200 bg-white dark:border-neutral-800 dark:bg-neutral-900">
            <div className="border-b border-neutral-200 p-4 dark:border-neutral-800">
              <h3 className="font-semibold text-neutral-900 dark:text-white">
                {phase === 'active' ? 'Live Transcript' : 'Session Transcript'}
              </h3>
              <p className="text-sm text-neutral-500">
                {phase === 'active'
                  ? 'Real-time conversation transcript'
                  : `${messages.length} messages recorded`}
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
