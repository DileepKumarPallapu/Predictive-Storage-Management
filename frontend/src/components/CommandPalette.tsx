import React, { useState, useEffect, useRef } from 'react';
import { Search, HardDrive, LayoutDashboard, Cpu, Activity, AlertTriangle, Shield, Sliders, X } from 'lucide-react';
import { PageId } from './Sidebar';

interface CommandPaletteProps {
  isOpen: boolean;
  onClose: () => void;
  onNavigatePage: (page: PageId) => void;
  onNavigateDevice: (deviceId: string) => void;
}

export const CommandPalette: React.FC<CommandPaletteProps> = ({
  isOpen,
  onClose,
  onNavigatePage,
  onNavigateDevice,
}) => {
  const [query, setQuery] = useState('');
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    if (isOpen) {
      setTimeout(() => inputRef.current?.focus(), 50);
    } else {
      setQuery('');
    }
  }, [isOpen]);

  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key === 'k') {
        e.preventDefault();
        if (isOpen) onClose();
        else {
          // Trigger open handled by parent or shortcut
        }
      } else if (e.key === 'Escape' && isOpen) {
        onClose();
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [isOpen, onClose]);

  if (!isOpen) return null;

  const devices = [
    { id: 'vol-nvme-tier1-db', name: 'Production E-Commerce OLTP NVMe', tier: 'NVME_TIER1' },
    { id: 'vol-sas-tier2-analytics', name: 'Corporate Data Warehouse & ETL SAS', tier: 'SAS_TIER2' },
    { id: 'vol-hdd-archive', name: 'Long-term Regulatory Compliance HDD', tier: 'HDD_ARCHIVE' },
    { id: 'vol-nvme-cache', name: 'Redis / Kafka High-Throughput NVMe Cache', tier: 'NVME_TIER1' },
  ];

  const pages: { id: PageId; label: string; icon: any }[] = [
    { id: 'overview', label: 'Executive Overview', icon: LayoutDashboard },
    { id: 'fleet', label: 'Storage Fleet', icon: HardDrive },
    { id: 'intelligence', label: 'Device Intelligence', icon: Cpu },
    { id: 'twin', label: 'Storage Digital Twin', icon: Activity },
    { id: 'interventions', label: 'Intervention Studio', icon: Sliders },
    { id: 'alerts', label: 'Alerts & Incidents', icon: AlertTriangle },
    { id: 'settings', label: 'Settings & Audit Trail', icon: Shield },
  ];

  const filteredDevices = devices.filter(
    (d) =>
      d.name.toLowerCase().includes(query.toLowerCase()) ||
      d.id.toLowerCase().includes(query.toLowerCase())
  );

  const filteredPages = pages.filter((p) =>
    p.label.toLowerCase().includes(query.toLowerCase())
  );

  return (
    <div className="fixed inset-0 z-50 bg-black/60 backdrop-blur-sm flex items-start justify-center pt-20 p-4">
      <div className="bg-obsidian-surface border border-obsidian-border rounded-xl shadow-2xl w-full max-w-xl overflow-hidden animate-in fade-in zoom-in-95 duration-100">
        {/* Search Input Header */}
        <div className="flex items-center px-4 py-3 border-b border-obsidian-border bg-obsidian-raised">
          <Search size={18} className="text-obsidian-cyan mr-3" />
          <input
            ref={inputRef}
            type="text"
            placeholder="Search storage pools, pages, or commands (Ctrl+K)..."
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            className="flex-1 bg-transparent text-sm text-obsidian-text placeholder-obsidian-muted focus:outline-none"
          />
          <button
            onClick={onClose}
            className="p-1 text-obsidian-muted hover:text-obsidian-text rounded hover:bg-obsidian-surface"
          >
            <X size={16} />
          </button>
        </div>

        {/* Results List */}
        <div className="max-h-80 overflow-y-auto p-2 space-y-3">
          {/* Devices Section */}
          {filteredDevices.length > 0 && (
            <div>
              <div className="text-[10px] uppercase font-mono font-bold text-obsidian-muted px-3 py-1">
                Storage Pools
              </div>
              <div className="space-y-1">
                {filteredDevices.map((dev) => (
                  <button
                    key={dev.id}
                    onClick={() => {
                      onNavigateDevice(dev.id);
                      onClose();
                    }}
                    className="w-full flex items-center justify-between px-3 py-2 rounded-lg text-left text-xs hover:bg-obsidian-cyan/15 group transition-colors"
                  >
                    <div className="flex items-center gap-2.5">
                      <HardDrive size={15} className="text-obsidian-cyan group-hover:scale-110 transition-transform" />
                      <div>
                        <div className="font-semibold text-obsidian-text">{dev.name}</div>
                        <div className="font-mono text-[10px] text-obsidian-muted">{dev.id}</div>
                      </div>
                    </div>
                    <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-obsidian-panel border border-obsidian-border text-obsidian-cyan">
                      {dev.tier}
                    </span>
                  </button>
                ))}
              </div>
            </div>
          )}

          {/* Navigation Section */}
          {filteredPages.length > 0 && (
            <div>
              <div className="text-[10px] uppercase font-mono font-bold text-obsidian-muted px-3 py-1">
                Platform Views
              </div>
              <div className="space-y-1">
                {filteredPages.map((page) => {
                  const Icon = page.icon;
                  return (
                    <button
                      key={page.id}
                      onClick={() => {
                        onNavigatePage(page.id);
                        onClose();
                      }}
                      className="w-full flex items-center gap-2.5 px-3 py-2 rounded-lg text-left text-xs text-obsidian-text hover:bg-obsidian-raised group transition-colors"
                    >
                      <Icon size={15} className="text-obsidian-muted group-hover:text-obsidian-cyan" />
                      <span className="font-medium">{page.label}</span>
                    </button>
                  );
                })}
              </div>
            </div>
          )}

          {filteredDevices.length === 0 && filteredPages.length === 0 && (
            <div className="text-center py-8 text-xs text-obsidian-muted">
              No matching storage volumes or pages found for "{query}".
            </div>
          )}
        </div>

        {/* Footer shortcuts */}
        <div className="px-4 py-2 bg-obsidian-panel border-t border-obsidian-border flex items-center justify-between text-[11px] text-obsidian-muted font-mono">
          <span>Navigate with click or arrow keys</span>
          <span>ESC to dismiss</span>
        </div>
      </div>
    </div>
  );
};
