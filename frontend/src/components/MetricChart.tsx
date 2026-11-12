import React, { useState } from 'react';

export interface ChartSeries {
  id: string;
  label: string;
  color: string;
  dashed?: boolean;
  values: (number | null)[];
}

interface MetricChartProps {
  title?: string;
  subtitle?: string;
  labels: string[];
  series: ChartSeries[];
  bandLower?: (number | null)[];
  bandUpper?: (number | null)[];
  bandLabel?: string;
  thresholdValue?: number | null;
  thresholdLabel?: string;
  unit?: string;
  height?: number;
  emptyMessage?: string;
}

export const MetricChart: React.FC<MetricChartProps> = ({
  title,
  subtitle,
  labels,
  series,
  bandLower,
  bandUpper,
  bandLabel = 'P10–P90 Interval',
  thresholdValue,
  thresholdLabel,
  unit = '',
  height = 220,
  emptyMessage = 'No telemetry data available for this selection.',
}) => {
  const [hoverIdx, setHoverIdx] = useState<number | null>(null);

  const allVals: number[] = [];
  series.forEach((s) =>
    s.values.forEach((v) => {
      if (v !== null && Number.isFinite(v)) allVals.push(v);
    })
  );
  if (bandLower) bandLower.forEach((v) => v !== null && Number.isFinite(v) && allVals.push(v));
  if (bandUpper) bandUpper.forEach((v) => v !== null && Number.isFinite(v) && allVals.push(v));
  if (thresholdValue !== null && thresholdValue !== undefined && Number.isFinite(thresholdValue)) {
    allVals.push(thresholdValue);
  }

  if (labels.length === 0 || allVals.length === 0) {
    return (
      <div className="bg-[var(--surface-primary)] border border-[var(--border-subtle)] rounded-lg p-5">
        {title && <h3 className="text-sm font-semibold text-[var(--text-primary)]">{title}</h3>}
        {subtitle && <p className="text-xs text-[var(--text-muted)] mt-0.5">{subtitle}</p>}
        <div className="h-36 flex items-center justify-center text-xs text-[var(--text-muted)] bg-[var(--surface-secondary)] rounded mt-3 border border-dashed border-[var(--border-subtle)]">
          {emptyMessage}
        </div>
      </div>
    );
  }

  const rawMin = Math.min(...allVals);
  const rawMax = Math.max(...allVals);
  const span = Math.max(1e-3, rawMax - rawMin);
  const minV = rawMin - span * 0.08;
  const maxV = rawMax + span * 0.08;

  const w = 680;
  const h = height;
  const padL = 48;
  const padR = 16;
  const padT = 16;
  const padB = 28;
  const plotW = w - padL - padR;
  const plotH = h - padT - padB;

  const xPos = (idx: number) =>
    labels.length <= 1 ? padL + plotW / 2 : padL + (idx / (labels.length - 1)) * plotW;
  const yPos = (val: number) =>
    padT + plotH - ((val - minV) / Math.max(1e-6, maxV - minV)) * plotH;

  // Uncertainty band polygon
  let bandPath = '';
  if (bandLower && bandUpper && bandLower.length === labels.length && bandUpper.length === labels.length) {
    const upperPts: string[] = [];
    const lowerPts: string[] = [];
    for (let i = 0; i < labels.length; i++) {
      const u = bandUpper[i];
      const l = bandLower[i];
      if (u !== null && l !== null && Number.isFinite(u) && Number.isFinite(l)) {
        upperPts.push(`${xPos(i).toFixed(1)},${yPos(u).toFixed(1)}`);
        lowerPts.unshift(`${xPos(i).toFixed(1)},${yPos(l).toFixed(1)}`);
      }
    }
    if (upperPts.length >= 2) {
      bandPath = `M ${upperPts.join(' L ')} L ${lowerPts.join(' L ')} Z`;
    }
  }

  const formatLabel = (raw: string) => {
    if (!raw) return '';
    return raw.length > 10 ? raw.slice(5, 16).replace('T', ' ') : raw;
  };

  return (
    <div className="bg-[var(--surface-primary)] border border-[var(--border-subtle)] rounded-lg p-4 sm:p-5 min-w-0">
      <div className="flex flex-wrap items-start justify-between gap-2 mb-3">
        <div className="min-w-0">
          {title && <h3 className="text-sm font-semibold text-[var(--text-primary)]">{title}</h3>}
          {subtitle && <p className="text-xs text-[var(--text-muted)] mt-0.5">{subtitle}</p>}
        </div>
        <div className="flex flex-wrap items-center gap-3 text-[11px] text-[var(--text-secondary)]">
          {series.map((s) => (
            <span key={s.id} className="inline-flex items-center gap-1.5">
              <span
                className="inline-block w-3 h-0.5"
                style={{
                  backgroundColor: s.dashed ? 'transparent' : s.color,
                  borderTop: s.dashed ? `2px dashed ${s.color}` : undefined,
                }}
              />
              {s.label}
            </span>
          ))}
          {bandPath && (
            <span className="inline-flex items-center gap-1.5">
              <span className="inline-block w-3 h-2 rounded-xs bg-[var(--brand-soft)] border border-[var(--brand-primary)]/40" />
              {bandLabel}
            </span>
          )}
        </div>
      </div>

      <div className="w-full overflow-hidden">
        <svg
          viewBox={`0 0 ${w} ${h}`}
          className="w-full h-auto block select-none"
          onMouseLeave={() => setHoverIdx(null)}
        >
          {[0, 0.25, 0.5, 0.75, 1].map((frac) => {
            const val = minV + (maxV - minV) * (1 - frac);
            const y = padT + plotH * frac;
            return (
              <g key={frac}>
                <line x1={padL} y1={y} x2={w - padR} y2={y} stroke="var(--grid-line)" strokeWidth="1" />
                <text x={padL - 6} y={y + 3} textAnchor="end" fontSize="9.5" fill="var(--text-muted)" className="font-mono">
                  {val >= 100 ? val.toFixed(0) : val.toFixed(1)}
                  {unit ? ` ${unit}` : ''}
                </text>
              </g>
            );
          })}

          {bandPath && <path d={bandPath} fill="var(--brand-primary)" fillOpacity="0.12" />}

          {thresholdValue !== null && thresholdValue !== undefined && Number.isFinite(thresholdValue) && (
            <g>
              <line
                x1={padL}
                y1={yPos(thresholdValue)}
                x2={w - padR}
                y2={yPos(thresholdValue)}
                stroke="var(--status-critical)"
                strokeWidth="1.2"
                strokeDasharray="4 4"
              />
              {thresholdLabel && (
                <text
                  x={w - padR - 4}
                  y={Math.max(padT + 10, yPos(thresholdValue) - 4)}
                  textAnchor="end"
                  fontSize="9.5"
                  fill="var(--status-critical)"
                  className="font-mono font-semibold"
                >
                  {thresholdLabel}
                </text>
              )}
            </g>
          )}

          {series.map((s) => {
            const segments: string[] = [];
            let currentSeg: string[] = [];
            s.values.forEach((v, idx) => {
              if (v !== null && Number.isFinite(v)) {
                currentSeg.push(`${xPos(idx).toFixed(1)},${yPos(v).toFixed(1)}`);
              } else if (currentSeg.length > 0) {
                if (currentSeg.length >= 2) segments.push(`M ${currentSeg.join(' L ')}`);
                currentSeg = [];
              }
            });
            if (currentSeg.length >= 2) segments.push(`M ${currentSeg.join(' L ')}`);
            return (
              <g key={s.id}>
                {segments.map((d, segIdx) => (
                  <path
                    key={segIdx}
                    d={d}
                    fill="none"
                    stroke={s.color}
                    strokeWidth="2"
                    strokeDasharray={s.dashed ? '5 4' : undefined}
                  />
                ))}
              </g>
            );
          })}

          {hoverIdx !== null && (
            <line
              x1={xPos(hoverIdx)}
              y1={padT}
              x2={xPos(hoverIdx)}
              y2={padT + plotH}
              stroke="var(--border-strong)"
              strokeWidth="1"
              strokeDasharray="2 2"
            />
          )}

          {labels.map((_, idx) => {
            const sliceW = Math.max(4, plotW / Math.max(1, labels.length));
            return (
              <rect
                key={idx}
                x={xPos(idx) - sliceW / 2}
                y={padT}
                width={sliceW}
                height={plotH}
                fill="transparent"
                onMouseEnter={() => setHoverIdx(idx)}
              />
            );
          })}

          {labels.length > 0 && (
            <>
              <text x={padL} y={h - 6} fontSize="9.5" fill="var(--text-muted)" className="font-mono">
                {formatLabel(labels[0])}
              </text>
              {labels.length > 2 && (
                <text x={padL + plotW / 2} y={h - 6} textAnchor="middle" fontSize="9.5" fill="var(--text-muted)" className="font-mono">
                  {formatLabel(labels[Math.floor(labels.length / 2)])}
                </text>
              )}
              <text x={w - padR} y={h - 6} textAnchor="end" fontSize="9.5" fill="var(--text-muted)" className="font-mono">
                {formatLabel(labels[labels.length - 1])}
              </text>
            </>
          )}
        </svg>
      </div>

      {hoverIdx !== null && (
        <div className="mt-2 pt-2 border-t border-[var(--border-subtle)] flex flex-wrap items-center gap-3 text-[11px] font-mono">
          <span className="text-[var(--text-muted)]">{formatLabel(labels[hoverIdx])}</span>
          {series.map((s) => {
            const v = s.values[hoverIdx];
            if (v === null || v === undefined) return null;
            return (
              <span key={s.id} className="text-[var(--text-primary)]">
                <span style={{ color: s.color }}>●</span> {s.label}: {v.toFixed(2)}
                {unit ? ` ${unit}` : ''}
              </span>
            );
          })}
          {bandLower?.[hoverIdx] !== null && bandLower?.[hoverIdx] !== undefined && bandUpper?.[hoverIdx] !== null && bandUpper?.[hoverIdx] !== undefined && (
            <span className="text-[var(--text-secondary)]">
              Band: [{bandLower[hoverIdx]!.toFixed(2)}, {bandUpper[hoverIdx]!.toFixed(2)}]
            </span>
          )}
        </div>
      )}
    </div>
  );
};
