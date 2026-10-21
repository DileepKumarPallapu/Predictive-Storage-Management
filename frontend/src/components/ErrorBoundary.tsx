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
        <div className="min-h-screen bg-obsidian-bg flex items-center justify-center p-6">
          <div className="max-w-md w-full bg-obsidian-panel border border-obsidian-coral/40 rounded-xl p-6 text-center shadow-2xl">
            <div className="w-12 h-12 rounded-full bg-obsidian-coral/15 border border-obsidian-coral/30 flex items-center justify-center mx-auto mb-4 text-obsidian-coral">
              <AlertOctagon size={28} />
            </div>
            <h2 className="text-lg font-bold text-obsidian-text tracking-tight">
              Interface Resilience Fault
            </h2>
            <p className="text-xs text-obsidian-muted mt-2 leading-relaxed">
              A component rendering exception was trapped by the Storage Resilience Error Boundary.
            </p>
            {this.state.error && (
              <pre className="mt-4 p-3 bg-obsidian-secondary border border-obsidian-border rounded text-[11px] font-mono text-obsidian-coral overflow-x-auto text-left">
                {this.state.error.message}
              </pre>
            )}
            <button
              onClick={this.handleReset}
              className="mt-5 w-full flex items-center justify-center gap-2 px-4 py-2 bg-obsidian-cyan/15 hover:bg-obsidian-cyan/25 border border-obsidian-cyan/40 text-obsidian-cyan rounded-lg text-xs font-semibold transition-colors"
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
