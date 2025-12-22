'use client';

import { motion } from 'framer-motion';
import { Clock, ArrowRight, Play } from 'lucide-react';
import { Card } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import Link from 'next/link';

interface Session {
  id: string;
  patient_name: string;
  session_type: 'intake' | 'checkin' | 'targeted_probe';
  status: 'completed' | 'active' | 'scheduled';
  date: string;
  duration?: string;
  summary?: string;
}

const mockSessions: Session[] = [
  {
    id: '1',
    patient_name: 'Alex Thompson',
    session_type: 'intake',
    status: 'completed',
    date: '2 hours ago',
    duration: '32 min',
    summary: 'Initial assessment focusing on social communication patterns...',
  },
  {
    id: '2',
    patient_name: 'Jordan Martinez',
    session_type: 'checkin',
    status: 'completed',
    date: 'Yesterday',
    duration: '18 min',
    summary: 'Follow-up on sensory processing concerns...',
  },
  {
    id: '3',
    patient_name: 'Sam Wilson',
    session_type: 'targeted_probe',
    status: 'scheduled',
    date: 'Tomorrow, 2:00 PM',
  },
];

const sessionTypeStyles = {
  intake: 'bg-blue-100 text-blue-700 dark:bg-blue-950 dark:text-blue-300',
  checkin: 'bg-green-100 text-green-700 dark:bg-green-950 dark:text-green-300',
  targeted_probe: 'bg-purple-100 text-purple-700 dark:bg-purple-950 dark:text-purple-300',
};

const sessionTypeLabels = {
  intake: 'Intake',
  checkin: 'Check-in',
  targeted_probe: 'Targeted Probe',
};

const statusStyles = {
  completed: 'bg-neutral-100 text-neutral-600 dark:bg-neutral-800 dark:text-neutral-400',
  active: 'bg-green-100 text-green-700 dark:bg-green-950 dark:text-green-300',
  scheduled: 'bg-yellow-100 text-yellow-700 dark:bg-yellow-950 dark:text-yellow-300',
};

export function RecentSessions() {
  return (
    <Card className="border-neutral-200 bg-white p-6 dark:border-neutral-800 dark:bg-neutral-900">
      <div className="mb-6 flex items-center justify-between">
        <div>
          <h2 className="text-lg font-semibold text-neutral-900 dark:text-white">
            Recent Sessions
          </h2>
          <p className="text-sm text-neutral-500">Your latest voice sessions</p>
        </div>
        <Button variant="ghost" size="sm" className="gap-1" asChild>
          <Link href="/sessions">
            View all
            <ArrowRight className="h-4 w-4" />
          </Link>
        </Button>
      </div>

      <div className="space-y-4">
        {mockSessions.map((session, index) => (
          <motion.div
            key={session.id}
            initial={{ opacity: 0, x: -20 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ delay: index * 0.1 }}
          >
            <Link href={`/sessions/${session.id}`}>
              <div className="group flex items-center gap-4 rounded-xl p-3 transition-colors hover:bg-neutral-50 dark:hover:bg-neutral-800/50">
                {/* Avatar */}
                <div className="flex h-12 w-12 items-center justify-center rounded-full bg-gradient-to-br from-neutral-200 to-neutral-300 text-sm font-semibold text-neutral-600 dark:from-neutral-700 dark:to-neutral-800 dark:text-neutral-300">
                  {session.patient_name
                    .split(' ')
                    .map((n) => n[0])
                    .join('')}
                </div>

                {/* Content */}
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2">
                    <p className="font-medium text-neutral-900 dark:text-white">
                      {session.patient_name}
                    </p>
                    <Badge
                      variant="secondary"
                      className={sessionTypeStyles[session.session_type]}
                    >
                      {sessionTypeLabels[session.session_type]}
                    </Badge>
                  </div>
                  {session.summary && (
                    <p className="mt-1 truncate text-sm text-neutral-500">
                      {session.summary}
                    </p>
                  )}
                  <div className="mt-1 flex items-center gap-3 text-xs text-neutral-400">
                    <span className="flex items-center gap-1">
                      <Clock className="h-3 w-3" />
                      {session.date}
                    </span>
                    {session.duration && (
                      <span>{session.duration}</span>
                    )}
                  </div>
                </div>

                {/* Status/Action */}
                <div className="flex items-center gap-2">
                  <Badge
                    variant="secondary"
                    className={statusStyles[session.status]}
                  >
                    {session.status}
                  </Badge>
                  {session.status === 'scheduled' && (
                    <Button size="icon" variant="ghost" className="h-8 w-8">
                      <Play className="h-4 w-4" />
                    </Button>
                  )}
                </div>
              </div>
            </Link>
          </motion.div>
        ))}
      </div>
    </Card>
  );
}
