import React, { useState } from 'react';
import { Info, Sparkles, SlidersHorizontal, AlertTriangle, TrendingUp, CheckCircle2 } from 'lucide-react';
import { usePresentationMode } from '../context/PresentationModeContext';

interface ChartProps {
  title: string;
  historicalTimestamps: string[];
  historicalValues: number[];
  forecastTimestamps?: string[];
  q10?: number[];
  q50?: number[];
  q90?: number[];
  counterfactualQ50?: number[];
  hardConstraint?: number | null;
  units: string;
  isBytes?: boolean;
}

export const ScientificForecastChart: React.FC<ChartProps> = ({
  title,
  historicalTimestamps,
  historicalValues,
  forecastTimestamps = [],
  q10 = [],
  q50 = [],
  q90 = [],
  counterfactualQ50 = [],
  hardConstraint = null,
  units,
  isBytes = true,
}) => {
  const [hoveredIdx, setHoveredIdx] = useState<{ type: 'hist' | 'fc'; index: number } | null>(null);
  const [showAdvancedStats, setShowAdvancedStats] = useState(false);
  const { isGuided } = usePresentationMode();

  // Downsample historical points if too dense (e.g. max 80 historical points for crisp SVG rendering)
  const step = Math.max(1, Math.floor(historicalValues.length / 80));
  const sampledHistTimes = historicalTimestamps.filter((_, i) => i % step === 0);
  const sampledHistVals = historicalValues.filter((_, i) => i % step === 0);

  // Compute scale boundaries
  const allVals = [
    ...sampledHistVals,
    ...q10,
    ...q50,
    ...q90,
    ...counterfactualQ50,
    ...(hardConstraint ? [hardConstraint] : []),
  ].filter((v) => !isNaN(v) && v !== null);

  if (allVals.length === 0) {
    return (
      <div className="h-64 flex items-center justify-center text-[var(--text-muted)] glass-panel rounded-xl border border-[var(--border-subtle)] text-sm">
        No telemetry records available for rendering.
      </div>
    );
  }

  const minVal = Math.min(...allVals) * 0.95;
  const maxVal = Math.max(...allVals) * 1.05;
  const range = maxVal - minVal || 1;

  const totalPoints = sampledHistVals.length + forecastTimestamps.length;
  const width = 800;
  const height = 300;
  const padLeft = 70;
  const padRight = 30;
  const padTop = 20;
  const padBottom = 35;
  const plotWidth = width - padLeft - padRight;
  const plotHeight = height - padTop - padBottom;

  const getX = (index: number) => padLeft + (index / (totalPoints - 1 || 1)) * plotWidth;
  const getY = (val: number) => padTop + plotHeight - ((val - minVal) / range) * plotHeight;

  // Format value
  const formatVal = (v: number) => {
    if (isBytes) {
      const tb = v / (1024 ** 4);
      if (tb >= 1) return `${tb.toFixed(2)} TB`;
      const gb = v / (1024 ** 3);
      return `${gb.toFixed(1)} GB`;
    }
    return `${v.toLocaleString(undefined, { maximumFractionDigits: 1 })} ${units}`;
  };

  // Dynamically generated real summary narrative
  const firstHist = sampledHistVals[0] || 0;
  const lastHist = sampledHistVals[sampledHistVals.length - 1] || 0;
  const histDelta = lastHist - firstHist;
  const histPctChange = firstHist > 0 ? ((histDelta / firstHist) * 100).toFixed(1) : '0';

  const lastFc = q50.length > 0 ? q50[q50.length - 1] : null;
  const fcDelta = lastFc !== null ? lastFc - lastHist : 0;
  const fcPctChange = lastHist > 0 ? ((fcDelta / lastHist) * 100).toFixed(1) : '0';

  let narrativeText = '';
  if (sampledHistVals.length > 1) {
    narrativeText = `Observed telemetry has ${
      histDelta >= 0 ? `increased by +${histPctChange}%` : `decreased by ${histPctChange}%`
    } over the recorded timeframe. `;
  }
  if (q50.length > 0) {
    narrativeText += `The calibrated model projects a ${
      fcDelta >= 0 ? `further growth of +${fcPctChange}%` : `downward adjustment of ${fcPctChange}%`
    } across the next ${forecastTimestamps.length} hours, bounded by the 80% expected uncertainty envelope.`;
  }

  // Historical path
  const histPath = sampledHistVals
    .map((v, i) => `${i === 0 ? 'M' : 'L'} ${getX(i)} ${getY(v)}`)
    .join(' ');

  // Forecast split X coordinate
  const splitX = getX(sampledHistVals.length - 1);

  // Forecast median path
  const fcOffset = sampledHistVals.length - 1;
  const fcMedianPath = q50.length > 0
    ? `M ${splitX} ${getY(sampledHistVals[sampledHistVals.length - 1])} ` +
      q50.map((v, i) => `L ${getX(fcOffset + 1 + i)} ${getY(v)}`).join(' ')
    : '';

  // Uncertainty polygon [q10, q90]
  let bandPolygon = '';
  if (q10.length > 0 && q90.length > 0) {
    const topPoints = q90.map((v, i) => `${getX(fcOffset + 1 + i)},${getY(v)}`);
    const bottomPoints = q10.map((v, i) => `${getX(fcOffset + 1 + i)},${getY(v)}`).reverse();
    const startPoint = `${splitX},${getY(sampledHistVals[sampledHistVals.length - 1])}`;
    bandPolygon = `${startPoint} ${topPoints.join(' ')} ${bottomPoints.join(' ')}`;
  }

  // Counterfactual overlay path
  const cfPath = counterfactualQ50.length > 0
    ? `M ${splitX} ${getY(sampledHistVals[sampledHistVals.length - 1])} ` +
      counterfactualQ50.map((v, i) => `L ${getX(fcOffset + 1 + i)} ${getY(v)}`).join(' ')
    : '';

  return (
    <div className="glass-panel rounded-2xl p-5 flex flex-col gap-3.5">
      {/* Header and Legend */}
      <div className="flex items-center justify-between flex-wrap gap-2.5">
        <div>
          <h4 className="text-sm font-semibold tracking-wide text-[var(--text-primary)] flex items-center gap-2">
            <span className="w-2 h-2 rounded-full bg-[var(--accent-cyan)] shadow-[0_0_8px_var(--accent-cyan)] animate-pulse" />
            {title}
          </h4>
          <p className="text-[11px] text-[var(--text-muted)] mt-0.5">
            {isGuided
              ? 'Past observations (cyan) followed by expected future range (shaded interval).'
              : 'Empirical time-series telemetry with conformal quantile intervals [q10, q90].'}
          </p>
        </div>

        <div className="flex items-center gap-4 text-xs flex-wrap">
          <span className="flex items-center gap-1.5 text-[var(--text-secondary)]">
            <span className="w-3 h-0.5 bg-[var(--accent-cyan)] inline-block rounded-full"></span>
            {isGuided ? 'Past Data' : 'Observed History'}
          </span>
          {q50.length > 0 && (
            <span className="flex items-center gap-1.5 text-[var(--accent-violet)]">
              <span className="w-3 h-0.5 bg-[var(--accent-violet)] inline-block rounded-full"></span>
              {isGuided ? 'Expected Trend' : 'Forecast Median (q50)'}
            </span>
          )}
          {q10.length > 0 && (
            <span className="flex items-center gap-1.5 text-[var(--text-secondary)]">
              <span className="w-3.5 h-2 bg-[var(--accent-cyan)] opacity-25 inline-block rounded-sm"></span>
              {isGuided ? 'Expected Range (80%)' : '80% CI [q10, q90]'}
            </span>
          )}
          {counterfactualQ50.length > 0 && (
            <span className="flex items-center gap-1.5 text-[var(--color-success)] font-medium">
              <span className="w-3 h-0.5 border-t border-dashed border-[var(--color-success)] inline-block"></span>
              {isGuided ? 'Virtual Action Test' : 'Counterfactual Simulation'}
            </span>
          )}
          {hardConstraint !== null && (
            <span className="flex items-center gap-1.5 text-[var(--color-critical)] font-medium">
              <span className="w-3 h-0.5 border-t border-dashed border-[var(--color-critical)] inline-block"></span>
              {isGuided ? 'Hard Limit' : 'Hard SLA Constraint'}
            </span>
          )}

          <button
            type="button"
            onClick={() => setShowAdvancedStats(!showAdvancedStats)}
            className="p-1 text-[var(--text-muted)] hover:text-[var(--text-primary)] transition-colors rounded"
            title="Toggle advanced statistical metrics"
          >
            <SlidersHorizontal size={13} />
          </button>
        </div>
      </div>

      {/* Dynamic Layperson Narrative Summary */}
      <div className="bg-[var(--surface-raised)]/60 rounded-xl px-3.5 py-2 border border-[var(--border-subtle)] text-[11px] text-[var(--text-secondary)] flex items-start gap-2">
        <Sparkles size={14} className="text-[var(--accent-cyan)] shrink-0 mt-0.5" />
        <span className="leading-relaxed">{narrativeText}</span>
      </div>

      {/* Advanced Statistical Breakdown (Revealed when requested) */}
      {showAdvancedStats && (
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-2.5 bg-[var(--surface-primary)] p-3 rounded-xl border border-[var(--border-visible)] text-xs font-mono animate-in fade-in duration-100">
          <div>
            <span className="text-[10px] text-[var(--text-muted)] block">Initial Observation:</span>
            <span className="font-bold text-[var(--text-primary)]">{formatVal(firstHist)}</span>
          </div>
          <div>
            <span className="text-[10px] text-[var(--text-muted)] block">Current Level:</span>
            <span className="font-bold text-[var(--accent-cyan)]">{formatVal(lastHist)}</span>
          </div>
          <div>
            <span className="text-[10px] text-[var(--text-muted)] block">End Projected (q50):</span>
            <span className="font-bold text-[var(--accent-violet)]">
              {lastFc !== null ? formatVal(lastFc) : 'N/A'}
            </span>
          </div>
          <div>
            <span className="text-[10px] text-[var(--text-muted)] block">SLA Headroom Margin:</span>
            <span className="font-bold text-[var(--color-success)]">
              {hardConstraint ? formatVal(Math.max(0, hardConstraint - lastHist)) : 'Unconstrained'}
            </span>
          </div>
        </div>
      )}

      {/* SVG Canvas */}
      <div className="relative w-full overflow-hidden">
        <svg
          viewBox={`0 0 ${width} ${height}`}
          className="w-full h-auto select-none"
          style={{ maxHeight: '340px' }}
        >
          {/* Subtle gradient definitions */}
          <defs>
            <linearGradient id="uncertaintyGradient" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor="var(--accent-cyan)" stopOpacity="0.25" />
              <stop offset="100%" stopColor="var(--accent-cyan)" stopOpacity="0.04" />
            </linearGradient>
            <linearGradient id="historyGradient" x1="0" y1="0" x2="1" y2="0">
              <stop offset="0%" stopColor="var(--accent-sapphire)" />
              <stop offset="100%" stopColor="var(--accent-cyan)" />
            </linearGradient>
          </defs>

          {/* Grid lines */}
          {[0, 0.25, 0.5, 0.75, 1].map((pct) => {
            const y = padTop + plotHeight * pct;
            const val = maxVal - pct * range;
            return (
              <g key={pct}>
                <line
                  x1={padLeft}
                  y1={y}
                  x2={width - padRight}
                  y2={y}
                  stroke="var(--border-subtle)"
                  strokeDasharray="3 3"
                  strokeOpacity="0.5"
                />
                <text
                  x={padLeft - 10}
                  y={y + 4}
                  textAnchor="end"
                  fill="var(--text-muted)"
                  className="text-[10px] font-mono tabular-nums"
                >
                  {formatVal(val)}
                </text>
              </g>
            );
          })}

          {/* Hard Constraint Line */}
          {hardConstraint !== null && (
            <g>
              <line
                x1={padLeft}
                y1={getY(hardConstraint)}
                x2={width - padRight}
                y2={getY(hardConstraint)}
                stroke="var(--color-critical)"
                strokeWidth="1.5"
                strokeDasharray="5 3"
              />
              <text
                x={width - padRight - 5}
                y={getY(hardConstraint) - 5}
                textAnchor="end"
                fill="var(--color-critical)"
                className="text-[10px] font-mono font-semibold"
              >
                Hard SLA Limit: {formatVal(hardConstraint)}
              </text>
            </g>
          )}

          {/* Forecast Cutoff Vertical Line */}
          {q50.length > 0 && (
            <g>
              <line
                x1={splitX}
                y1={padTop}
                x2={splitX}
                y2={padTop + plotHeight}
                stroke="var(--accent-cyan)"
                strokeOpacity="0.6"
                strokeDasharray="2 2"
              />
              <text
                x={splitX - 6}
                y={padTop + 14}
                textAnchor="end"
                fill="var(--accent-cyan)"
                className="text-[10px] font-mono font-semibold"
              >
                Now (Cutoff)
              </text>
            </g>
          )}

          {/* Uncertainty Band Polygon */}
          {bandPolygon && (
            <polygon
              points={bandPolygon}
              fill="url(#uncertaintyGradient)"
            />
          )}

          {/* Observed Historical Line */}
          <path
            d={histPath}
            fill="none"
            stroke="url(#historyGradient)"
            strokeWidth="2.2"
          />

          {/* Forecast Median Line */}
          {fcMedianPath && (
            <path
              d={fcMedianPath}
              fill="none"
              stroke="var(--accent-violet)"
              strokeWidth="2.4"
            />
          )}

          {/* Counterfactual Simulation Line */}
          {cfPath && (
            <path
              d={cfPath}
              fill="none"
              stroke="var(--color-success)"
              strokeWidth="2.2"
              strokeDasharray="6 3"
            />
          )}

          {/* Hover interaction points */}
          {sampledHistVals.map((v, i) => (
            <circle
              key={`h-${i}`}
              cx={getX(i)}
              cy={getY(v)}
              r="4.5"
              className="opacity-0 hover:opacity-100 fill-[var(--accent-cyan)] cursor-pointer transition-opacity"
              onMouseEnter={() => setHoveredIdx({ type: 'hist', index: i })}
              onMouseLeave={() => setHoveredIdx(null)}
            />
          ))}

          {q50.map((v, i) => (
            <circle
              key={`f-${i}`}
              cx={getX(fcOffset + 1 + i)}
              cy={getY(v)}
              r="4.5"
              className="opacity-0 hover:opacity-100 fill-[var(--accent-violet)] cursor-pointer transition-opacity"
              onMouseEnter={() => setHoveredIdx({ type: 'fc', index: i })}
              onMouseLeave={() => setHoveredIdx(null)}
            />
          ))}
        </svg>

        {/* Floating Tooltip Info */}
        {hoveredIdx && (
          <div className="absolute top-2 right-4 glass-panel-elevated rounded-xl px-3.5 py-2.5 shadow-glass text-xs font-mono">
            {hoveredIdx.type === 'hist' ? (
              <div>
                <span className="text-[var(--text-secondary)]">Observed Value: </span>
                <span className="text-[var(--accent-cyan)] font-bold">
                  {formatVal(sampledHistVals[hoveredIdx.index])}
                </span>
                <div className="text-[10px] text-[var(--text-muted)]">
                  {new Date(sampledHistTimes[hoveredIdx.index]).toLocaleString()}
                </div>
              </div>
            ) : (
              <div>
                <span className="text-[var(--text-secondary)]">Forecast Median: </span>
                <span className="text-[var(--accent-violet)] font-bold">
                  {formatVal(q50[hoveredIdx.index])}
                </span>
                {q10[hoveredIdx.index] && (
                  <div className="text-[10px] text-[var(--text-muted)]">
                    80% Expected Range: [{formatVal(q10[hoveredIdx.index])} — {formatVal(q90[hoveredIdx.index])}]
                  </div>
                )}
                <div className="text-[10px] text-[var(--text-muted)]">
                  +{hoveredIdx.index + 1}h ({new Date(forecastTimestamps[hoveredIdx.index]).toLocaleDateString()})
                </div>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
};
