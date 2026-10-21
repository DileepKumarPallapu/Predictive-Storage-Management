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
        <h2 className="text-xl font-bold text-obsidian-text tracking-tight flex items-center gap-2">
          <Database className="text-obsidian-cyan" size={22} />
          Telemetry Datasets & Data Provenance
        </h2>
        <p className="text-xs text-obsidian-muted mt-1">
          Complete schema governance, license attribution, sampling frequency, and missingness metrics.
        </p>
      </div>

      {/* Dataset Cards */}
      <div className="grid grid-cols-1 gap-4">
        {datasets.map((ds) => (
          <div key={ds.id} className="bg-obsidian-panel border border-obsidian-border rounded-lg p-5 space-y-4">
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
              <div>
                <h3 className="text-sm font-bold text-obsidian-text flex items-center gap-2">
                  {ds.name}
                  <span className="px-2 py-0.5 rounded text-[10px] font-mono font-bold uppercase bg-obsidian-cyan/15 text-obsidian-cyan border border-obsidian-cyan/40">
                    {ds.dataset_type}
                  </span>
                </h3>
                <div className="text-[11px] font-mono text-obsidian-muted mt-0.5">ID: {ds.id}</div>
              </div>

              <div className="text-xs font-mono text-obsidian-teal flex items-center gap-1.5">
                <CheckCircle2 size={14} />
                <span>Verified Schema Provenance</span>
              </div>
            </div>

            <p className="text-xs text-obsidian-muted leading-relaxed">{ds.description}</p>

            <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 text-xs font-mono">
              <div className="bg-obsidian-secondary/50 rounded p-2.5 border border-obsidian-border/50">
                <span className="text-[10px] text-obsidian-muted block">Records Count</span>
                <span className="text-obsidian-text font-bold mt-1 block">{ds.records_count.toLocaleString()} samples</span>
              </div>

              <div className="bg-obsidian-secondary/50 rounded p-2.5 border border-obsidian-border/50">
                <span className="text-[10px] text-obsidian-muted block">Sampling Interval</span>
                <span className="text-obsidian-text font-bold mt-1 block">{ds.sampling_interval_s} seconds (1h)</span>
              </div>

              <div className="bg-obsidian-secondary/50 rounded p-2.5 border border-obsidian-border/50">
                <span className="text-[10px] text-obsidian-muted block">Missingness Rate</span>
                <span className="text-obsidian-teal font-bold mt-1 block">{(ds.missing_rate * 100).toFixed(2)}%</span>
              </div>

              <div className="bg-obsidian-secondary/50 rounded p-2.5 border border-obsidian-border/50">
                <span className="text-[10px] text-obsidian-muted block">License & Citation</span>
                <span className="text-obsidian-cyan font-bold mt-1 block truncate">{ds.license}</span>
              </div>
            </div>
          </div>
        ))}
      </div>

      {/* Provenance Ethics Statement */}
      <div className="bg-obsidian-panel border border-obsidian-border rounded-lg p-5 text-xs text-obsidian-muted space-y-2">
        <h4 className="font-semibold text-obsidian-text flex items-center gap-2">
          <Info size={15} className="text-obsidian-cyan" />
          Academic Rigor & Data Transparency Statement
        </h4>
        <p className="leading-relaxed">
          AEGISSTOR maintains explicit demarcation between synthetic, replay, and live physical telemetry. Synthetic datasets are deterministically generated using physics-informed workload generators and are labeled as synthetic across all APIs, database records, and visualization charts. Real-world host telemetry collection operates in strict read-only mode without destructive commands.
        </p>
      </div>
    </div>
  );
};
