'use client';

import { motion } from 'framer-motion';
import { Users, Activity, Brain, AlertTriangle, TrendingUp, TrendingDown } from 'lucide-react';
import { Card } from '@/components/ui/card';

interface StatCardProps {
  title: string;
  value: string | number;
  change?: number;
  icon: React.ElementType;
  iconColor: string;
  iconBg: string;
  delay?: number;
}

function StatCard({ title, value, change, icon: Icon, iconColor, iconBg, delay = 0 }: StatCardProps) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.5, delay }}
    >
      <Card className="relative overflow-hidden border-neutral-200 bg-white p-6 dark:border-neutral-800 dark:bg-neutral-900">
        <div className="flex items-start justify-between">
          <div>
            <p className="text-sm font-medium text-neutral-500 dark:text-neutral-400">
              {title}
            </p>
            <motion.p
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              transition={{ delay: delay + 0.2 }}
              className="mt-2 text-3xl font-bold tracking-tight text-neutral-900 dark:text-white"
            >
              {value}
            </motion.p>
            {change !== undefined && (
              <div className="mt-2 flex items-center gap-1">
                {change >= 0 ? (
                  <TrendingUp className="h-4 w-4 text-green-500" />
                ) : (
                  <TrendingDown className="h-4 w-4 text-red-500" />
                )}
                <span
                  className={`text-sm font-medium ${
                    change >= 0 ? 'text-green-600' : 'text-red-600'
                  }`}
                >
                  {change >= 0 ? '+' : ''}
                  {change}%
                </span>
                <span className="text-sm text-neutral-500">vs last week</span>
              </div>
            )}
          </div>
          <div
            className={`flex h-12 w-12 items-center justify-center rounded-2xl ${iconBg}`}
          >
            <Icon className={`h-6 w-6 ${iconColor}`} />
          </div>
        </div>

        {/* Decorative gradient */}
        <div className="absolute -right-6 -top-6 h-24 w-24 rounded-full bg-gradient-to-br from-neutral-100 to-transparent opacity-50 dark:from-neutral-800" />
      </Card>
    </motion.div>
  );
}

interface StatsCardsProps {
  metrics?: {
    total_patients: number;
    active_patients: number;
    sessions_this_week: number;
    assessments_in_progress: number;
    high_confidence_hypotheses: number;
    urgent_concerns: number;
  };
}

export function StatsCards({ metrics }: StatsCardsProps) {
  const defaultMetrics = {
    total_patients: 24,
    active_patients: 18,
    sessions_this_week: 12,
    assessments_in_progress: 8,
    high_confidence_hypotheses: 5,
    urgent_concerns: 2,
  };

  const data = metrics || defaultMetrics;

  const stats = [
    {
      title: 'Active Patients',
      value: data.active_patients,
      change: 12,
      icon: Users,
      iconColor: 'text-blue-600',
      iconBg: 'bg-blue-100 dark:bg-blue-950',
    },
    {
      title: 'Sessions This Week',
      value: data.sessions_this_week,
      change: 8,
      icon: Activity,
      iconColor: 'text-green-600',
      iconBg: 'bg-green-100 dark:bg-green-950',
    },
    {
      title: 'Assessments in Progress',
      value: data.assessments_in_progress,
      change: -3,
      icon: Brain,
      iconColor: 'text-purple-600',
      iconBg: 'bg-purple-100 dark:bg-purple-950',
    },
    {
      title: 'Urgent Concerns',
      value: data.urgent_concerns,
      icon: AlertTriangle,
      iconColor: 'text-orange-600',
      iconBg: 'bg-orange-100 dark:bg-orange-950',
    },
  ];

  return (
    <div className="grid gap-6 sm:grid-cols-2 lg:grid-cols-4">
      {stats.map((stat, index) => (
        <StatCard key={stat.title} {...stat} delay={index * 0.1} />
      ))}
    </div>
  );
}
