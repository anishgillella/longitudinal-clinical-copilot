'use client';

import { motion } from 'framer-motion';
import { StatsCards } from '@/components/dashboard/stats-cards';
import { QuickActions } from '@/components/dashboard/quick-actions';
import { RecentSessions } from '@/components/dashboard/recent-sessions';
import { PatientOverview } from '@/components/dashboard/patient-overview';

export default function DashboardPage() {
  return (
    <div className="space-y-8">
      {/* Welcome Header */}
      <motion.div
        initial={{ opacity: 0, y: -20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5 }}
      >
        <h1 className="text-3xl font-bold tracking-tight text-neutral-900 dark:text-white">
          Good afternoon, Dr. Chen
        </h1>
        <p className="mt-1 text-neutral-500">
          Here&apos;s what&apos;s happening with your patients today.
        </p>
      </motion.div>

      {/* Quick Actions */}
      <motion.section
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ delay: 0.1 }}
      >
        <QuickActions />
      </motion.section>

      {/* Stats Cards */}
      <motion.section
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ delay: 0.2 }}
      >
        <StatsCards />
      </motion.section>

      {/* Two Column Layout */}
      <div className="grid gap-6 lg:grid-cols-2">
        <motion.div
          initial={{ opacity: 0, x: -20 }}
          animate={{ opacity: 1, x: 0 }}
          transition={{ delay: 0.3 }}
        >
          <RecentSessions />
        </motion.div>

        <motion.div
          initial={{ opacity: 0, x: 20 }}
          animate={{ opacity: 1, x: 0 }}
          transition={{ delay: 0.4 }}
        >
          <PatientOverview />
        </motion.div>
      </div>
    </div>
  );
}
