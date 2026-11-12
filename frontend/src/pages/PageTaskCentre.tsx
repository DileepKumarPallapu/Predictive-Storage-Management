import React, { useCallback, useEffect, useState } from "react";
import {
  AlertTriangle,
  CheckCircle2,
  ClipboardList,
  Clock,
  MessageSquare,
  Plus,
  RefreshCw,
  Send,
  UserCheck,
} from "lucide-react";
import { api } from "../api/client";
import { useRealtimeSubscription } from "../context/RealtimeContext";

interface PageTaskCentreProps {
  currentUserRole: string;
  currentUsername: string;
}

const STATUS_BADGE: Record<string, string> = {
  ASSIGNED: "bg-blue-500/15 text-blue-600 dark:text-blue-400 border-blue-500/30",
  ACKNOWLEDGED: "bg-indigo-500/15 text-indigo-600 dark:text-indigo-400 border-indigo-500/30",
  IN_PROGRESS: "bg-amber-500/15 text-amber-600 dark:text-amber-400 border-amber-500/30",
  WAITING: "bg-slate-500/15 text-slate-600 dark:text-slate-300 border-slate-500/30",
  COMPLETED: "bg-emerald-500/15 text-emerald-600 dark:text-emerald-400 border-emerald-500/30",
  CANCELLED: "bg-rose-500/15 text-rose-600 dark:text-rose-400 border-rose-500/30",
};

const PRIORITY_BADGE: Record<string, string> = {
  CRITICAL: "bg-rose-500/15 text-rose-600 dark:text-rose-400 border-rose-500/30",
  HIGH: "bg-amber-500/15 text-amber-600 dark:text-amber-400 border-amber-500/30",
  MEDIUM: "bg-blue-500/15 text-blue-600 dark:text-blue-400 border-blue-500/30",
  LOW: "bg-slate-500/15 text-slate-500 border-slate-500/30",
};

export const PageTaskCentre: React.FC<PageTaskCentreProps> = ({
  currentUserRole,
  currentUsername,
}) => {
  const isAdmin = currentUserRole === "ADMIN";
  const [tasks, setTasks] = useState<any[]>([]);
  const [users, setUsers] = useState<any[]>([]);
  const [devices, setDevices] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [statusFilter, setStatusFilter] = useState<string>("");
  const [selectedTaskId, setSelectedTaskId] = useState<string | null>(null);
  const [conflictBanner, setConflictBanner] = useState<string | null>(null);
  const [commentText, setCommentText] = useState("");
  const [submitting, setSubmitting] = useState(false);

  // Create task form (Admin or authorized assigner)
  const [showCreate, setShowCreate] = useState(false);
  const [newTitle, setNewTitle] = useState("");
  const [newDesc, setNewDesc] = useState("");
  const [newPriority, setNewPriority] = useState("HIGH");
  const [newAssigneeId, setNewAssigneeId] = useState("");
  const [newDeviceId, setNewDeviceId] = useState("");
  const [createError, setCreateError] = useState<string | null>(null);

  const loadData = useCallback(async () => {
    try {
      const [taskRes, devRes] = await Promise.all([
        api.listTasks(statusFilter || undefined, false),
        api.getDevices(),
      ]);
      setTasks(taskRes.tasks || []);
      setDevices(devRes || []);
      if (isAdmin) {
        try {
          const uRes = await api.listUsers();
          setUsers((uRes || []).filter((u: any) => u.is_active));
          if (!newAssigneeId && uRes?.length) {
            const op = uRes.find((u: any) => u.role === "OPERATOR" && u.is_active) || uRes[0];
            if (op) setNewAssigneeId(op.id);
          }
        } catch {
          // ignore if lacking users.read
        }
      }
    } finally {
      setLoading(false);
    }
  }, [statusFilter, isAdmin, newAssigneeId]);

  useEffect(() => {
    loadData();
  }, [loadData]);

  useRealtimeSubscription(["task.", "storage."], () => {
    loadData();
  });

  const selectedTask = tasks.find((t) => t.id === selectedTaskId) || tasks[0] || null;

  const handleCreateTask = async (e: React.FormEvent) => {
    e.preventDefault();
    setCreateError(null);
    if (!newTitle.trim() || !newAssigneeId) {
      setCreateError("Task title and assignee are required.");
      return;
    }
    setSubmitting(true);
    try {
      const created = await api.createTask({
        title: newTitle.trim(),
        description: newDesc.trim(),
        priority: newPriority,
        assigned_to_user_id: newAssigneeId,
        linked_device_id: newDeviceId || undefined,
      });
      setNewTitle("");
      setNewDesc("");
      setShowCreate(false);
      setSelectedTaskId(created.id);
      await loadData();
    } catch (err: any) {
      setCreateError(err?.message || "Failed to create task.");
    } finally {
      setSubmitting(false);
    }
  };

  const handleUpdateStatus = async (task: any, nextStatus: string) => {
    setConflictBanner(null);
    setSubmitting(true);
    try {
      await api.updateTask(task.id, {
        status: nextStatus,
        expected_version: task.version,
      });
      await loadData();
    } catch (err: any) {
      if (err?.status === 409) {
        setConflictBanner(
          err?.message ||
            "This task was updated by another user. Reloading latest server state.",
        );
        await loadData();
      } else {
        setConflictBanner(err?.message || "Failed to update task status.");
      }
    } finally {
      setSubmitting(false);
    }
  };

  const handleAddComment = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedTask || !commentText.trim()) return;
    setSubmitting(true);
    try {
      await api.addTaskComment(selectedTask.id, commentText.trim());
      setCommentText("");
      await loadData();
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="space-y-5">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="text-xl font-bold text-[var(--text-primary)] flex items-center gap-2">
            <ClipboardList size={20} className="text-[var(--accent)]" />
            Collaborative Operational Task Centre
          </h1>
          <p className="text-xs text-[var(--text-secondary)] mt-0.5">
            Real-time task assignment, acknowledgement, progress updates, and audit-backed comments between Administrator and Operators.
          </p>
        </div>
        <div className="flex items-center gap-2">
          <select
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
            className="px-2.5 py-1.5 rounded-lg bg-[var(--surface)] border border-[var(--border)] text-xs text-[var(--text-primary)]"
          >
            <option value="">All Statuses</option>
            <option value="ASSIGNED">ASSIGNED</option>
            <option value="ACKNOWLEDGED">ACKNOWLEDGED</option>
            <option value="IN_PROGRESS">IN_PROGRESS</option>
            <option value="WAITING">WAITING</option>
            <option value="COMPLETED">COMPLETED</option>
            <option value="CANCELLED">CANCELLED</option>
          </select>
          <button
            onClick={loadData}
            className="px-2.5 py-1.5 rounded-lg border border-[var(--border)] bg-[var(--surface)] hover:bg-[var(--surface-elevated)] text-xs flex items-center gap-1.5"
          >
            <RefreshCw size={13} />
            Refresh
          </button>
          {isAdmin && (
            <button
              onClick={() => setShowCreate((v) => !v)}
              className="px-3 py-1.5 rounded-lg bg-[var(--accent)] text-white font-semibold text-xs flex items-center gap-1.5 hover:opacity-95"
            >
              <Plus size={14} />
              Assign New Task
            </button>
          )}
        </div>
      </div>

      {conflictBanner && (
        <div className="p-3 rounded-lg border border-amber-500/40 bg-amber-500/10 text-amber-700 dark:text-amber-300 text-xs flex items-center justify-between gap-2">
          <span className="flex items-center gap-2 font-medium">
            <AlertTriangle size={15} />
            {conflictBanner}
          </span>
          <button
            onClick={() => {
              setConflictBanner(null);
              loadData();
            }}
            className="px-2 py-1 rounded bg-amber-500/20 hover:bg-amber-500/30 font-semibold"
          >
            Dismiss
          </button>
        </div>
      )}

      {showCreate && isAdmin && (
        <form
          onSubmit={handleCreateTask}
          className="p-4 rounded-xl bg-[var(--surface)] border border-[var(--border)] space-y-3"
        >
          <div className="text-xs font-bold uppercase tracking-wider text-[var(--text-secondary)]">
            Create & Assign Operational Task
          </div>
          {createError && (
            <div className="text-xs text-rose-500 font-medium">{createError}</div>
          )}
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-3">
            <input
              type="text"
              placeholder="Task title (e.g., Expand SAN Tier-1 Pool)"
              value={newTitle}
              onChange={(e) => setNewTitle(e.target.value)}
              className="md:col-span-2 px-3 py-2 rounded-lg bg-[var(--surface-elevated)] border border-[var(--border)] text-xs text-[var(--text-primary)]"
              required
            />
            <select
              value={newAssigneeId}
              onChange={(e) => setNewAssigneeId(e.target.value)}
              className="px-3 py-2 rounded-lg bg-[var(--surface-elevated)] border border-[var(--border)] text-xs text-[var(--text-primary)]"
              required
            >
              <option value="">Select Operator / Assignee</option>
              {users.map((u) => (
                <option key={u.id} value={u.id}>
                  {u.username} ({u.role})
                </option>
              ))}
            </select>
            <select
              value={newPriority}
              onChange={(e) => setNewPriority(e.target.value)}
              className="px-3 py-2 rounded-lg bg-[var(--surface-elevated)] border border-[var(--border)] text-xs text-[var(--text-primary)]"
            >
              <option value="LOW">LOW</option>
              <option value="MEDIUM">MEDIUM</option>
              <option value="HIGH">HIGH</option>
              <option value="CRITICAL">CRITICAL</option>
            </select>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
            <input
              type="text"
              placeholder="Detailed operational instructions..."
              value={newDesc}
              onChange={(e) => setNewDesc(e.target.value)}
              className="md:col-span-2 px-3 py-2 rounded-lg bg-[var(--surface-elevated)] border border-[var(--border)] text-xs text-[var(--text-primary)]"
            />
            <select
              value={newDeviceId}
              onChange={(e) => setNewDeviceId(e.target.value)}
              className="px-3 py-2 rounded-lg bg-[var(--surface-elevated)] border border-[var(--border)] text-xs text-[var(--text-primary)]"
            >
              <option value="">Optional Linked Storage Volume</option>
              {devices.map((d) => (
                <option key={d.id} value={d.id}>
                  {d.name} ({d.id})
                </option>
              ))}
            </select>
          </div>
          <div className="flex justify-end gap-2">
            <button
              type="button"
              onClick={() => setShowCreate(false)}
              className="px-3 py-1.5 rounded-lg border border-[var(--border)] text-xs"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={submitting}
              className="px-4 py-1.5 rounded-lg bg-[var(--accent)] text-white font-semibold text-xs"
            >
              {submitting ? "Assigning..." : "Create & Notify Assignee"}
            </button>
          </div>
        </form>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-12 gap-4">
        {/* Task List */}
        <div className="lg:col-span-5 space-y-2.5">
          {loading ? (
            <div className="p-6 rounded-xl bg-[var(--surface)] border border-[var(--border)] text-xs text-[var(--text-muted)] text-center">
              Loading operational tasks...
            </div>
          ) : tasks.length === 0 ? (
            <div className="p-6 rounded-xl bg-[var(--surface)] border border-[var(--border)] text-xs text-[var(--text-muted)] text-center">
              No operational tasks found.
            </div>
          ) : (
            tasks.map((t) => {
              const active = selectedTask?.id === t.id;
              return (
                <button
                  key={t.id}
                  type="button"
                  onClick={() => setSelectedTaskId(t.id)}
                  className={`w-full text-left p-3.5 rounded-xl border transition-all ${
                    active
                      ? "bg-[var(--surface)] border-[var(--accent)] ring-1 ring-[var(--accent)]/30"
                      : "bg-[var(--surface)] border-[var(--border)] hover:border-[var(--border-strong)]"
                  }`}
                >
                  <div className="flex items-start justify-between gap-2">
                    <div className="font-semibold text-xs text-[var(--text-primary)] line-clamp-1">
                      {t.title}
                    </div>
                    <span
                      className={`px-2 py-0.5 rounded-full text-[10px] font-bold border shrink-0 ${
                        PRIORITY_BADGE[t.priority] || PRIORITY_BADGE.MEDIUM
                      }`}
                    >
                      {t.priority}
                    </span>
                  </div>
                  <div className="mt-2 flex flex-wrap items-center gap-2 text-[11px] text-[var(--text-secondary)]">
                    <span
                      className={`px-2 py-0.5 rounded-full text-[10px] font-semibold border ${
                        STATUS_BADGE[t.status] || STATUS_BADGE.ASSIGNED
                      }`}
                    >
                      {t.status}
                    </span>
                    <span className="flex items-center gap-1">
                      <UserCheck size={12} />
                      {t.assigned_to_username}
                    </span>
                    {t.linked_device_name && (
                      <span className="text-[10px] font-mono bg-[var(--surface-elevated)] px-1.5 py-0.5 rounded">
                        {t.linked_device_name}
                      </span>
                    )}
                    <span className="ml-auto text-[10px] text-[var(--text-muted)] font-mono">
                      v{t.version}
                    </span>
                  </div>
                </button>
              );
            })
          )}
        </div>

        {/* Selected Task Detail & Comments */}
        <div className="lg:col-span-7">
          {selectedTask ? (
            <div className="p-5 rounded-xl bg-[var(--surface)] border border-[var(--border)] space-y-4">
              <div className="flex flex-wrap items-start justify-between gap-3 border-b border-[var(--border)] pb-3">
                <div>
                  <div className="flex items-center gap-2">
                    <span className="text-[10px] font-mono text-[var(--text-muted)]">
                      {selectedTask.id} · v{selectedTask.version}
                    </span>
                    <span
                      className={`px-2 py-0.5 rounded-full text-[10px] font-bold border ${
                        STATUS_BADGE[selectedTask.status] || STATUS_BADGE.ASSIGNED
                      }`}
                    >
                      {selectedTask.status}
                    </span>
                  </div>
                  <h2 className="text-base font-bold text-[var(--text-primary)] mt-1">
                    {selectedTask.title}
                  </h2>
                  <p className="text-xs text-[var(--text-secondary)] mt-1">
                    {selectedTask.description || "No additional description provided."}
                  </p>
                </div>
                <div className="text-right text-[11px] text-[var(--text-secondary)] space-y-1">
                  <div>
                    Assigned to:{" "}
                    <strong className="text-[var(--text-primary)]">
                      {selectedTask.assigned_to_username}
                    </strong>
                  </div>
                  <div>
                    Created by:{" "}
                    <strong className="text-[var(--text-primary)]">
                      {selectedTask.created_by_username}
                    </strong>
                  </div>
                  {selectedTask.updated_at && (
                    <div className="flex items-center justify-end gap-1 text-[10px] text-[var(--text-muted)]">
                      <Clock size={11} />
                      Updated {new Date(selectedTask.updated_at).toLocaleString()}
                    </div>
                  )}
                </div>
              </div>

              {/* Status Workflow Buttons */}
              {(isAdmin || selectedTask.assigned_to_username === currentUsername) && (
                <div className="flex flex-wrap items-center gap-2">
                  <span className="text-[11px] font-semibold text-[var(--text-secondary)] mr-1">
                    Update Status:
                  </span>
                  {["ACKNOWLEDGED", "IN_PROGRESS", "WAITING", "COMPLETED", "CANCELLED"].map(
                    (st) => (
                      <button
                        key={st}
                        type="button"
                        disabled={submitting || selectedTask.status === st}
                        onClick={() => handleUpdateStatus(selectedTask, st)}
                        className={`px-2.5 py-1 rounded-lg text-[11px] font-semibold border transition-colors ${
                          selectedTask.status === st
                            ? "bg-[var(--accent)] text-white border-[var(--accent)]"
                            : "bg-[var(--surface-elevated)] border-[var(--border)] hover:border-[var(--accent)] text-[var(--text-primary)]"
                        } disabled:opacity-50`}
                      >
                        {st === "COMPLETED" && <CheckCircle2 size={11} className="inline mr-1" />}
                        {st}
                      </button>
                    ),
                  )}
                </div>
              )}

              {/* Comment Thread */}
              <div className="space-y-3 pt-2 border-t border-[var(--border)]">
                <div className="text-xs font-bold text-[var(--text-primary)] flex items-center gap-1.5">
                  <MessageSquare size={14} className="text-[var(--accent)]" />
                  Progress Thread ({selectedTask.comments?.length || 0})
                </div>
                <div className="space-y-2 max-h-60 overflow-y-auto pr-1">
                  {(selectedTask.comments || []).length === 0 ? (
                    <div className="text-xs text-[var(--text-muted)] italic">
                      No progress comments yet.
                    </div>
                  ) : (
                    selectedTask.comments.map((c: any) => (
                      <div
                        key={c.id}
                        className="p-2.5 rounded-lg bg-[var(--surface-elevated)] border border-[var(--border)] text-xs"
                      >
                        <div className="flex items-center justify-between text-[11px]">
                          <span className="font-bold text-[var(--text-primary)]">
                            {c.author_username}{" "}
                            <span className="font-normal text-[var(--text-muted)]">
                              ({c.author_role})
                            </span>
                          </span>
                          <span className="text-[10px] text-[var(--text-muted)]">
                            {c.created_at ? new Date(c.created_at).toLocaleTimeString() : ""}
                          </span>
                        </div>
                        <div className="mt-1 text-[var(--text-secondary)]">{c.body}</div>
                      </div>
                    ))
                  )}
                </div>

                <form onSubmit={handleAddComment} className="flex gap-2">
                  <input
                    type="text"
                    placeholder="Post a real-time progress note..."
                    value={commentText}
                    onChange={(e) => setCommentText(e.target.value)}
                    className="flex-1 px-3 py-2 rounded-lg bg-[var(--surface-elevated)] border border-[var(--border)] text-xs text-[var(--text-primary)]"
                  />
                  <button
                    type="submit"
                    disabled={submitting || !commentText.trim()}
                    className="px-3.5 py-2 rounded-lg bg-[var(--accent)] text-white text-xs font-semibold flex items-center gap-1.5 disabled:opacity-50"
                  >
                    <Send size={13} />
                    Post
                  </button>
                </form>
              </div>
            </div>
          ) : (
            <div className="p-8 rounded-xl bg-[var(--surface)] border border-[var(--border)] text-xs text-[var(--text-muted)] text-center">
              Select a task to view details, transition status, or post comments.
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
