'use client';

import { motion } from 'framer-motion';
import { useEffect, useState, useMemo } from 'react';

interface VoiceVisualizerProps {
  isActive: boolean;
  isSpeaking: boolean;
  volumeLevel: number;
}

export function VoiceVisualizer({ isActive, isSpeaking, volumeLevel }: VoiceVisualizerProps) {
  const [bars, setBars] = useState<number[]>(Array(24).fill(0.15));

  // Create a smooth wave pattern for idle state
  const idlePattern = useMemo(() => {
    return Array(24).fill(0).map((_, i) => {
      const center = 12;
      const distance = Math.abs(i - center);
      return 0.15 + (1 - distance / center) * 0.1;
    });
  }, []);

  useEffect(() => {
    if (!isActive) {
      setBars(idlePattern);
      return;
    }

    const interval = setInterval(() => {
      if (isSpeaking) {
        // Create smooth, organic wave when speaking
        const time = Date.now() / 100;
        setBars(
          Array(24)
            .fill(0)
            .map((_, i) => {
              const wave1 = Math.sin(time + i * 0.3) * 0.3;
              const wave2 = Math.sin(time * 1.5 + i * 0.2) * 0.2;
              const randomness = Math.random() * 0.15 * volumeLevel;
              const base = 0.3 + volumeLevel * 0.4;
              return Math.min(0.95, Math.max(0.15, base + wave1 + wave2 + randomness));
            })
        );
      } else {
        // Gentle breathing animation when listening
        const time = Date.now() / 500;
        setBars(
          Array(24)
            .fill(0)
            .map((_, i) => {
              const center = 12;
              const distance = Math.abs(i - center);
              const wave = Math.sin(time + i * 0.15) * 0.08;
              const base = 0.2 + (1 - distance / center) * 0.15;
              return base + wave;
            })
        );
      }
    }, 50);

    return () => clearInterval(interval);
  }, [isActive, isSpeaking, volumeLevel, idlePattern]);

  return (
    <div className="relative flex h-24 items-center justify-center overflow-hidden rounded-2xl">
      {/* Subtle glow effect behind bars */}
      {isActive && (
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: isSpeaking ? 0.4 : 0.2 }}
          className="absolute inset-0 bg-gradient-to-r from-transparent via-blue-500/10 to-transparent blur-xl"
        />
      )}

      {/* Visualization bars */}
      <div className="relative flex h-full items-center justify-center gap-[3px]">
        {bars.map((height, index) => (
          <motion.div
            key={index}
            className="relative"
            style={{ height: '100%' }}
          >
            <motion.div
              className={`w-[3px] rounded-full ${
                isActive
                  ? isSpeaking
                    ? 'bg-gradient-to-t from-blue-500 via-blue-400 to-cyan-400'
                    : 'bg-gradient-to-t from-blue-400/80 to-blue-300/80'
                  : 'bg-neutral-300 dark:bg-neutral-600'
              }`}
              animate={{
                height: `${height * 100}%`,
                opacity: isActive ? 0.7 + height * 0.3 : 0.4,
              }}
              transition={{
                duration: 0.15,
                ease: [0.4, 0, 0.2, 1], // Apple's ease curve
              }}
              style={{
                position: 'absolute',
                bottom: '50%',
                transform: 'translateY(50%)',
                minHeight: '4px',
                maxHeight: '88px',
              }}
            />
          </motion.div>
        ))}
      </div>
    </div>
  );
}
