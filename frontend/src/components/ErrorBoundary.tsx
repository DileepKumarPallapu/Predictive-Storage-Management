import React, { Component, ErrorInfo, ReactNode } from "react";
import { AlertOctagon, RotateCcw } from "lucide-react";

interface Props {
  children: ReactNode;
}

interface State {
  hasError: boolean;
  error: Error | null;
}

export class ErrorBoundary extends Component<Props, State> {
  public state: State = {
    hasError: false,
    error: null,
  };

  public static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error };
  }

  public componentDidCatch(error: Error, errorInfo: ErrorInfo) {
    console.error("Uncaught Error inside AEGISSTOR UI:", error, errorInfo);
  }

  private handleReset = () => {
    this.setState({ hasError: false, error: null });
    window.location.reload();
  };

  public render() {
    if (this.state.hasError) {
      return (
        <div className="min-h-screen bg-[var(--bg-primary)] flex items-center justify-center p-6 text-[var(--text-primary)]">
          <div className="max-w-md w-full glass-modal border border-[var(--status-critical)]/40 rounded-2xl p-6 text-center shadow-glass-modal">
            <div className="w-12 h-12 rounded-full bg-[var(--status-critical)]/15 border border-[var(--status-critical)]/30 flex items-center justify-center mx-auto mb-4 text-[var(--status-critical)]">
              <AlertOctagon size={28} />
            </div>
            <h2 className="text-lg font-bold text-[var(--text-primary)] tracking-tight">
              Interface Resilience Fault
            </h2>
            <p className="text-xs text-[var(--text-secondary)] mt-2 leading-relaxed">
              A component rendering exception was trapped by the Storage Resilience Error Boundary.
            </p>
            {this.state.error && (
              <pre className="mt-4 p-3 bg-[var(--surface-secondary)] border border-[var(--border-subtle)] rounded text-[11px] font-mono text-[var(--status-critical)] overflow-x-auto text-left">
                {this.state.error.message}
              </pre>
            )}
            <button
              onClick={this.handleReset}
              className="mt-5 w-full btn-primary flex items-center justify-center gap-2 px-4 py-2.5 rounded-lg text-xs font-semibold"
            >
              <RotateCcw size={14} />
              Reload Platform Interface
            </button>
          </div>
        </div>
      );
    }

    return this.props.children;
  }
}
