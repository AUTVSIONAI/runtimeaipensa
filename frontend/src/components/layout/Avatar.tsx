'use client';

import { cn } from '@/lib/utils';
import { motion } from 'framer-motion';
import { Bot } from 'lucide-react';

type AvatarState = 'idle' | 'listening' | 'thinking' | 'speaking' | 'error';

interface AvatarProps {
  state?: AvatarState;
  size?: 'sm' | 'md' | 'lg' | 'xl';
  className?: string;
}

const sizeClasses = {
  sm: 'w-12 h-12',
  md: 'w-20 h-20',
  lg: 'w-32 h-32',
  xl: 'w-48 h-48',
};

export function Avatar({ state = 'idle', size = 'md', className }: AvatarProps) {
  const pulseClasses = {
    idle: 'animate-pulse-slow',
    listening: 'animate-pulse-ring-blue',
    thinking: 'animate-pulse-ring-yellow animate-rotate-slow',
    speaking: 'animate-wave-form',
    error: 'animate-pulse-ring-red',
  };

  return (
    <motion.div
      className={cn('relative flex items-center justify-center', sizeClasses[size], className)}
      animate={{ scale: state === 'speaking' ? [1, 1.05, 1] : 1 }}
      transition={{ duration: 0.8, repeat: Infinity, ease: 'easeInOut' }}
    >
      {/* Outer rings for active states */}
      {['listening', 'thinking', 'speaking', 'error'].includes(state) && (
        <motion.div
          className={cn(
            'absolute inset-0 rounded-full border-2',
            state === 'listening' && 'border-blue-500',
            state === 'thinking' && 'border-yellow-500',
            state === 'speaking' && 'border-green-500',
            state === 'error' && 'border-red-500',
            pulseClasses[state]
          )}
          animate={{ scale: [1, 1.3], opacity: [0.6, 0] }}
          transition={{ duration: 1.5, repeat: Infinity, ease: 'easeOut' }}
        />
      )}

      {/* Core avatar */}
      <div className={cn(
        'relative rounded-full overflow-hidden flex items-center justify-center',
        'bg-gradient-to-br from-blue-500 to-purple-600',
        'shadow-lg shadow-blue-500/25'
      )}>
        <Bot className="text-white" size={size === 'sm' ? 20 : size === 'md' ? 32 : size === 'lg' ? 48 : 64} />
      </div>

      {/* Speaking wave form visualization */}
      {state === 'speaking' && (
        <div className="absolute bottom-0 left-1/2 -translate-x-1/2 translate-y-1/2 flex gap-1">
          {[1, 2, 3, 4, 5].map((i) => (
            <motion.div
              key={i}
              className="w-1 h-2 bg-green-400 rounded"
              animate={{ height: [4, 16, 4] }}
              transition={{ duration: 0.6, repeat: Infinity, delay: i * 0.1, ease: 'easeInOut' }}
            />
          ))}
        </div>
      )}
    </motion.div>
  );
}