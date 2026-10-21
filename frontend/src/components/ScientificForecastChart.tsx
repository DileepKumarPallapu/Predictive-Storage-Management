import React, { useState } from 'react';

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

  // Downsample historical points if too dense (e.g. max 100 historical points for crisp SVG rendering)
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
      <div className="h-64 flex items-center justify-center text-obsidian-muted bg-obsidian-panel rounded-lg border border-obsidian-border text-sm">
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
    <div className="bg-obsidian-panel border border-obsidian-border rounded-lg p-4 flex flex-col gap-3">
      <div className="flex items-center justify-between flex-wrap gap-2">
        <h4 className="text-sm font-semibold tracking-wide text-obsidian-text flex items-center gap-2">
          <span className="w-2 h-2 rounded-full bg-obsidian-cyan animate-pulse"></span>
          {title}
        </h4>
        <div className="flex items-center gap-4 text-xs">
          <span className="flex items-center gap-1.5 text-obsidian-muted">
            <span className="w-3 h-0.5 bg-obsidian-cyan inline-block"></span> Observed History
          </span>
          {q50.length > 0 && (
            <span className="flex items-center gap-1.5 text-obsidian-cyan">
              <span className="w-3 h-0.5 bg-obsidian-violet inline-block"></span> Forecast Median (q50)
            </span>
          )}
          {q10.length > 0 && (
            <span className="flex items-center gap-1.5 text-obsidian-muted">
              <span className="w-3 h-2 bg-obsidian-cyan opacity-25 inline-block rounded-sm"></span> 80% Confidence [q10, q90]
            </span>
          )}
          {counterfactualQ50.length > 0 && (
            <span className="flex items-center gap-1.5 text-obsidian-teal font-medium">
              <span className="w-3 h-0.5 border-t border-dashed border-obsidian-teal inline-block"></span> Counterfactual Simulation
            </span>
          )}
          {hardConstraint !== null && (
            <span className="flex items-center gap-1.5 text-obsidian-coral font-medium">
              <span className="w-3 h-0.5 border-t border-dashed border-obsidian-coral inline-block"></span> Hard Constraint
            </span>
          )}
        </div>
      </div>

      <div className="relative w-full overflow-hidden">
        <svg
          viewBox={`0 0 ${width} ${height}`}
          className="w-full h-auto select-none"
          style={{ maxHeight: '340px' }}
        >
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
                  strokeOpacity="0.4"
                />
                <text
                  x={padLeft - 8}
                  y={y + 4}
                  textAnchor="end"
                  fill="var(--text-secondary)"
                  className="text-[10px] font-mono"
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
              fill="var(--accent-cyan)"
              fillOpacity="0.12"
            />
          )}

          {/* Observed Historical Line */}
          <path
            d={histPath}
            fill="none"
            stroke="var(--accent-cyan)"
            strokeWidth="2"
          />

          {/* Forecast Median Line */}
          {fcMedianPath && (
            <path
              d={fcMedianPath}
              fill="none"
              stroke="var(--accent-violet)"
              strokeWidth="2.2"
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
              r="4"
              className="opacity-0 hover:opacity-100 fill-obsidian-cyan cursor-pointer transition-opacity"
              onMouseEnter={() => setHoveredIdx({ type: 'hist', index: i })}
              onMouseLeave={() => setHoveredIdx(null)}
            />
          ))}

          {q50.map((v, i) => (
            <circle
              key={`f-${i}`}
              cx={getX(fcOffset + 1 + i)}
              cy={getY(v)}
              r="4"
              className="opacity-0 hover:opacity-100 fill-obsidian-violet cursor-pointer transition-opacity"
              onMouseEnter={() => setHoveredIdx({ type: 'fc', index: i })}
              onMouseLeave={() => setHoveredIdx(null)}
            />
          ))}
        </svg>

        {/* Floating Tooltip Info */}
        {hoveredIdx && (
          <div className="absolute top-2 right-4 bg-obsidian-raised border border-obsidian-border rounded px-3 py-1.5 shadow-lg text-xs font-mono">
            {hoveredIdx.type === 'hist' ? (
              <div>
                <span className="text-obsidian-muted">Observed: </span>
                <span className="text-obsidian-cyan font-bold">
                  {formatVal(sampledHistVals[hoveredIdx.index])}
                </span>
                <div className="text-[10px] text-obsidian-muted">
                  {new Date(sampledHistTimes[hoveredIdx.index]).toLocaleString()}
                </div>
              </div>
            ) : (
              <div>
                <span className="text-obsidian-muted">Forecast (q50): </span>
                <span className="text-obsidian-violet font-bold">
                  {formatVal(q50[hoveredIdx.index])}
                </span>
                {q10[hoveredIdx.index] && (
                  <div className="text-[10px] text-obsidian-muted">
                    80% Interval: [{formatVal(q10[hoveredIdx.index])} — {formatVal(q90[hoveredIdx.index])}]
                  </div>
                )}
                <div className="text-[10px] text-obsidian-muted">
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
