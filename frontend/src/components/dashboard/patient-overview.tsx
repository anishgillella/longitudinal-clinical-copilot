'use client';

import { motion } from 'framer-motion';
import { ArrowRight, Circle } from 'lucide-react';
import { Card } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Progress } from '@/components/ui/progress';
import Link from 'next/link';

interface PatientOverview {
  id: string;
  name: string;
  status: 'active' | 'on_hold' | 'completed';
  progress: number;
  lastSession: string;
  primaryHypothesis?: string;
  confidenceLevel?: number;
}

const mockPatients: PatientOverview[] = [
  {
    id: '1',
    name: 'Alex Thompson',
    status: 'active',
    progress: 65,
    lastSession: '2 hours ago',
    primaryHypothesis: 'ASD Level 1',
    confidenceLevel: 72,
  },
  {
    id: '2',
    name: 'Jordan Martinez',
    status: 'active',
    progress: 45,
    lastSession: 'Yesterday',
    primaryHypothesis: 'Under assessment',
    confidenceLevel: 38,
  },
  {
    id: '3',
    name: 'Sam Wilson',
    status: 'active',
    progress: 20,
    lastSession: '3 days ago',
  },
  {
    id: '4',
    name: 'Casey Brown',
    status: 'on_hold',
    progress: 80,
    lastSession: '1 week ago',
    primaryHypothesis: 'ASD Level 2',
    confidenceLevel: 85,
  },
];

const statusColors = {
  active: 'text-green-500',
  on_hold: 'text-yellow-500',
  completed: 'text-blue-500',
};

export function PatientOverview() {
  return (
    <Card className="border-neutral-200 bg-white p-6 dark:border-neutral-800 dark:bg-neutral-900">
      <div className="mb-6 flex items-center justify-between">
        <div>
          <h2 className="text-lg font-semibold text-neutral-900 dark:text-white">
            Patient Overview
          </h2>
          <p className="text-sm text-neutral-500">Assessment progress at a glance</p>
        </div>
        <Button variant="ghost" size="sm" className="gap-1" asChild>
          <Link href="/patients">
            View all
            <ArrowRight className="h-4 w-4" />
          </Link>
        </Button>
      </div>

      <div className="space-y-4">
        {mockPatients.map((patient, index) => (
          <motion.div
            key={patient.id}
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: index * 0.1 }}
          >
            <Link href={`/patients/${patient.id}`}>
              <div className="group rounded-xl p-4 transition-colors hover:bg-neutral-50 dark:hover:bg-neutral-800/50">
                <div className="flex items-start justify-between">
                  <div className="flex items-center gap-3">
                    {/* Status indicator */}
                    <Circle
                      className={`h-2.5 w-2.5 fill-current ${statusColors[patient.status]}`}
                    />
                    <div>
                      <p className="font-medium text-neutral-900 dark:text-white">
                        {patient.name}
                      </p>
                      <p className="text-sm text-neutral-500">
                        Last session: {patient.lastSession}
                      </p>
                    </div>
                  </div>
                  {patient.primaryHypothesis && (
                    <Badge
                      variant="secondary"
                      className="bg-neutral-100 text-neutral-600 dark:bg-neutral-800 dark:text-neutral-400"
                    >
                      {patient.primaryHypothesis}
                      {patient.confidenceLevel && (
                        <span className="ml-1 text-neutral-400">
                          ({patient.confidenceLevel}%)
                        </span>
                      )}
                    </Badge>
                  )}
                </div>

                {/* Progress bar */}
                <div className="mt-3">
                  <div className="mb-1 flex items-center justify-between text-xs">
                    <span className="text-neutral-500">Assessment Progress</span>
                    <span className="font-medium text-neutral-700 dark:text-neutral-300">
                      {patient.progress}%
                    </span>
                  </div>
                  <Progress value={patient.progress} className="h-1.5" />
                </div>
              </div>
            </Link>
          </motion.div>
        ))}
      </div>
    </Card>
  );
}
