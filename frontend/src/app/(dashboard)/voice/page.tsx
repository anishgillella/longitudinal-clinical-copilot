'use client';

import { useState, useCallback } from 'react';
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
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Card } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
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

// Mock patients for selection
const patients = [
  { id: '1', name: 'Alex Thompson', age: 12 },
  { id: '2', name: 'Jordan Martinez', age: 10 },
  { id: '3', name: 'Sam Wilson', age: 13 },
];

export default function VoiceSessionPage() {
  const [selectedPatient, setSelectedPatient] = useState<typeof patients[0] | null>(null);
  const [sessionType, setSessionType] = useState<'intake' | 'checkin' | 'targeted_probe'>('checkin');
  const [messages, setMessages] = useState<Message[]>([]);
  const [isMuted, setIsMuted] = useState(false);
  const [callDuration, setCallDuration] = useState(0);

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
    const interval = setInterval(() => {
      setCallDuration((d) => d + 1);
    }, 1000);
    return () => clearInterval(interval);
  }, []);

  const { isCallActive, isSpeaking, volumeLevel, startCall, endCall, toggleMute } =
    useVapi({
      onTranscript: handleTranscript,
      onCallStart: handleCallStart,
    });

  const handleStartCall = async () => {
    if (!selectedPatient) return;
    try {
      await startCall();
    } catch (error) {
      console.error('Failed to start call:', error);
    }
  };

  const handleEndCall = () => {
    endCall();
  };

  const handleToggleMute = () => {
    const newMutedState = toggleMute();
    setIsMuted(newMutedState ?? false);
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

  return (
    <div className="flex h-[calc(100vh-8rem)] gap-6">
      {/* Main Voice Area */}
      <div className="flex flex-1 flex-col">
        {/* Pre-call Setup */}
        <AnimatePresence mode="wait">
          {!isCallActive ? (
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

                {/* Start Button */}
                <Button
                  size="lg"
                  className="mt-8 w-full gap-2 bg-green-600 py-6 text-lg hover:bg-green-700"
                  disabled={!selectedPatient}
                  onClick={handleStartCall}
                >
                  <Phone className="h-5 w-5" />
                  Start Session
                </Button>

                {!selectedPatient && (
                  <p className="mt-4 flex items-center justify-center gap-2 text-sm text-orange-600">
                    <AlertCircle className="h-4 w-4" />
                    Please select a patient first
                  </p>
                )}
              </Card>
            </motion.div>
          ) : (
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
        </AnimatePresence>
      </div>

      {/* Transcript Panel */}
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
              {isCallActive
                ? 'Real-time conversation transcript'
                : 'Transcript will appear here during the session'}
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
                  {isCallActive
                    ? 'Waiting for speech...'
                    : 'Start a session to see the transcript'}
                </p>
              </div>
            )}
          </div>
        </Card>
      </motion.div>
    </div>
  );
}
