'use client';

import { useState, useEffect, useCallback, useRef } from 'react';
import Vapi from '@vapi-ai/web';

interface VapiMessage {
  type: string;
  role?: 'assistant' | 'user';
  transcript?: string;
  transcriptType?: 'partial' | 'final';
}

interface UseVapiOptions {
  onTranscript?: (role: 'assistant' | 'user', text: string, isFinal: boolean) => void;
  onCallStart?: () => void;
  onCallEnd?: () => void;
  onError?: (error: Error) => void;
  onSpeechStart?: () => void;
  onSpeechEnd?: () => void;
}

export function useVapi(options: UseVapiOptions = {}) {
  const [isConnected, setIsConnected] = useState(false);
  const [isCallActive, setIsCallActive] = useState(false);
  const [isSpeaking, setIsSpeaking] = useState(false);
  const [volumeLevel, setVolumeLevel] = useState(0);
  const [error, setError] = useState<string | null>(null);
  const vapiRef = useRef<Vapi | null>(null);

  useEffect(() => {
    const apiKey = process.env.NEXT_PUBLIC_VAPI_API_KEY;
    if (!apiKey) {
      console.error('VAPI API key not configured. Add NEXT_PUBLIC_VAPI_API_KEY to .env.local');
      setError('VAPI API key not configured');
      return;
    }

    console.log('Initializing VAPI with key:', apiKey.substring(0, 8) + '...');

    const vapi = new Vapi(apiKey);
    vapiRef.current = vapi;

    vapi.on('call-start', () => {
      console.log('VAPI: Call started');
      setIsCallActive(true);
      setIsConnected(true);
      setError(null);
      // Note: call ID is available from the start() return value, not this event
      options.onCallStart?.();
    });

    vapi.on('call-end', () => {
      console.log('VAPI: Call ended');
      setIsCallActive(false);
      setIsConnected(false);
      setIsSpeaking(false);
      options.onCallEnd?.();
    });

    vapi.on('speech-start', () => {
      setIsSpeaking(true);
      options.onSpeechStart?.();
    });

    vapi.on('speech-end', () => {
      setIsSpeaking(false);
      options.onSpeechEnd?.();
    });

    vapi.on('volume-level', (level: number) => {
      setVolumeLevel(level);
    });

    vapi.on('message', (message: VapiMessage) => {
      console.log('VAPI message:', message);
      if (message.type === 'transcript' && message.role && message.transcript) {
        options.onTranscript?.(
          message.role,
          message.transcript,
          message.transcriptType === 'final'
        );
      }
    });

    vapi.on('error', (err: unknown) => {
      // Handle different error types from VAPI
      let errorMessage = 'Unknown VAPI error';
      if (err instanceof Error) {
        errorMessage = err.message;
      } else if (typeof err === 'object' && err !== null) {
        errorMessage = JSON.stringify(err);
        if (errorMessage === '{}') {
          errorMessage = 'VAPI connection failed. Check: 1) API key is PUBLIC key (not private), 2) Assistant ID exists, 3) Microphone permissions';
        }
      }
      console.error('VAPI Error:', errorMessage, err);
      setError(errorMessage);
      options.onError?.(new Error(errorMessage));
    });

    return () => {
      vapi.stop();
    };
  }, []);

  interface StartCallOptions {
    assistantId?: string;
    variables?: Record<string, string | number | boolean>;
  }

  // Store the current call ID
  const [callId, setCallId] = useState<string | null>(null);

  const startCall = useCallback(async (options?: StartCallOptions | string): Promise<string | null> => {
    if (!vapiRef.current) {
      throw new Error('VAPI not initialized');
    }

    // Handle both old string API and new options API
    const assistantId = typeof options === 'string'
      ? options
      : options?.assistantId || process.env.NEXT_PUBLIC_VAPI_ASSISTANT_ID;

    const variables = typeof options === 'object' ? options.variables : undefined;

    if (!assistantId) {
      throw new Error('Assistant ID not configured. Add NEXT_PUBLIC_VAPI_ASSISTANT_ID to .env.local');
    }

    console.log('Starting VAPI call with assistant:', assistantId);
    if (variables) {
      console.log('With variables:', variables);
    }

    try {
      // Request microphone permission first
      await navigator.mediaDevices.getUserMedia({ audio: true });
      console.log('Microphone permission granted');

      // If we have variables, pass them as assistant overrides
      // VAPI expects variableValues in the assistantOverrides object
      let call;
      if (variables) {
        call = await vapiRef.current.start(assistantId, {
          variableValues: variables,
        } as never);
      } else {
        call = await vapiRef.current.start(assistantId);
      }

      // Extract call ID from the response
      const vapiCallId = (call as { id?: string })?.id || null;
      if (vapiCallId) {
        console.log('VAPI call started with ID:', vapiCallId);
        setCallId(vapiCallId);
      }

      return vapiCallId;
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Failed to start call';
      console.error('Failed to start call:', errorMessage, err);
      setError(errorMessage);
      throw err;
    }
  }, []);

  const endCall = useCallback(() => {
    if (!vapiRef.current) return;
    vapiRef.current.stop();
  }, []);

  const toggleMute = useCallback(() => {
    if (!vapiRef.current) return;
    const isMuted = vapiRef.current.isMuted();
    vapiRef.current.setMuted(!isMuted);
    return !isMuted;
  }, []);

  return {
    isConnected,
    isCallActive,
    isSpeaking,
    volumeLevel,
    error,
    callId,
    startCall,
    endCall,
    toggleMute,
  };
}
