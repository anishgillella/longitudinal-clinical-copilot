'use client';

import { motion } from 'framer-motion';
import {
  ArrowLeft,
  Clock,
  Calendar,
  User,
  Mic,
  Brain,
  FileText,
  Play,
  Download,
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Card } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { ScrollArea } from '@/components/ui/scroll-area';
import Link from 'next/link';

// Mock session data
const session = {
  id: '1',
  patient_name: 'Alex Thompson',
  patient_id: '1',
  session_type: 'checkin',
  status: 'completed',
  date: 'December 22, 2024',
  time: '2:30 PM',
  duration: '32 minutes',
  summary: 'Discussed recent school challenges and peer interactions. Alex showed notable improvement in describing emotional states compared to previous sessions. Explored sensory experiences in classroom settings.',
  key_topics: ['School challenges', 'Peer interactions', 'Emotional awareness', 'Sensory experiences'],
  signals_detected: 8,
};

const transcript = [
  { id: '1', role: 'assistant', content: "Hi Alex, it's good to talk with you again. How has your week been?", timestamp: '0:00' },
  { id: '2', role: 'user', content: "It was okay. School was kind of hard this week.", timestamp: '0:12' },
  { id: '3', role: 'assistant', content: "I hear you. Can you tell me more about what made school hard?", timestamp: '0:18' },
  { id: '4', role: 'user', content: "There was a group project and I didn't really know what to say to the other kids.", timestamp: '0:25' },
  { id: '5', role: 'assistant', content: "That sounds challenging. How did that make you feel?", timestamp: '0:35' },
  { id: '6', role: 'user', content: "I felt kind of nervous. Like my stomach hurt a little.", timestamp: '0:42' },
  { id: '7', role: 'assistant', content: "Thank you for sharing that. It's really good that you can identify those feelings in your body.", timestamp: '0:50' },
  { id: '8', role: 'user', content: "Yeah, my mom says I'm getting better at that.", timestamp: '1:02' },
];

const signals = [
  {
    id: '1',
    type: 'emotional',
    name: 'Emotional identification',
    evidence: 'Patient described physical sensation (stomach hurt) associated with nervousness',
    significance: 'high',
  },
  {
    id: '2',
    type: 'social',
    name: 'Social communication difficulty',
    evidence: "Reported not knowing what to say to peers during group project",
    significance: 'moderate',
  },
  {
    id: '3',
    type: 'behavioral',
    name: 'Anxiety response',
    evidence: 'Physical manifestation of anxiety in social situation',
    significance: 'moderate',
  },
];

const sessionTypeStyles = {
  intake: 'bg-blue-100 text-blue-700 dark:bg-blue-950 dark:text-blue-300',
  checkin: 'bg-green-100 text-green-700 dark:bg-green-950 dark:text-green-300',
  targeted_probe: 'bg-purple-100 text-purple-700 dark:bg-purple-950 dark:text-purple-300',
};

const sessionTypeLabels = {
  intake: 'Initial Intake',
  checkin: 'Check-in',
  targeted_probe: 'Targeted Probe',
};

const signalTypeColors = {
  emotional: 'bg-pink-100 text-pink-700 dark:bg-pink-950 dark:text-pink-300',
  social: 'bg-blue-100 text-blue-700 dark:bg-blue-950 dark:text-blue-300',
  behavioral: 'bg-orange-100 text-orange-700 dark:bg-orange-950 dark:text-orange-300',
  linguistic: 'bg-purple-100 text-purple-700 dark:bg-purple-950 dark:text-purple-300',
};

export default function SessionDetailPage() {
  return (
    <div className="space-y-6">
      {/* Header */}
      <motion.div
        initial={{ opacity: 0, y: -20 }}
        animate={{ opacity: 1, y: 0 }}
      >
        <Button variant="ghost" size="sm" className="mb-4 gap-2" asChild>
          <Link href="/sessions">
            <ArrowLeft className="h-4 w-4" />
            Back to Sessions
          </Link>
        </Button>

        <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
          {/* Session Info */}
          <div className="flex items-start gap-4">
            <div className="flex h-16 w-16 items-center justify-center rounded-2xl bg-gradient-to-br from-blue-500 to-purple-600 shadow-lg shadow-blue-500/25">
              <Mic className="h-8 w-8 text-white" />
            </div>
            <div>
              <div className="flex items-center gap-3">
                <h1 className="text-2xl font-bold tracking-tight text-neutral-900 dark:text-white">
                  {sessionTypeLabels[session.session_type as keyof typeof sessionTypeLabels]} Session
                </h1>
                <Badge
                  variant="secondary"
                  className={sessionTypeStyles[session.session_type as keyof typeof sessionTypeStyles]}
                >
                  {session.status}
                </Badge>
              </div>
              <div className="mt-2 flex flex-wrap items-center gap-4 text-sm text-neutral-500">
                <span className="flex items-center gap-1">
                  <User className="h-4 w-4" />
                  {session.patient_name}
                </span>
                <span className="flex items-center gap-1">
                  <Calendar className="h-4 w-4" />
                  {session.date}
                </span>
                <span className="flex items-center gap-1">
                  <Clock className="h-4 w-4" />
                  {session.duration}
                </span>
              </div>
            </div>
          </div>

          {/* Actions */}
          <div className="flex gap-2">
            <Button variant="outline" className="gap-2">
              <Play className="h-4 w-4" />
              Play Audio
            </Button>
            <Button variant="outline" className="gap-2">
              <Download className="h-4 w-4" />
              Export
            </Button>
            <Button className="gap-2 bg-blue-600 hover:bg-blue-700" asChild>
              <Link href={`/patients/${session.patient_id}`}>
                <User className="h-4 w-4" />
                View Patient
              </Link>
            </Button>
          </div>
        </div>
      </motion.div>

      {/* Summary Card */}
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ delay: 0.1 }}
      >
        <Card className="border-neutral-200 bg-white p-6 dark:border-neutral-800 dark:bg-neutral-900">
          <h2 className="text-lg font-semibold text-neutral-900 dark:text-white">
            Session Summary
          </h2>
          <p className="mt-2 text-neutral-600 dark:text-neutral-400">
            {session.summary}
          </p>
          <div className="mt-4 flex flex-wrap gap-2">
            {session.key_topics.map((topic) => (
              <Badge
                key={topic}
                variant="secondary"
                className="bg-neutral-100 text-neutral-600 dark:bg-neutral-800 dark:text-neutral-400"
              >
                {topic}
              </Badge>
            ))}
          </div>
        </Card>
      </motion.div>

      {/* Main Content */}
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ delay: 0.2 }}
      >
        <Tabs defaultValue="transcript" className="space-y-4">
          <TabsList className="bg-neutral-100 dark:bg-neutral-800">
            <TabsTrigger value="transcript">Transcript</TabsTrigger>
            <TabsTrigger value="signals">Clinical Signals ({signals.length})</TabsTrigger>
            <TabsTrigger value="notes">Notes</TabsTrigger>
          </TabsList>

          {/* Transcript Tab */}
          <TabsContent value="transcript">
            <Card className="border-neutral-200 bg-white dark:border-neutral-800 dark:bg-neutral-900">
              <ScrollArea className="h-[500px]">
                <div className="space-y-4 p-6">
                  {transcript.map((message, index) => (
                    <motion.div
                      key={message.id}
                      initial={{ opacity: 0, y: 10 }}
                      animate={{ opacity: 1, y: 0 }}
                      transition={{ delay: index * 0.05 }}
                      className={`flex ${
                        message.role === 'user' ? 'justify-end' : 'justify-start'
                      }`}
                    >
                      <div
                        className={`max-w-[70%] rounded-2xl px-4 py-3 ${
                          message.role === 'user'
                            ? 'bg-blue-600 text-white'
                            : 'bg-neutral-100 text-neutral-900 dark:bg-neutral-800 dark:text-white'
                        }`}
                      >
                        <p className="text-sm leading-relaxed">{message.content}</p>
                        <p
                          className={`mt-1 text-xs ${
                            message.role === 'user'
                              ? 'text-blue-200'
                              : 'text-neutral-400'
                          }`}
                        >
                          {message.timestamp}
                        </p>
                      </div>
                    </motion.div>
                  ))}
                </div>
              </ScrollArea>
            </Card>
          </TabsContent>

          {/* Signals Tab */}
          <TabsContent value="signals">
            <Card className="border-neutral-200 bg-white p-6 dark:border-neutral-800 dark:bg-neutral-900">
              <div className="mb-4 flex items-center justify-between">
                <div>
                  <h3 className="text-lg font-semibold text-neutral-900 dark:text-white">
                    Clinical Signals Detected
                  </h3>
                  <p className="text-sm text-neutral-500">
                    Observations extracted from the session
                  </p>
                </div>
                <div className="flex items-center gap-2">
                  <Brain className="h-5 w-5 text-purple-500" />
                  <span className="text-sm font-medium text-neutral-600 dark:text-neutral-400">
                    {signals.length} signals
                  </span>
                </div>
              </div>

              <div className="space-y-4">
                {signals.map((signal, index) => (
                  <motion.div
                    key={signal.id}
                    initial={{ opacity: 0, x: -10 }}
                    animate={{ opacity: 1, x: 0 }}
                    transition={{ delay: index * 0.1 }}
                    className="rounded-xl border border-neutral-200 p-4 dark:border-neutral-700"
                  >
                    <div className="flex items-start justify-between">
                      <div className="flex items-center gap-2">
                        <Badge
                          variant="secondary"
                          className={signalTypeColors[signal.type as keyof typeof signalTypeColors]}
                        >
                          {signal.type}
                        </Badge>
                        <span className="font-medium text-neutral-900 dark:text-white">
                          {signal.name}
                        </span>
                      </div>
                      <Badge
                        variant="secondary"
                        className={
                          signal.significance === 'high'
                            ? 'bg-red-100 text-red-700 dark:bg-red-950 dark:text-red-300'
                            : 'bg-yellow-100 text-yellow-700 dark:bg-yellow-950 dark:text-yellow-300'
                        }
                      >
                        {signal.significance}
                      </Badge>
                    </div>
                    <p className="mt-2 text-sm text-neutral-600 dark:text-neutral-400">
                      {signal.evidence}
                    </p>
                  </motion.div>
                ))}
              </div>
            </Card>
          </TabsContent>

          {/* Notes Tab */}
          <TabsContent value="notes">
            <Card className="border-neutral-200 bg-white p-6 dark:border-neutral-800 dark:bg-neutral-900">
              <div className="flex items-center gap-2">
                <FileText className="h-5 w-5 text-neutral-400" />
                <h3 className="text-lg font-semibold text-neutral-900 dark:text-white">
                  Clinical Notes
                </h3>
              </div>
              <p className="mt-4 text-neutral-500">
                No additional notes have been added to this session yet.
              </p>
              <Button className="mt-4" variant="outline">
                Add Notes
              </Button>
            </Card>
          </TabsContent>
        </Tabs>
      </motion.div>
    </div>
  );
}
