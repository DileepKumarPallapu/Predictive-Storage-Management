import React, { useState, useEffect, useCallback } from 'react';
import {
  Play,
  Pause,
  SkipBack,
  SkipForward,
  RotateCcw,
  Sliders,
  FileText,
  AlertCircle,
  Database,
  FastForward,
} from 'lucide-react';
import { api, ReplayStatus } from '../api/client';
import { useOperatingMode } from '../context/OperatingModeContext';

export const ReplayControlBar: React.FC = () => {
  const { operatingMode, setOperatingMode, triggerRefresh } = useOperatingMode();
  const [status, setStatus] = useState<ReplayStatus | null>(null);
  const [loading, setLoading] = useState<boolean>(false);

  const fetchStatus = useCallback(async () => {
    try {
      const res = await api.getReplayStatus();
      setStatus(res);
    } catch (e) {
      console.error('Failed to fetch replay status:', e);
    }
  }, []);

  useEffect(() => {
    if (operatingMode === 'replay') {
      fetchStatus();
    }
  }, [operatingMode, fetchStatus]);

  // Periodic poll while playing
  useEffect(() => {
    if (operatingMode !== 'replay' || !status?.is_playing) return;
    const interval = setInterval(() => {
      fetchStatus();
    }, 1000);
    return () => clearInterval(interval);
  }, [operatingMode, status?.is_playing, fetchStatus]);

  if (operatingMode !== 'replay') {
    return null;
  }

  const handleAction = async (action: string, val?: any) => {
    setLoading(true);
    try {
      const updated = await api.controlReplay(action, val);
      setStatus(updated);
      triggerRefresh();
    } catch (e) {
      console.error(`Replay control ${action} failed:`, e);
    } finally {
      setLoading(false);
    }
  };

  const handleTraceChange = async (filename: string) => {
    if (filename === '__unload__') {
      await handleAction('unload');
    } else {
      await handleAction('load', filename);
    }
  };

  const formatTimestamp = (iso?: string | null) => {
    if (!iso) return 'N/A';
    try {
      const d = new Date(iso);
      return d.toISOString().replace('T', ' ').substring(0, 19) + ' UTC';
    } catch {
      return iso;
    }
  };

  return (
    <section 
      aria-label="Storage Trace Replay Controls"
      className="bg-[var(--surface-elevated)] border-b border-[var(--border)] px-4 sm:px-6 py-2.5 shadow-xs transition-colors"
    >
      <div className="max-w-7xl mx-auto flex flex-col md:flex-row items-center justify-between gap-3 text-xs">
        {/* Left: Mode Badge & Trace Selector */}
        <div className="flex items-center gap-3 w-full md:w-auto justify-between md:justify-start">
          <div className="flex items-center gap-1.5 px-2 py-1 rounded bg-[var(--warning)]/10 text-[var(--warning)] border border-[var(--warning)]/30 font-mono text-[11px] font-semibold shrink-0">
            <span className="w-2 h-2 rounded-full bg-[var(--warning)] animate-pulse" />
            TRACE REPLAY
          </div>

          <div className="flex items-center gap-1.5">
            <FileText size={13} className="text-[var(--text-muted)]" />
            <select
              aria-label="Select Storage Trace Dataset"
              value={status?.active_trace_id || '__unload__'}
              onChange={(e) => handleTraceChange(e.target.value)}
              disabled={loading}
              className="bg-[var(--surface)] text-[var(--text-primary)] border border-[var(--border)] rounded px-2 py-1 text-xs font-medium focus:outline-none focus:border-[var(--accent)]"
            >
              <option value="__unload__">No Trace Selected (Empty State)</option>
              {status?.available_traces.map((t) => (
                <option key={t.id} value={t.filename}>
                  {t.filename} ({t.format})
                </option>
              ))}
            </select>
          </div>
        </div>

        {/* Center: Playback Transport & Timeline Scrub Slider */}
        {status?.has_trace ? (
          <div className="flex items-center gap-3 w-full md:w-auto flex-1 max-w-xl px-2">
            {/* Step Back */}
            <button
              onClick={() => handleAction('step', -1)}
              disabled={loading || status.current_frame_index <= 0}
              className="p-1.5 rounded hover:bg-[var(--surface)] text-[var(--text-secondary)] hover:text-[var(--text-primary)] disabled:opacity-40 transition-colors"
              title="Step Backward 1 Frame"
              aria-label="Step Backward"
            >
              <SkipBack size={14} />
            </button>

            {/* Play / Pause */}
            <button
              onClick={() => handleAction(status.is_playing ? 'pause' : 'play')}
              disabled={loading}
              className={`p-1.5 rounded text-white flex items-center justify-center transition-all ${
                status.is_playing
                  ? 'bg-[var(--warning)] hover:brightness-110 shadow-xs'
                  : 'bg-[var(--accent)] hover:bg-[var(--accent-hover)] shadow-xs'
              }`}
              title={status.is_playing ? 'Pause Replay' : 'Play Benchmark Trace'}
              aria-label={status.is_playing ? 'Pause' : 'Play'}
            >
              {status.is_playing ? <Pause size={14} /> : <Play size={14} className="ml-0.5" />}
            </button>

            {/* Step Forward */}
            <button
              onClick={() => handleAction('step', 1)}
              disabled={loading || status.current_frame_index >= status.total_frames - 1}
              className="p-1.5 rounded hover:bg-[var(--surface)] text-[var(--text-secondary)] hover:text-[var(--text-primary)] disabled:opacity-40 transition-colors"
              title="Step Forward 1 Frame"
              aria-label="Step Forward"
            >
              <SkipForward size={14} />
            </button>

            {/* Timeline Scrub Slider */}
            <div className="flex-1 flex flex-col justify-center gap-0.5">
              <input
                type="range"
                min={0}
                max={Math.max(1, status.total_frames - 1)}
                value={status.current_frame_index}
                onChange={(e) => handleAction('seek', parseInt(e.target.value, 10))}
                className="w-full h-1.5 bg-[var(--surface)] rounded-lg appearance-none cursor-pointer accent-[var(--accent)]"
                title={`Seek frame ${status.current_frame_index} / ${status.total_frames - 1}`}
                aria-label="Timeline scrubber"
              />
              <div className="flex justify-between items-center text-[10px] font-mono text-[var(--text-muted)]">
                <span>Frame {status.current_frame_index} / {status.total_frames - 1}</span>
                <span className="font-semibold text-[var(--text-secondary)]">
                  {formatTimestamp(status.current_timestamp)}
                </span>
                <span>{status.progress_pct}%</span>
              </div>
            </div>
          </div>
        ) : (
          <div className="flex items-center gap-2 text-xs text-[var(--warning)] py-1">
            <AlertCircle size={14} />
            <span>Trace replay paused: No trace dataset loaded. Select a trace above to begin playback.</span>
          </div>
        )}

        {/* Right: Speed Multiplier */}
        {status?.has_trace && (
          <div className="flex items-center gap-1 shrink-0">
            <FastForward size={12} className="text-[var(--text-muted)] hidden lg:inline" />
            <span className="text-[11px] text-[var(--text-muted)] mr-1 hidden lg:inline">Speed:</span>
            {[1, 2, 5, 10].map((spd) => (
              <button
                key={spd}
                onClick={() => handleAction('speed', spd)}
                disabled={loading}
                className={`px-2 py-0.5 rounded text-[11px] font-mono transition-all ${
                  status.playback_speed === spd
                    ? 'bg-[var(--accent)] text-white font-semibold'
                    : 'bg-[var(--surface)] text-[var(--text-secondary)] hover:text-[var(--text-primary)] border border-[var(--border)]'
                }`}
              >
                {spd}x
              </button>
            ))}
          </div>
        )}
      </div>
    </section>
  );
};
