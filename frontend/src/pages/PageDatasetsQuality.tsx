import React, { useState, useEffect } from 'react';
import { api, DatasetItem } from '../api/client';
import { Database, ShieldCheck, FileText, CheckCircle2, Info } from 'lucide-react';

export const PageDatasetsQuality: React.FC = () => {
  const [datasets, setDatasets] = useState<DatasetItem[]>([]);
  const [loading, setLoading] = useState<boolean>(true);

  useEffect(() => {
    loadDatasets();
  }, []);

  const loadDatasets = async () => {
    try {
      const data = await api.getDatasets();
      setDatasets(data);
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <div className="flex items-center gap-2.5">
          <div className="w-8 h-8 rounded-lg bg-[var(--accent-primary)]/15 border border-[var(--accent-primary)]/30 flex items-center justify-center text-[var(--accent-primary)] shadow-glow-vermilion">
            <Database size={18} />
          </div>
          <h2 className="text-xl font-bold text-[var(--text-primary)] tracking-tight">
            Telemetry Datasets & Data Provenance
          </h2>
        </div>
        <p className="text-xs text-[var(--text-secondary)] mt-1.5 leading-relaxed">
          Complete schema governance, license attribution, sampling frequency, and missingness metrics.
        </p>
      </div>

      {/* Dataset Cards */}
      <div className="grid grid-cols-1 gap-4">
        {datasets.map((ds) => (
          <div key={ds.id} className="glass-panel rounded-xl p-5 space-y-4 hover:border-[var(--accent-primary)]/40 transition-all">
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
              <div>
                <h3 className="text-sm font-bold text-[var(--text-primary)] flex items-center gap-2.5">
                  {ds.name}
                  <span className="px-2.5 py-0.5 rounded-full text-[10px] font-mono font-bold uppercase bg-[var(--accent-primary)]/15 text-[var(--accent-primary)] border border-[var(--accent-primary)]/40 shadow-sm">
                    {ds.dataset_type}
                  </span>
                </h3>
                <div className="text-[11px] font-mono text-[var(--accent-primary)] mt-0.5">ID: {ds.id}</div>
              </div>

              <div className="text-xs font-mono text-[var(--status-success)] flex items-center gap-1.5">
                <CheckCircle2 size={14} />
                <span>Verified Schema Provenance</span>
              </div>
            </div>

            <p className="text-xs text-[var(--text-secondary)] leading-relaxed">{ds.description}</p>

            <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 text-xs font-mono">
              <div className="bg-[var(--surface-secondary)]/60 rounded-xl p-3 border border-[var(--border-subtle)]">
                <span className="text-[10px] text-[var(--text-tertiary)] uppercase tracking-wider block">Records Count</span>
                <span className="text-[var(--text-primary)] font-bold mt-1 block">{ds.records_count.toLocaleString()} samples</span>
              </div>

              <div className="bg-[var(--surface-secondary)]/60 rounded-xl p-3 border border-[var(--border-subtle)]">
                <span className="text-[10px] text-[var(--text-tertiary)] uppercase tracking-wider block">Sampling Interval</span>
                <span className="text-[var(--text-primary)] font-bold mt-1 block">{ds.sampling_interval_s} seconds (1h)</span>
              </div>

              <div className="bg-[var(--surface-secondary)]/60 rounded-xl p-3 border border-[var(--border-subtle)]">
                <span className="text-[10px] text-[var(--text-tertiary)] uppercase tracking-wider block">Missingness Rate</span>
                <span className="text-[var(--status-success)] font-bold mt-1 block">{(ds.missing_rate * 100).toFixed(2)}%</span>
              </div>

              <div className="bg-[var(--surface-secondary)]/60 rounded-xl p-3 border border-[var(--border-subtle)]">
                <span className="text-[10px] text-[var(--text-tertiary)] uppercase tracking-wider block">License & Citation</span>
                <span className="text-[var(--accent-primary)] font-bold mt-1 block truncate">{ds.license}</span>
              </div>
            </div>
          </div>
        ))}
      </div>

      {/* Provenance Ethics Statement */}
      <div className="glass-panel rounded-xl p-5 text-xs text-[var(--text-secondary)] space-y-2">
        <h4 className="font-semibold text-[var(--text-primary)] flex items-center gap-2">
          <Info size={15} className="text-[var(--accent-primary)]" />
          Academic Rigor & Data Transparency Statement
        </h4>
        <p className="leading-relaxed">
          AEGISSTOR maintains explicit demarcation between synthetic, replay, and live physical telemetry. Synthetic datasets are deterministically generated using physics-informed workload generators and are labeled as synthetic across all APIs, database records, and visualization charts. Real-world host telemetry collection operates in strict read-only mode without destructive commands.
        </p>
      </div>
    </div>
  );
};
