'use client';

import { useState } from 'react';
import { motion } from 'framer-motion';
import {
  Search,
  Filter,
  Calendar,
  Clock,
  Play,
  FileText,
  ArrowUpDown,
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Card } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
import Link from 'next/link';

interface Session {
  id: string;
  patient_name: string;
  patient_id: string;
  session_type: 'intake' | 'checkin' | 'targeted_probe';
  status: 'completed' | 'active' | 'scheduled' | 'failed';
  date: string;
  time: string;
  duration?: string;
  summary?: string;
  signals_detected?: number;
}

const mockSessions: Session[] = [
  {
    id: '1',
    patient_name: 'Alex Thompson',
    patient_id: '1',
    session_type: 'checkin',
    status: 'completed',
    date: 'Dec 22, 2024',
    time: '2:30 PM',
    duration: '32 min',
    summary: 'Discussed recent school challenges and peer interactions. Notable improvement in...',
    signals_detected: 8,
  },
  {
    id: '2',
    patient_name: 'Jordan Martinez',
    patient_id: '2',
    session_type: 'targeted_probe',
    status: 'completed',
    date: 'Dec 21, 2024',
    time: '11:00 AM',
    duration: '28 min',
    summary: 'Explored sensory processing concerns in detail. Patient reported...',
    signals_detected: 12,
  },
  {
    id: '3',
    patient_name: 'Sam Wilson',
    patient_id: '3',
    session_type: 'intake',
    status: 'completed',
    date: 'Dec 20, 2024',
    time: '3:00 PM',
    duration: '45 min',
    summary: 'Initial intake session. Covered developmental history, current concerns...',
    signals_detected: 15,
  },
  {
    id: '4',
    patient_name: 'Alex Thompson',
    patient_id: '1',
    session_type: 'checkin',
    status: 'scheduled',
    date: 'Dec 23, 2024',
    time: '10:00 AM',
  },
  {
    id: '5',
    patient_name: 'Casey Brown',
    patient_id: '4',
    session_type: 'targeted_probe',
    status: 'scheduled',
    date: 'Dec 24, 2024',
    time: '2:00 PM',
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
  failed: 'bg-red-100 text-red-700 dark:bg-red-950 dark:text-red-300',
};

export default function SessionsPage() {
  const [searchQuery, setSearchQuery] = useState('');
  const [statusFilter, setStatusFilter] = useState<string>('all');

  const filteredSessions = mockSessions.filter((session) => {
    const matchesSearch = session.patient_name
      .toLowerCase()
      .includes(searchQuery.toLowerCase());
    const matchesStatus =
      statusFilter === 'all' || session.status === statusFilter;
    return matchesSearch && matchesStatus;
  });

  const completedSessions = filteredSessions.filter(
    (s) => s.status === 'completed'
  );
  const upcomingSessions = filteredSessions.filter(
    (s) => s.status === 'scheduled'
  );

  return (
    <div className="space-y-6">
      {/* Header */}
      <motion.div
        initial={{ opacity: 0, y: -20 }}
        animate={{ opacity: 1, y: 0 }}
        className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between"
      >
        <div>
          <h1 className="text-3xl font-bold tracking-tight text-neutral-900 dark:text-white">
            Sessions
          </h1>
          <p className="mt-1 text-neutral-500">
            View and manage voice session history
          </p>
        </div>
        <Button className="gap-2 bg-blue-600 hover:bg-blue-700" asChild>
          <Link href="/voice">
            <Play className="h-4 w-4" />
            New Session
          </Link>
        </Button>
      </motion.div>

      {/* Filters */}
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ delay: 0.1 }}
        className="flex flex-col gap-4 sm:flex-row sm:items-center"
      >
        <div className="relative flex-1">
          <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-neutral-400" />
          <Input
            placeholder="Search by patient name..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="pl-10"
          />
        </div>
        <div className="flex gap-2">
          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <Button variant="outline" className="gap-2">
                <Filter className="h-4 w-4" />
                {statusFilter === 'all'
                  ? 'All Status'
                  : statusFilter.charAt(0).toUpperCase() + statusFilter.slice(1)}
              </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent>
              <DropdownMenuItem onClick={() => setStatusFilter('all')}>
                All Status
              </DropdownMenuItem>
              <DropdownMenuItem onClick={() => setStatusFilter('completed')}>
                Completed
              </DropdownMenuItem>
              <DropdownMenuItem onClick={() => setStatusFilter('scheduled')}>
                Scheduled
              </DropdownMenuItem>
              <DropdownMenuItem onClick={() => setStatusFilter('active')}>
                Active
              </DropdownMenuItem>
            </DropdownMenuContent>
          </DropdownMenu>
          <Button variant="outline" className="gap-2">
            <ArrowUpDown className="h-4 w-4" />
            Sort
          </Button>
        </div>
      </motion.div>

      {/* Upcoming Sessions */}
      {upcomingSessions.length > 0 && (
        <motion.section
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 0.2 }}
        >
          <h2 className="mb-4 text-lg font-semibold text-neutral-900 dark:text-white">
            Upcoming Sessions
          </h2>
          <div className="grid gap-4 md:grid-cols-2">
            {upcomingSessions.map((session, index) => (
              <motion.div
                key={session.id}
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: index * 0.1 }}
              >
                <Card className="border-neutral-200 bg-white p-5 dark:border-neutral-800 dark:bg-neutral-900">
                  <div className="flex items-start justify-between">
                    <div className="flex items-center gap-3">
                      <div className="flex h-12 w-12 items-center justify-center rounded-full bg-gradient-to-br from-blue-500 to-purple-600 text-lg font-semibold text-white">
                        {session.patient_name
                          .split(' ')
                          .map((n) => n[0])
                          .join('')}
                      </div>
                      <div>
                        <h3 className="font-semibold text-neutral-900 dark:text-white">
                          {session.patient_name}
                        </h3>
                        <div className="flex items-center gap-2 text-sm text-neutral-500">
                          <Calendar className="h-3 w-3" />
                          {session.date} at {session.time}
                        </div>
                      </div>
                    </div>
                    <Badge
                      variant="secondary"
                      className={sessionTypeStyles[session.session_type]}
                    >
                      {sessionTypeLabels[session.session_type]}
                    </Badge>
                  </div>
                  <div className="mt-4 flex gap-2">
                    <Button
                      className="flex-1 gap-2 bg-green-600 hover:bg-green-700"
                      asChild
                    >
                      <Link href={`/voice?patient=${session.patient_id}`}>
                        <Play className="h-4 w-4" />
                        Start Now
                      </Link>
                    </Button>
                    <Button variant="outline">Reschedule</Button>
                  </div>
                </Card>
              </motion.div>
            ))}
          </div>
        </motion.section>
      )}

      {/* Completed Sessions */}
      <motion.section
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ delay: 0.3 }}
      >
        <h2 className="mb-4 text-lg font-semibold text-neutral-900 dark:text-white">
          Session History
        </h2>
        <Card className="border-neutral-200 bg-white dark:border-neutral-800 dark:bg-neutral-900">
          <div className="divide-y divide-neutral-200 dark:divide-neutral-800">
            {completedSessions.map((session, index) => (
              <motion.div
                key={session.id}
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                transition={{ delay: index * 0.05 }}
              >
                <Link href={`/sessions/${session.id}`}>
                  <div className="flex items-center gap-4 p-4 transition-colors hover:bg-neutral-50 dark:hover:bg-neutral-800/50">
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
                          <Calendar className="h-3 w-3" />
                          {session.date}
                        </span>
                        {session.duration && (
                          <span className="flex items-center gap-1">
                            <Clock className="h-3 w-3" />
                            {session.duration}
                          </span>
                        )}
                        {session.signals_detected && (
                          <span>{session.signals_detected} signals detected</span>
                        )}
                      </div>
                    </div>

                    {/* Actions */}
                    <div className="flex items-center gap-2">
                      <Button variant="ghost" size="sm" className="gap-1">
                        <FileText className="h-4 w-4" />
                        View
                      </Button>
                    </div>
                  </div>
                </Link>
              </motion.div>
            ))}
          </div>
        </Card>
      </motion.section>
    </div>
  );
}
