import React, { useState } from 'react';
import { Sparkles, SlidersHorizontal, CheckCircle2 } from 'lucide-react';
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

  // Downsample historical points if too dense (max 80 points for crisp SVG render)
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
      <div className="h-64 flex items-center justify-center text-[var(--text-muted)] titan-card text-xs">
        No telemetry records available for rendering.
      </div>
    );
  }

  const minVal = Math.min(...allVals) * 0.95;
  const maxVal = Math.max(...allVals) * 1.05;
  const range = maxVal - minVal || 1;

  const totalPoints = sampledHistVals.length + forecastTimestamps.length;
  const width = 800;
  const height = 280;
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

  // Narrative summary calculation
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
    } over the window. `;
  }
  if (q50.length > 0) {
    narrativeText += `The calibrated model projects a ${
      fcDelta >= 0 ? `further change of +${fcPctChange}%` : `downward adjustment of ${fcPctChange}%`
    } across the next ${forecastTimestamps.length} hours (bounded by 80% conformal envelope).`;
  }

  // Paths
  const histPath = sampledHistVals
    .map((v, i) => `${i === 0 ? 'M' : 'L'} ${getX(i)} ${getY(v)}`)
    .join(' ');

  const splitX = getX(sampledHistVals.length - 1);
  const fcOffset = sampledHistVals.length - 1;

  const fcMedianPath = q50.length > 0
    ? `M ${splitX} ${getY(sampledHistVals[sampledHistVals.length - 1])} ` +
      q50.map((v, i) => `L ${getX(fcOffset + 1 + i)} ${getY(v)}`).join(' ')
    : '';

  let bandPolygon = '';
  if (q10.length > 0 && q90.length > 0) {
    const topPoints = q90.map((v, i) => `${getX(fcOffset + 1 + i)},${getY(v)}`);
    const bottomPoints = q10.map((v, i) => `${getX(fcOffset + 1 + i)},${getY(v)}`).reverse();
    const startPoint = `${splitX},${getY(sampledHistVals[sampledHistVals.length - 1])}`;
    bandPolygon = `${startPoint} ${topPoints.join(' ')} ${bottomPoints.join(' ')}`;
  }

  const cfPath = counterfactualQ50.length > 0
    ? `M ${splitX} ${getY(sampledHistVals[sampledHistVals.length - 1])} ` +
      counterfactualQ50.map((v, i) => `L ${getX(fcOffset + 1 + i)} ${getY(v)}`).join(' ')
    : '';

  return (
    <div className="titan-card p-4 flex flex-col gap-3">
      {/* Header and Legend */}
      <div className="flex items-center justify-between flex-wrap gap-2">
        <div className="flex items-center gap-2">
          <span className="w-2 h-2 rounded-full bg-[var(--accent)]" />
          <div>
            <h4 className="text-xs font-bold text-[var(--text-primary)] tracking-tight">
              {title}
            </h4>
            <p className="text-[11px] text-[var(--text-muted)] mt-0.5">
              {isGuided
                ? 'Historical observations followed by expected future projection.'
                : 'Empirical time-series telemetry with conformal quantile intervals [q10, q90].'}
            </p>
          </div>
        </div>

        {/* Legend */}
        <div className="flex items-center gap-3.5 text-[11px] flex-wrap">
          <span className="flex items-center gap-1.5 text-[var(--text-secondary)]">
            <span className="w-2.5 h-0.5 bg-[var(--text-secondary)] inline-block"></span>
            {isGuided ? 'Past Data' : 'Observed History'}
          </span>
          {q50.length > 0 && (
            <span className="flex items-center gap-1.5 text-[var(--accent)] font-medium">
              <span className="w-2.5 h-0.5 bg-[var(--accent)] inline-block"></span>
              {isGuided ? 'Expected Trend' : 'Forecast Median (q50)'}
            </span>
          )}
          {q10.length > 0 && (
            <span className="flex items-center gap-1.5 text-[var(--text-secondary)]">
              <span className="w-3 h-2 bg-[var(--accent)]/20 inline-block border border-[var(--accent)]/40 rounded-sm"></span>
              {isGuided ? 'Expected Range (80%)' : '80% CI [q10, q90]'}
            </span>
          )}
          {counterfactualQ50.length > 0 && (
            <span className="flex items-center gap-1.5 text-[var(--accent-secondary)] font-medium">
              <span className="w-2.5 h-0.5 border-t border-dashed border-[var(--accent-secondary)] inline-block"></span>
              {isGuided ? 'Virtual Action' : 'Counterfactual'}
            </span>
          )}
          {hardConstraint !== null && (
            <span className="flex items-center gap-1.5 text-[var(--critical)] font-medium">
              <span className="w-2.5 h-0.5 border-t border-dashed border-[var(--critical)] inline-block"></span>
              {isGuided ? 'Hard Limit' : 'Hard SLA Constraint'}
            </span>
          )}

          <button
            type="button"
            onClick={() => setShowAdvancedStats(!showAdvancedStats)}
            className="p-1 text-[var(--text-muted)] hover:text-[var(--text-primary)] transition-colors rounded hover:bg-[var(--surface-subtle)]"
            title="Toggle Quantile Metrics"
            aria-label="Toggle Quantile Metrics"
          >
            <SlidersHorizontal size={12} />
          </button>
        </div>
      </div>

      {/* Narrative Summary Bar */}
      <div className="bg-[var(--surface-elevated)] rounded-md px-3 py-1.5 border border-[var(--border)] text-[11px] text-[var(--text-secondary)] flex items-start gap-2">
        <Sparkles size={13} className="text-[var(--accent)] shrink-0 mt-0.5" />
        <span className="leading-relaxed">{narrativeText}</span>
      </div>

      {/* Advanced Statistical Breakdown */}
      {showAdvancedStats && (
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 bg-[var(--surface-elevated)] p-2.5 rounded-md border border-[var(--border)] text-xs font-mono">
          <div>
            <span className="text-[10px] text-[var(--text-muted)] block">Initial Observation:</span>
            <span className="font-bold text-[var(--text-primary)]">{formatVal(firstHist)}</span>
          </div>
          <div>
            <span className="text-[10px] text-[var(--text-muted)] block">Current Level:</span>
            <span className="font-bold text-[var(--text-primary)]">{formatVal(lastHist)}</span>
          </div>
          <div>
            <span className="text-[10px] text-[var(--text-muted)] block">End Projected (q50):</span>
            <span className="font-bold text-[var(--accent)]">
              {lastFc !== null ? formatVal(lastFc) : 'N/A'}
            </span>
          </div>
          <div>
            <span className="text-[10px] text-[var(--text-muted)] block">SLA Headroom Margin:</span>
            <span className="font-bold text-[var(--success)]">
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
          style={{ maxHeight: '300px' }}
        >
          <defs>
            <linearGradient id="titaniumUncertaintyGradient" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor="var(--accent)" stopOpacity="0.16" />
              <stop offset="100%" stopColor="var(--accent)" stopOpacity="0.02" />
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
                  stroke="var(--border)"
                  strokeDasharray="2 3"
                  strokeOpacity="0.7"
                />
                <text
                  x={padLeft - 8}
                  y={y + 3}
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
                stroke="var(--critical)"
                strokeWidth="1.2"
                strokeDasharray="4 3"
              />
              <text
                x={width - padRight - 5}
                y={getY(hardConstraint) - 4}
                textAnchor="end"
                fill="var(--critical)"
                className="text-[10px] font-mono font-bold"
              >
                Hard Limit: {formatVal(hardConstraint)}
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
                stroke="var(--accent)"
                strokeOpacity="0.6"
                strokeDasharray="2 2"
              />
              <text
                x={splitX - 6}
                y={padTop + 12}
                textAnchor="end"
                fill="var(--accent)"
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
              fill="url(#titaniumUncertaintyGradient)"
            />
          )}

          {/* Observed Historical Line */}
          <path
            d={histPath}
            fill="none"
            stroke="var(--text-secondary)"
            strokeWidth="1.8"
          />

          {/* Forecast Median Line */}
          {fcMedianPath && (
            <path
              d={fcMedianPath}
              fill="none"
              stroke="var(--accent)"
              strokeWidth="2.2"
            />
          )}

          {/* Counterfactual Simulation Line */}
          {cfPath && (
            <path
              d={cfPath}
              fill="none"
              stroke="var(--accent-secondary)"
              strokeWidth="1.8"
              strokeDasharray="5 3"
            />
          )}

          {/* Interactive Hover Points */}
          {sampledHistVals.map((v, i) => {
            const x = getX(i);
            const y = getY(v);
            const isHovered = hoveredIdx?.type === 'hist' && hoveredIdx.index === i;
            return (
              <circle
                key={`hist-${i}`}
                cx={x}
                cy={y}
                r={isHovered ? 4.5 : 2}
                fill={isHovered ? 'var(--accent)' : 'var(--text-secondary)'}
                className="cursor-pointer"
                onMouseEnter={() => setHoveredIdx({ type: 'hist', index: i })}
                onMouseLeave={() => setHoveredIdx(null)}
              />
            );
          })}

          {q50.map((v, i) => {
            const x = getX(fcOffset + 1 + i);
            const y = getY(v);
            const isHovered = hoveredIdx?.type === 'fc' && hoveredIdx.index === i;
            return (
              <circle
                key={`fc-${i}`}
                cx={x}
                cy={y}
                r={isHovered ? 4.5 : 2}
                fill="var(--accent)"
                className="cursor-pointer"
                onMouseEnter={() => setHoveredIdx({ type: 'fc', index: i })}
                onMouseLeave={() => setHoveredIdx(null)}
              />
            );
          })}
        </svg>

        {/* Hover Tooltip Box */}
        {hoveredIdx && (
          <div
            className="absolute top-2 right-3 bg-[var(--surface-elevated)] p-2.5 rounded-md text-xs pointer-events-none shadow-md border border-[var(--border)] font-mono"
            style={{ zIndex: 10 }}
          >
            {hoveredIdx.type === 'hist' ? (
              <div>
                <span className="text-[10px] text-[var(--text-muted)] font-bold block uppercase tracking-wider">
                  Observed Telemetry
                </span>
                <span className="text-[10px] text-[var(--text-muted)] block">
                  {sampledHistTimes[hoveredIdx.index]?.slice(0, 19).replace('T', ' ')}
                </span>
                <span className="text-sm font-bold text-[var(--text-primary)]">
                  {formatVal(sampledHistVals[hoveredIdx.index])}
                </span>
              </div>
            ) : (
              <div>
                <span className="text-[10px] text-[var(--accent)] font-bold block uppercase tracking-wider">
                  Forecast Median (q50)
                </span>
                <span className="text-[10px] text-[var(--text-muted)] block">
                  {forecastTimestamps[hoveredIdx.index]?.slice(0, 19).replace('T', ' ')}
                </span>
                <span className="text-sm font-bold text-[var(--text-primary)]">
                  {formatVal(q50[hoveredIdx.index])}
                </span>
                {q10[hoveredIdx.index] !== undefined && q90[hoveredIdx.index] !== undefined && (
                  <span className="text-[10px] text-[var(--text-secondary)] block mt-0.5">
                    Range: [{formatVal(q10[hoveredIdx.index])} – {formatVal(q90[hoveredIdx.index])}]
                  </span>
                )}
              </div>
            )}
          </div>
        )}
      </div>

      {/* Axis Timestamps */}
      <div className="flex items-center justify-between text-[10px] text-[var(--text-muted)] font-mono px-2 pt-1 border-t border-[var(--border)]">
        <span>{sampledHistTimes[0]?.slice(5, 16).replace('T', ' ')}</span>
        <span>{sampledHistTimes[sampledHistTimes.length - 1]?.slice(5, 16).replace('T', ' ')} (Cutoff)</span>
        <span>
          {forecastTimestamps.length > 0
            ? forecastTimestamps[forecastTimestamps.length - 1]?.slice(5, 16).replace('T', ' ')
            : 'Horizon End'}
        </span>
      </div>
    </div>
  );
};
