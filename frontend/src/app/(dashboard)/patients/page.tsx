'use client';

import { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
  Plus,
  Search,
  Filter,
  MoreVertical,
  Phone,
  Mail,
  Calendar,
  Circle,
  ArrowUpDown,
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Card } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Progress } from '@/components/ui/progress';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
import Link from 'next/link';

interface Patient {
  id: string;
  first_name: string;
  last_name: string;
  date_of_birth: string;
  email?: string;
  phone?: string;
  status: 'active' | 'inactive' | 'archived';
  primary_concern?: string;
  intake_date?: string;
  sessions_count: number;
  assessment_progress: number;
  last_session?: string;
  hypothesis?: string;
  hypothesis_confidence?: number;
}

const mockPatients: Patient[] = [
  {
    id: '1',
    first_name: 'Alex',
    last_name: 'Thompson',
    date_of_birth: '2012-03-15',
    email: 'parent@email.com',
    phone: '(555) 123-4567',
    status: 'active',
    primary_concern: 'Social communication difficulties',
    intake_date: '2024-11-15',
    sessions_count: 5,
    assessment_progress: 65,
    last_session: '2 hours ago',
    hypothesis: 'ASD Level 1',
    hypothesis_confidence: 72,
  },
  {
    id: '2',
    first_name: 'Jordan',
    last_name: 'Martinez',
    date_of_birth: '2014-07-22',
    email: 'jmartinez@email.com',
    phone: '(555) 234-5678',
    status: 'active',
    primary_concern: 'Sensory processing concerns',
    intake_date: '2024-12-01',
    sessions_count: 3,
    assessment_progress: 45,
    last_session: 'Yesterday',
    hypothesis: 'Under assessment',
    hypothesis_confidence: 38,
  },
  {
    id: '3',
    first_name: 'Sam',
    last_name: 'Wilson',
    date_of_birth: '2011-11-08',
    phone: '(555) 345-6789',
    status: 'active',
    primary_concern: 'Executive function challenges',
    intake_date: '2024-12-10',
    sessions_count: 2,
    assessment_progress: 20,
    last_session: '3 days ago',
  },
  {
    id: '4',
    first_name: 'Casey',
    last_name: 'Brown',
    date_of_birth: '2013-05-30',
    email: 'cbrown@email.com',
    phone: '(555) 456-7890',
    status: 'inactive',
    primary_concern: 'Attention and focus issues',
    intake_date: '2024-10-01',
    sessions_count: 8,
    assessment_progress: 80,
    last_session: '1 week ago',
    hypothesis: 'ASD Level 2',
    hypothesis_confidence: 85,
  },
  {
    id: '5',
    first_name: 'Riley',
    last_name: 'Davis',
    date_of_birth: '2015-01-12',
    email: 'rdavis@email.com',
    status: 'active',
    primary_concern: 'Behavioral concerns at school',
    intake_date: '2024-12-15',
    sessions_count: 1,
    assessment_progress: 10,
    last_session: '5 days ago',
  },
];

const statusColors = {
  active: 'bg-green-500',
  inactive: 'bg-yellow-500',
  archived: 'bg-neutral-400',
};

const statusLabels = {
  active: 'Active',
  inactive: 'On Hold',
  archived: 'Archived',
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

export default function PatientsPage() {
  const [searchQuery, setSearchQuery] = useState('');
  const [statusFilter, setStatusFilter] = useState<string>('all');

  const filteredPatients = mockPatients.filter((patient) => {
    const matchesSearch =
      `${patient.first_name} ${patient.last_name}`
        .toLowerCase()
        .includes(searchQuery.toLowerCase()) ||
      patient.primary_concern?.toLowerCase().includes(searchQuery.toLowerCase());
    const matchesStatus = statusFilter === 'all' || patient.status === statusFilter;
    return matchesSearch && matchesStatus;
  });

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
            Patients
          </h1>
          <p className="mt-1 text-neutral-500">
            Manage and track your patient assessments
          </p>
        </div>
        <Button className="gap-2 bg-blue-600 hover:bg-blue-700" asChild>
          <Link href="/patients/new">
            <Plus className="h-4 w-4" />
            Add Patient
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
            placeholder="Search patients..."
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
                {statusFilter === 'all' ? 'All Status' : statusLabels[statusFilter as keyof typeof statusLabels]}
              </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent>
              <DropdownMenuItem onClick={() => setStatusFilter('all')}>
                All Status
              </DropdownMenuItem>
              <DropdownMenuItem onClick={() => setStatusFilter('active')}>
                Active
              </DropdownMenuItem>
              <DropdownMenuItem onClick={() => setStatusFilter('inactive')}>
                On Hold
              </DropdownMenuItem>
              <DropdownMenuItem onClick={() => setStatusFilter('archived')}>
                Archived
              </DropdownMenuItem>
            </DropdownMenuContent>
          </DropdownMenu>
          <Button variant="outline" className="gap-2">
            <ArrowUpDown className="h-4 w-4" />
            Sort
          </Button>
        </div>
      </motion.div>

      {/* Patient Cards */}
      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
        <AnimatePresence mode="popLayout">
          {filteredPatients.map((patient, index) => (
            <motion.div
              key={patient.id}
              initial={{ opacity: 0, scale: 0.95 }}
              animate={{ opacity: 1, scale: 1 }}
              exit={{ opacity: 0, scale: 0.95 }}
              transition={{ delay: index * 0.05 }}
              layout
            >
              <Link href={`/patients/${patient.id}`}>
                <Card className="group cursor-pointer overflow-hidden border-neutral-200 bg-white p-5 transition-all hover:border-neutral-300 hover:shadow-lg dark:border-neutral-800 dark:bg-neutral-900 dark:hover:border-neutral-700">
                  {/* Header */}
                  <div className="flex items-start justify-between">
                    <div className="flex items-center gap-3">
                      <div className="flex h-12 w-12 items-center justify-center rounded-full bg-gradient-to-br from-blue-500 to-purple-600 text-lg font-semibold text-white shadow-lg shadow-blue-500/25">
                        {patient.first_name[0]}
                        {patient.last_name[0]}
                      </div>
                      <div>
                        <h3 className="font-semibold text-neutral-900 dark:text-white">
                          {patient.first_name} {patient.last_name}
                        </h3>
                        <div className="flex items-center gap-2 text-sm text-neutral-500">
                          <span>{calculateAge(patient.date_of_birth)} years old</span>
                          <Circle
                            className={`h-2 w-2 fill-current ${statusColors[patient.status]}`}
                          />
                        </div>
                      </div>
                    </div>
                    <DropdownMenu>
                      <DropdownMenuTrigger asChild>
                        <Button
                          variant="ghost"
                          size="icon"
                          className="h-8 w-8 opacity-0 transition-opacity group-hover:opacity-100"
                          onClick={(e) => e.preventDefault()}
                        >
                          <MoreVertical className="h-4 w-4" />
                        </Button>
                      </DropdownMenuTrigger>
                      <DropdownMenuContent align="end">
                        <DropdownMenuItem>View Profile</DropdownMenuItem>
                        <DropdownMenuItem>Start Session</DropdownMenuItem>
                        <DropdownMenuItem>Edit Patient</DropdownMenuItem>
                        <DropdownMenuItem className="text-red-600">
                          Archive
                        </DropdownMenuItem>
                      </DropdownMenuContent>
                    </DropdownMenu>
                  </div>

                  {/* Primary Concern */}
                  {patient.primary_concern && (
                    <p className="mt-3 text-sm text-neutral-600 dark:text-neutral-400">
                      {patient.primary_concern}
                    </p>
                  )}

                  {/* Progress */}
                  <div className="mt-4">
                    <div className="mb-1 flex items-center justify-between text-xs">
                      <span className="text-neutral-500">Assessment Progress</span>
                      <span className="font-medium text-neutral-700 dark:text-neutral-300">
                        {patient.assessment_progress}%
                      </span>
                    </div>
                    <Progress value={patient.assessment_progress} className="h-1.5" />
                  </div>

                  {/* Hypothesis */}
                  {patient.hypothesis && (
                    <div className="mt-4 flex items-center justify-between">
                      <Badge
                        variant="secondary"
                        className="bg-purple-100 text-purple-700 dark:bg-purple-950 dark:text-purple-300"
                      >
                        {patient.hypothesis}
                      </Badge>
                      {patient.hypothesis_confidence && (
                        <span className="text-xs text-neutral-500">
                          {patient.hypothesis_confidence}% confidence
                        </span>
                      )}
                    </div>
                  )}

                  {/* Footer */}
                  <div className="mt-4 flex items-center justify-between border-t border-neutral-100 pt-4 dark:border-neutral-800">
                    <div className="flex items-center gap-4 text-xs text-neutral-500">
                      <span>{patient.sessions_count} sessions</span>
                      <span>Last: {patient.last_session}</span>
                    </div>
                    <div className="flex items-center gap-1">
                      {patient.phone && (
                        <Button
                          variant="ghost"
                          size="icon"
                          className="h-7 w-7"
                          onClick={(e) => e.preventDefault()}
                        >
                          <Phone className="h-3.5 w-3.5" />
                        </Button>
                      )}
                      {patient.email && (
                        <Button
                          variant="ghost"
                          size="icon"
                          className="h-7 w-7"
                          onClick={(e) => e.preventDefault()}
                        >
                          <Mail className="h-3.5 w-3.5" />
                        </Button>
                      )}
                    </div>
                  </div>
                </Card>
              </Link>
            </motion.div>
          ))}
        </AnimatePresence>
      </div>

      {/* Empty State */}
      {filteredPatients.length === 0 && (
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          className="flex flex-col items-center justify-center py-12 text-center"
        >
          <div className="flex h-16 w-16 items-center justify-center rounded-full bg-neutral-100 dark:bg-neutral-800">
            <Search className="h-8 w-8 text-neutral-400" />
          </div>
          <h3 className="mt-4 text-lg font-medium text-neutral-900 dark:text-white">
            No patients found
          </h3>
          <p className="mt-1 text-neutral-500">
            Try adjusting your search or filter criteria
          </p>
        </motion.div>
      )}
    </div>
  );
}
