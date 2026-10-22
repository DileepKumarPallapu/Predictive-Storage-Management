/**
 * AEGISSTOR FLOWSTATE — High-Performance Scientific Time-Series Decimation
 * Reduces DOM and Canvas/SVG rendering load for high-density telemetry without
 * obscuring critical spikes, SLA threshold breaches, or null intervals.
 */

export interface DecimatedSeries {
  timestamps: string[];
  values: (number | null)[];
  originalCount: number;
  decimatedCount: number;
}

/**
 * Min/Max Bucket Decimation:
 * Divides the series into buckets and preserves both the minimum and maximum
 * within each window. This guarantees that momentary tail latency spikes,
 * capacity jumps, and dropped frames are never smoothed away.
 */
export function decimateTelemetrySeries(
  timestamps: string[],
  values: (number | null)[],
  targetResolution = 144
): DecimatedSeries {
  const n = values.length;
  if (n <= targetResolution || targetResolution <= 0) {
    return {
      timestamps,
      values,
      originalCount: n,
      decimatedCount: n,
    };
  }

  // Bucket size (must accommodate 2 points per bucket: min & max)
  const bucketCount = Math.floor(targetResolution / 2);
  const bucketSize = n / bucketCount;

  const resultTimestamps: string[] = [];
  const resultValues: (number | null)[] = [];

  for (let b = 0; b < bucketCount; b++) {
    const startIdx = Math.floor(b * bucketSize);
    const endIdx = Math.min(n, Math.floor((b + 1) * bucketSize));

    let minVal: number | null = null;
    let maxVal: number | null = null;
    let minIdx = startIdx;
    let maxIdx = startIdx;

    for (let i = startIdx; i < endIdx; i++) {
      const v = values[i];
      if (v === null || v === undefined || isNaN(v)) {
        continue;
      }
      if (minVal === null || v < minVal) {
        minVal = v;
        minIdx = i;
      }
      if (maxVal === null || v > maxVal) {
        maxVal = v;
        maxIdx = i;
      }
    }

    if (minVal === null) {
      // Entire bucket was null/missing data - preserve null to prevent false zeros
      resultTimestamps.push(timestamps[startIdx] || '');
      resultValues.push(null);
    } else if (minIdx === maxIdx) {
      // Flat bucket
      resultTimestamps.push(timestamps[minIdx] || '');
      resultValues.push(minVal);
    } else {
      // Preserve chronological order of min and max in this bucket
      if (minIdx < maxIdx) {
        resultTimestamps.push(timestamps[minIdx] || '');
        resultValues.push(minVal);
        resultTimestamps.push(timestamps[maxIdx] || '');
        resultValues.push(maxVal);
      } else {
        resultTimestamps.push(timestamps[maxIdx] || '');
        resultValues.push(maxVal);
        resultTimestamps.push(timestamps[minIdx] || '');
        resultValues.push(minVal);
      }
    }
  }

  return {
    timestamps: resultTimestamps,
    values: resultValues,
    originalCount: n,
    decimatedCount: resultValues.length,
  };
}
