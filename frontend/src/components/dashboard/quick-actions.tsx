'use client';

import { motion } from 'framer-motion';
import { Mic, UserPlus, FileText, Calendar } from 'lucide-react';
import { Card } from '@/components/ui/card';
import Link from 'next/link';

const actions = [
  {
    title: 'Start Voice Session',
    description: 'Begin a new clinical voice session',
    href: '/voice',
    icon: Mic,
    color: 'from-blue-500 to-blue-600',
    shadowColor: 'shadow-blue-500/25',
  },
  {
    title: 'Add Patient',
    description: 'Register a new patient',
    href: '/patients/new',
    icon: UserPlus,
    color: 'from-green-500 to-green-600',
    shadowColor: 'shadow-green-500/25',
  },
  {
    title: 'Generate Report',
    description: 'Create an assessment report',
    href: '/reports/new',
    icon: FileText,
    color: 'from-purple-500 to-purple-600',
    shadowColor: 'shadow-purple-500/25',
  },
  {
    title: 'Schedule Session',
    description: 'Plan upcoming sessions',
    href: '/sessions/schedule',
    icon: Calendar,
    color: 'from-orange-500 to-orange-600',
    shadowColor: 'shadow-orange-500/25',
  },
];

export function QuickActions() {
  return (
    <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
      {actions.map((action, index) => (
        <motion.div
          key={action.title}
          initial={{ opacity: 0, scale: 0.95 }}
          animate={{ opacity: 1, scale: 1 }}
          transition={{ delay: index * 0.1 }}
          whileHover={{ scale: 1.02 }}
          whileTap={{ scale: 0.98 }}
        >
          <Link href={action.href}>
            <Card className="group relative cursor-pointer overflow-hidden border-neutral-200 bg-white p-6 transition-all hover:border-neutral-300 hover:shadow-lg dark:border-neutral-800 dark:bg-neutral-900 dark:hover:border-neutral-700">
              <div
                className={`mb-4 flex h-12 w-12 items-center justify-center rounded-2xl bg-gradient-to-br ${action.color} shadow-lg ${action.shadowColor}`}
              >
                <action.icon className="h-6 w-6 text-white" />
              </div>

              <h3 className="font-semibold text-neutral-900 dark:text-white">
                {action.title}
              </h3>
              <p className="mt-1 text-sm text-neutral-500">
                {action.description}
              </p>

              {/* Hover effect */}
              <div className="absolute inset-0 bg-gradient-to-br from-white/0 to-neutral-100/0 transition-all group-hover:from-white/50 group-hover:to-neutral-100/20 dark:group-hover:from-neutral-800/50 dark:group-hover:to-neutral-900/20" />
            </Card>
          </Link>
        </motion.div>
      ))}
    </div>
  );
}
