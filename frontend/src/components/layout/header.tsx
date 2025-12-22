'use client';

import { Bell, Search, Moon, Sun } from 'lucide-react';
import { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';

export function Header() {
  const [isDark, setIsDark] = useState(false);
  const [showSearch, setShowSearch] = useState(false);

  useEffect(() => {
    const isDarkMode = document.documentElement.classList.contains('dark');
    setIsDark(isDarkMode);
  }, []);

  const toggleTheme = () => {
    setIsDark(!isDark);
    document.documentElement.classList.toggle('dark');
  };

  return (
    <header className="sticky top-0 z-30 flex h-16 items-center justify-between border-b border-neutral-200 bg-white/80 px-6 backdrop-blur-xl dark:border-neutral-800 dark:bg-neutral-950/80">
      {/* Search */}
      <div className="flex items-center gap-4">
        <AnimatePresence mode="wait">
          {showSearch ? (
            <motion.div
              initial={{ opacity: 0, width: 0 }}
              animate={{ opacity: 1, width: 320 }}
              exit={{ opacity: 0, width: 0 }}
              transition={{ duration: 0.2 }}
              className="overflow-hidden"
            >
              <Input
                type="search"
                placeholder="Search patients, sessions..."
                className="h-10 w-80 rounded-xl border-neutral-200 bg-neutral-50 dark:border-neutral-700 dark:bg-neutral-900"
                autoFocus
                onBlur={() => setShowSearch(false)}
              />
            </motion.div>
          ) : (
            <motion.button
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              onClick={() => setShowSearch(true)}
              className="flex items-center gap-2 rounded-xl bg-neutral-100 px-4 py-2.5 text-sm text-neutral-500 transition-colors hover:bg-neutral-200 dark:bg-neutral-800 dark:hover:bg-neutral-700"
            >
              <Search className="h-4 w-4" />
              <span>Search...</span>
              <kbd className="ml-2 rounded bg-white px-1.5 py-0.5 text-xs font-medium text-neutral-400 shadow-sm dark:bg-neutral-700 dark:text-neutral-500">
                ⌘K
              </kbd>
            </motion.button>
          )}
        </AnimatePresence>
      </div>

      {/* Actions */}
      <div className="flex items-center gap-2">
        {/* Notifications */}
        <Button
          variant="ghost"
          size="icon"
          className="relative h-10 w-10 rounded-xl"
        >
          <Bell className="h-5 w-5 text-neutral-600 dark:text-neutral-400" />
          <span className="absolute right-2 top-2 h-2 w-2 rounded-full bg-red-500" />
        </Button>

        {/* Theme Toggle */}
        <Button
          variant="ghost"
          size="icon"
          className="h-10 w-10 rounded-xl"
          onClick={toggleTheme}
        >
          <AnimatePresence mode="wait" initial={false}>
            {isDark ? (
              <motion.div
                key="sun"
                initial={{ rotate: -90, opacity: 0 }}
                animate={{ rotate: 0, opacity: 1 }}
                exit={{ rotate: 90, opacity: 0 }}
                transition={{ duration: 0.2 }}
              >
                <Sun className="h-5 w-5 text-yellow-500" />
              </motion.div>
            ) : (
              <motion.div
                key="moon"
                initial={{ rotate: 90, opacity: 0 }}
                animate={{ rotate: 0, opacity: 1 }}
                exit={{ rotate: -90, opacity: 0 }}
                transition={{ duration: 0.2 }}
              >
                <Moon className="h-5 w-5 text-neutral-600" />
              </motion.div>
            )}
          </AnimatePresence>
        </Button>
      </div>
    </header>
  );
}
