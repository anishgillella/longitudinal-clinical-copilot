'use client';

import { useState } from 'react';
import { motion } from 'framer-motion';
import {
  ArrowLeft,
  Phone,
  Mail,
  Calendar,
  Clock,
  Mic,
  FileText,
  Brain,
  Activity,
  ChevronRight,
  TrendingUp,
  TrendingDown,
  Minus,
  Eye,
  AlertCircle,
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Card } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Progress } from '@/components/ui/progress';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { ScrollArea } from '@/components/ui/scroll-area';
import Link from 'next/link';
import { EvidenceModal, type HypothesisDetail } from '@/components/assessment/evidence-modal';

// Mock patient data
const patient = {
  id: '1',
  first_name: 'Alex',
  last_name: 'Thompson',
  date_of_birth: '2012-03-15',
  gender: 'Male',
  email: 'parent@email.com',
  phone: '(555) 123-4567',
  status: 'active',
  primary_concern: 'Social communication difficulties and sensory sensitivities',
  referral_source: 'Pediatrician referral',
  intake_date: '2024-11-15',
};

const assessmentProgress = {
  overall_completeness: 65,
  total_sessions: 5,
  domains_explored: 6,
  domains_total: 10,
  signals_collected: 47,
  last_session: '2 hours ago',
};

// Mock hypotheses with detailed evidence for the modal
const hypotheses: HypothesisDetail[] = [
  {
    id: '1',
    condition_code: 'asd_level_1',
    condition_name: 'ASD Level 1',
    evidence_strength: 0.72,
    uncertainty: 0.15,
    confidence_low: 0.57,
    confidence_high: 0.87,
    supporting_signals: 12,
    contradicting_signals: 3,
    trend: 'increasing',
    explanation: 'Multiple communication and social interaction patterns observed across sessions suggest characteristics consistent with ASD Level 1. The child demonstrates challenges with social reciprocity and shows preference for structured interactions.',
    limitations: 'Eye contact, motor behaviors, and sensory responses cannot be directly assessed from transcript alone. Direct observation is recommended to complete the assessment.',
    supporting_evidence: [
      {
        signal_id: 's1',
        signal_name: 'Echolalia',
        evidence_type: 'observed',
        quote: "How was school today? How was school today?",
        reasoning: 'Patient repeated the exact phrase back, which is a common communication pattern in ASD.',
        session_id: '1',
        transcript_line: 12,
      },
      {
        signal_id: 's2',
        signal_name: 'Literal Interpretation',
        evidence_type: 'observed',
        quote: "Can you tell me more? Yes.",
        reasoning: 'Responded literally to a question intended as a prompt, indicating pragmatic language difficulties.',
        session_id: '1',
        transcript_line: 24,
      },
      {
        signal_id: 's3',
        signal_name: 'Social Difficulty',
        evidence_type: 'self_reported',
        quote: "I don\'t really know what to say to the other kids during group projects.",
        reasoning: 'Self-reported difficulty with peer interactions, a core feature of ASD.',
        session_id: '1',
        transcript_line: 35,
      },
      {
        signal_id: 's4',
        signal_name: 'Sensory Sensitivity',
        evidence_type: 'self_reported',
        quote: "The lights at school hurt my eyes sometimes.",
        reasoning: 'Reported sensory hypersensitivity, common in ASD presentations.',
        session_id: '2',
        transcript_line: 8,
      },
    ],
    contradicting_evidence: [
      {
        signal_name: 'Emotional Awareness',
        evidence_type: 'observed',
        quote: "I felt kind of nervous. Like my stomach hurt a little.",
        reasoning: 'Patient was able to identify and describe emotional states with physical correlates, showing some interoceptive awareness.',
      },
    ],
  },
  {
    id: '2',
    condition_code: 'sensory_processing',
    condition_name: 'Sensory Processing Disorder',
    evidence_strength: 0.45,
    uncertainty: 0.2,
    confidence_low: 0.25,
    confidence_high: 0.65,
    supporting_signals: 8,
    contradicting_signals: 5,
    trend: 'stable',
    explanation: 'Evidence of sensory sensitivities reported by the patient, particularly to light and sound. However, these could be part of ASD presentation rather than standalone SPD.',
    limitations: 'Sensory responses in real-world settings cannot be assessed from transcript. Occupational therapy evaluation recommended.',
    supporting_evidence: [
      {
        signal_id: 's4',
        signal_name: 'Light Sensitivity',
        evidence_type: 'self_reported',
        quote: "The lights at school hurt my eyes sometimes.",
        reasoning: 'Clear report of visual hypersensitivity affecting daily functioning.',
        session_id: '2',
        transcript_line: 8,
      },
      {
        signal_id: 's5',
        signal_name: 'Sound Sensitivity',
        evidence_type: 'self_reported',
        quote: "The cafeteria is too loud. I eat in the library.",
        reasoning: 'Auditory sensitivity with behavioral adaptation (avoidance).',
        session_id: '2',
        transcript_line: 22,
      },
    ],
    contradicting_evidence: [],
  },
  {
    id: '3',
    condition_code: 'adhd',
    condition_name: 'ADHD',
    evidence_strength: 0.28,
    uncertainty: 0.15,
    confidence_low: 0.13,
    confidence_high: 0.43,
    supporting_signals: 4,
    contradicting_signals: 8,
    trend: 'decreasing',
    explanation: 'Limited evidence for ADHD. While some attention-related comments were made, the overall pattern is more consistent with ASD-related executive function challenges than primary ADHD.',
    limitations: 'Attention and hyperactivity cannot be assessed from transcript. Classroom observation and standardized ADHD measures recommended if ADHD remains a consideration.',
    supporting_evidence: [
      {
        signal_id: 's6',
        signal_name: 'Attention Comment',
        evidence_type: 'self_reported',
        quote: "Sometimes I forget what the teacher said.",
        reasoning: 'Could indicate attention difficulties, though also common in ASD.',
        session_id: '3',
        transcript_line: 15,
      },
    ],
    contradicting_evidence: [
      {
        signal_name: 'Sustained Focus on Interests',
        evidence_type: 'inferred',
        quote: "I can talk about trains for hours. I know every type.",
        reasoning: 'Ability to hyperfocus on preferred topics is more consistent with ASD than ADHD.',
      },
      {
        signal_name: 'Structured Responses',
        evidence_type: 'observed',
        quote: "",
        reasoning: 'Conversation patterns showed methodical, non-impulsive responses throughout sessions.',
      },
    ],
  },
];

const domainScores = [
  { name: 'Social-Emotional Reciprocity', score: 72, category: 'Social Communication' },
  { name: 'Nonverbal Communication', score: 65, category: 'Social Communication' },
  { name: 'Relationships', score: 58, category: 'Social Communication' },
  { name: 'Repetitive Behaviors', score: 45, category: 'Restricted/Repetitive' },
  { name: 'Sensory Reactivity', score: 78, category: 'Restricted/Repetitive' },
  { name: 'Routines & Rituals', score: 52, category: 'Restricted/Repetitive' },
];

const timeline = [
  {
    id: '1',
    type: 'session',
    title: 'Check-in Session Completed',
    description: 'Discussed school challenges and peer interactions',
    date: '2 hours ago',
    significance: 'high',
  },
  {
    id: '2',
    type: 'observation',
    title: 'New Clinical Signal Detected',
    description: 'Eye contact avoidance during emotional discussion',
    date: 'Yesterday',
    significance: 'moderate',
  },
  {
    id: '3',
    type: 'milestone',
    title: 'Hypothesis Confidence Increased',
    description: 'ASD Level 1 confidence increased from 65% to 72%',
    date: '3 days ago',
    significance: 'high',
  },
  {
    id: '4',
    type: 'session',
    title: 'Targeted Probe: Sensory',
    description: 'Explored sensory sensitivities in detail',
    date: '1 week ago',
    significance: 'moderate',
  },
];

const sessions = [
  {
    id: '1',
    type: 'checkin',
    date: 'Dec 22, 2024',
    duration: '32 min',
    status: 'completed',
    summary: 'Discussed recent school challenges...',
  },
  {
    id: '2',
    type: 'targeted_probe',
    date: 'Dec 19, 2024',
    duration: '28 min',
    status: 'completed',
    summary: 'Explored sensory processing concerns...',
  },
  {
    id: '3',
    type: 'checkin',
    date: 'Dec 15, 2024',
    duration: '25 min',
    status: 'completed',
    summary: 'Follow-up on social interactions...',
  },
];

const trendIcons = {
  increasing: TrendingUp,
  stable: Minus,
  decreasing: TrendingDown,
};

const trendColors = {
  increasing: 'text-green-500',
  stable: 'text-neutral-400',
  decreasing: 'text-red-500',
};

function calculateAge(dob: string): number {
  const birthDate = new Date(dob);
  const today = new Date();
  let age = today.getFullYear() - birthDate.getFullYear();
  const monthDiff = today.getMonth() - birthDate.getMonth();
  if (monthDiff < 0 || (monthDiff === 0 && today.getDate() < birthDate.getDate())) {
    age--;
  }
  return age;
}

export default function PatientProfilePage() {
  const [activeTab, setActiveTab] = useState('overview');
  const [selectedHypothesis, setSelectedHypothesis] = useState<HypothesisDetail | null>(null);
  const [isEvidenceModalOpen, setIsEvidenceModalOpen] = useState(false);

  const handleHypothesisClick = (hypothesis: HypothesisDetail) => {
    setSelectedHypothesis(hypothesis);
    setIsEvidenceModalOpen(true);
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <motion.div
        initial={{ opacity: 0, y: -20 }}
        animate={{ opacity: 1, y: 0 }}
      >
        <Button variant="ghost" size="sm" className="mb-4 gap-2" asChild>
          <Link href="/patients">
            <ArrowLeft className="h-4 w-4" />
            Back to Patients
          </Link>
        </Button>

        <div className="flex flex-col gap-6 lg:flex-row lg:items-start lg:justify-between">
          {/* Patient Info */}
          <div className="flex items-start gap-4">
            <div className="flex h-20 w-20 items-center justify-center rounded-2xl bg-gradient-to-br from-blue-500 to-purple-600 text-2xl font-bold text-white shadow-xl shadow-blue-500/25">
              {patient.first_name[0]}
              {patient.last_name[0]}
            </div>
            <div>
              <h1 className="text-3xl font-bold tracking-tight text-neutral-900 dark:text-white">
                {patient.first_name} {patient.last_name}
              </h1>
              <div className="mt-1 flex flex-wrap items-center gap-3 text-neutral-500">
                <span>{calculateAge(patient.date_of_birth)} years old</span>
                <span>•</span>
                <span>{patient.gender}</span>
                <Badge
                  variant="secondary"
                  className="bg-green-100 text-green-700 dark:bg-green-950 dark:text-green-300"
                >
                  Active
                </Badge>
              </div>
              <p className="mt-2 max-w-xl text-sm text-neutral-600 dark:text-neutral-400">
                {patient.primary_concern}
              </p>
            </div>
          </div>

          {/* Actions */}
          <div className="flex gap-2">
            <Button variant="outline" className="gap-2">
              <Phone className="h-4 w-4" />
              Call
            </Button>
            <Button variant="outline" className="gap-2">
              <Mail className="h-4 w-4" />
              Email
            </Button>
            <Button className="gap-2 bg-blue-600 hover:bg-blue-700" asChild>
              <Link href={`/voice?patient=${patient.id}`}>
                <Mic className="h-4 w-4" />
                Start Session
              </Link>
            </Button>
          </div>
        </div>
      </motion.div>

      {/* Quick Stats */}
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ delay: 0.1 }}
        className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4"
      >
        <Card className="border-neutral-200 bg-white p-4 dark:border-neutral-800 dark:bg-neutral-900">
          <div className="flex items-center gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-blue-100 dark:bg-blue-950">
              <Activity className="h-5 w-5 text-blue-600" />
            </div>
            <div>
              <p className="text-sm text-neutral-500">Sessions</p>
              <p className="text-xl font-semibold text-neutral-900 dark:text-white">
                {assessmentProgress.total_sessions}
              </p>
            </div>
          </div>
        </Card>
        <Card className="border-neutral-200 bg-white p-4 dark:border-neutral-800 dark:bg-neutral-900">
          <div className="flex items-center gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-purple-100 dark:bg-purple-950">
              <Brain className="h-5 w-5 text-purple-600" />
            </div>
            <div>
              <p className="text-sm text-neutral-500">Signals Collected</p>
              <p className="text-xl font-semibold text-neutral-900 dark:text-white">
                {assessmentProgress.signals_collected}
              </p>
            </div>
          </div>
        </Card>
        <Card className="border-neutral-200 bg-white p-4 dark:border-neutral-800 dark:bg-neutral-900">
          <div className="flex items-center gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-green-100 dark:bg-green-950">
              <FileText className="h-5 w-5 text-green-600" />
            </div>
            <div>
              <p className="text-sm text-neutral-500">Domains Explored</p>
              <p className="text-xl font-semibold text-neutral-900 dark:text-white">
                {assessmentProgress.domains_explored}/{assessmentProgress.domains_total}
              </p>
            </div>
          </div>
        </Card>
        <Card className="border-neutral-200 bg-white p-4 dark:border-neutral-800 dark:bg-neutral-900">
          <div className="flex items-center gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-orange-100 dark:bg-orange-950">
              <Clock className="h-5 w-5 text-orange-600" />
            </div>
            <div>
              <p className="text-sm text-neutral-500">Last Session</p>
              <p className="text-xl font-semibold text-neutral-900 dark:text-white">
                {assessmentProgress.last_session}
              </p>
            </div>
          </div>
        </Card>
      </motion.div>

      {/* Main Content */}
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ delay: 0.2 }}
      >
        <Tabs value={activeTab} onValueChange={setActiveTab} className="space-y-6">
          <TabsList className="bg-neutral-100 dark:bg-neutral-800">
            <TabsTrigger value="overview">Overview</TabsTrigger>
            <TabsTrigger value="sessions">Sessions</TabsTrigger>
            <TabsTrigger value="assessment">Assessment</TabsTrigger>
            <TabsTrigger value="timeline">Timeline</TabsTrigger>
          </TabsList>

          {/* Overview Tab */}
          <TabsContent value="overview" className="space-y-6">
            <div className="grid gap-6 lg:grid-cols-2">
              {/* Assessment Progress */}
              <Card className="border-neutral-200 bg-white p-6 dark:border-neutral-800 dark:bg-neutral-900">
                <h3 className="text-lg font-semibold text-neutral-900 dark:text-white">
                  Assessment Progress
                </h3>
                <div className="mt-4">
                  <div className="mb-2 flex items-center justify-between">
                    <span className="text-sm text-neutral-500">Overall Completion</span>
                    <span className="text-sm font-medium">{assessmentProgress.overall_completeness}%</span>
                  </div>
                  <Progress value={assessmentProgress.overall_completeness} className="h-3" />
                </div>
                <div className="mt-6 space-y-3">
                  {domainScores.slice(0, 4).map((domain) => (
                    <div key={domain.name} className="flex items-center justify-between">
                      <span className="text-sm text-neutral-600 dark:text-neutral-400">
                        {domain.name}
                      </span>
                      <div className="flex items-center gap-2">
                        <Progress value={domain.score} className="h-1.5 w-20" />
                        <span className="w-8 text-right text-xs font-medium text-neutral-500">
                          {domain.score}%
                        </span>
                      </div>
                    </div>
                  ))}
                </div>
              </Card>

              {/* Hypotheses */}
              <Card className="border-neutral-200 bg-white p-6 dark:border-neutral-800 dark:bg-neutral-900">
                <h3 className="text-lg font-semibold text-neutral-900 dark:text-white">
                  Diagnostic Hypotheses
                </h3>
                <p className="mt-1 text-sm text-neutral-500">
                  Evidence-based working hypotheses
                </p>
                <div className="mt-4 space-y-4">
                  {hypotheses.map((hypothesis) => {
                    const TrendIcon = trendIcons[hypothesis.trend as keyof typeof trendIcons];
                    const confidencePercent = Math.round(hypothesis.evidence_strength * 100);
                    return (
                      <motion.div
                        key={hypothesis.id}
                        whileHover={{ scale: 1.01 }}
                        whileTap={{ scale: 0.99 }}
                        onClick={() => handleHypothesisClick(hypothesis)}
                        className="cursor-pointer rounded-xl border border-neutral-200 p-4 transition-colors hover:border-blue-300 hover:bg-blue-50/50 dark:border-neutral-700 dark:hover:border-blue-700 dark:hover:bg-blue-950/20"
                      >
                        <div className="flex items-start justify-between">
                          <div>
                            <div className="flex items-center gap-2">
                              <span className="font-medium text-neutral-900 dark:text-white">
                                {hypothesis.condition_name}
                              </span>
                              <TrendIcon
                                className={`h-4 w-4 ${trendColors[hypothesis.trend as keyof typeof trendColors]}`}
                              />
                            </div>
                            <div className="mt-1 flex items-center gap-3 text-xs text-neutral-500">
                              <span className="text-green-600">+{hypothesis.supporting_signals} supporting</span>
                              <span className="text-red-500">-{hypothesis.contradicting_signals} contradicting</span>
                            </div>
                          </div>
                          <div className="text-right">
                            <span className="text-2xl font-bold text-neutral-900 dark:text-white">
                              {confidencePercent}%
                            </span>
                            <p className="text-xs text-neutral-500">confidence</p>
                          </div>
                        </div>
                        <Progress value={confidencePercent} className="mt-3 h-1.5" />
                        <div className="mt-2 flex items-center justify-between">
                          <div className="flex items-center gap-1 text-xs text-neutral-400">
                            <Eye className="h-3 w-3" />
                            Click to view evidence
                          </div>
                          {hypothesis.limitations && (
                            <div className="flex items-center gap-1 text-xs text-amber-500">
                              <AlertCircle className="h-3 w-3" />
                              Limitations apply
                            </div>
                          )}
                        </div>
                      </motion.div>
                    );
                  })}
                </div>
              </Card>
            </div>

            {/* Recent Timeline */}
            <Card className="border-neutral-200 bg-white p-6 dark:border-neutral-800 dark:bg-neutral-900">
              <div className="mb-4 flex items-center justify-between">
                <h3 className="text-lg font-semibold text-neutral-900 dark:text-white">
                  Recent Activity
                </h3>
                <Button variant="ghost" size="sm" className="gap-1">
                  View all
                  <ChevronRight className="h-4 w-4" />
                </Button>
              </div>
              <div className="space-y-4">
                {timeline.slice(0, 3).map((event, index) => (
                  <div key={event.id} className="flex gap-4">
                    <div className="relative flex flex-col items-center">
                      <div
                        className={`h-3 w-3 rounded-full ${
                          event.significance === 'high'
                            ? 'bg-blue-500'
                            : 'bg-neutral-300 dark:bg-neutral-600'
                        }`}
                      />
                      {index < timeline.slice(0, 3).length - 1 && (
                        <div className="h-full w-px bg-neutral-200 dark:bg-neutral-700" />
                      )}
                    </div>
                    <div className="flex-1 pb-4">
                      <p className="font-medium text-neutral-900 dark:text-white">
                        {event.title}
                      </p>
                      <p className="text-sm text-neutral-500">{event.description}</p>
                      <p className="mt-1 text-xs text-neutral-400">{event.date}</p>
                    </div>
                  </div>
                ))}
              </div>
            </Card>
          </TabsContent>

          {/* Sessions Tab */}
          <TabsContent value="sessions">
            <Card className="border-neutral-200 bg-white p-6 dark:border-neutral-800 dark:bg-neutral-900">
              <div className="mb-4 flex items-center justify-between">
                <h3 className="text-lg font-semibold text-neutral-900 dark:text-white">
                  Session History
                </h3>
                <Button className="gap-2 bg-blue-600 hover:bg-blue-700">
                  <Mic className="h-4 w-4" />
                  New Session
                </Button>
              </div>
              <div className="space-y-3">
                {sessions.map((session) => (
                  <Link key={session.id} href={`/sessions/${session.id}`}>
                    <div className="flex items-center justify-between rounded-xl border border-neutral-200 p-4 transition-colors hover:bg-neutral-50 dark:border-neutral-700 dark:hover:bg-neutral-800">
                      <div className="flex items-center gap-4">
                        <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-blue-100 dark:bg-blue-950">
                          <Mic className="h-5 w-5 text-blue-600" />
                        </div>
                        <div>
                          <p className="font-medium text-neutral-900 dark:text-white">
                            {session.type === 'checkin' ? 'Check-in' : 'Targeted Probe'}
                          </p>
                          <p className="text-sm text-neutral-500">{session.summary}</p>
                        </div>
                      </div>
                      <div className="text-right">
                        <p className="text-sm font-medium text-neutral-900 dark:text-white">
                          {session.date}
                        </p>
                        <p className="text-xs text-neutral-500">{session.duration}</p>
                      </div>
                    </div>
                  </Link>
                ))}
              </div>
            </Card>
          </TabsContent>

          {/* Assessment Tab */}
          <TabsContent value="assessment">
            <Card className="border-neutral-200 bg-white p-6 dark:border-neutral-800 dark:bg-neutral-900">
              <h3 className="text-lg font-semibold text-neutral-900 dark:text-white">
                Domain Scores
              </h3>
              <p className="mt-1 text-sm text-neutral-500">
                Assessment scores across all evaluated domains
              </p>
              <div className="mt-6 space-y-4">
                {domainScores.map((domain) => (
                  <div key={domain.name} className="space-y-2">
                    <div className="flex items-center justify-between">
                      <div>
                        <p className="font-medium text-neutral-900 dark:text-white">
                          {domain.name}
                        </p>
                        <p className="text-xs text-neutral-500">{domain.category}</p>
                      </div>
                      <span className="text-lg font-semibold text-neutral-900 dark:text-white">
                        {domain.score}%
                      </span>
                    </div>
                    <Progress value={domain.score} className="h-2" />
                  </div>
                ))}
              </div>
            </Card>
          </TabsContent>

          {/* Timeline Tab */}
          <TabsContent value="timeline">
            <Card className="border-neutral-200 bg-white p-6 dark:border-neutral-800 dark:bg-neutral-900">
              <h3 className="text-lg font-semibold text-neutral-900 dark:text-white">
                Full Timeline
              </h3>
              <ScrollArea className="mt-4 h-[500px]">
                <div className="space-y-4 pr-4">
                  {timeline.map((event, index) => (
                    <div key={event.id} className="flex gap-4">
                      <div className="relative flex flex-col items-center">
                        <div
                          className={`h-3 w-3 rounded-full ${
                            event.significance === 'high'
                              ? 'bg-blue-500'
                              : event.significance === 'critical'
                              ? 'bg-red-500'
                              : 'bg-neutral-300 dark:bg-neutral-600'
                          }`}
                        />
                        {index < timeline.length - 1 && (
                          <div className="h-full w-px bg-neutral-200 dark:bg-neutral-700" />
                        )}
                      </div>
                      <div className="flex-1 pb-4">
                        <p className="font-medium text-neutral-900 dark:text-white">
                          {event.title}
                        </p>
                        <p className="text-sm text-neutral-500">{event.description}</p>
                        <p className="mt-1 text-xs text-neutral-400">{event.date}</p>
                      </div>
                    </div>
                  ))}
                </div>
              </ScrollArea>
            </Card>
          </TabsContent>
        </Tabs>
      </motion.div>

      {/* Evidence Modal */}
      <EvidenceModal
        isOpen={isEvidenceModalOpen}
        onClose={() => setIsEvidenceModalOpen(false)}
        hypothesis={selectedHypothesis}
      />
    </div>
  );
}
