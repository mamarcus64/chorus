export class ApiError extends Error {
  status: number;
  constructor(status: number, message: string) {
    super(message);
    this.status = status;
  }
}

export interface User {
  id: string;
  username: string;
  is_admin: boolean;
}

export interface Choice {
  value: string;
  label: string;
  key: string;
}

export interface TaskConfig {
  prompt: string;
  choices: Choice[];
  overlays: string[];
  instructions: string;
}

export interface PartitionEntry {
  id: string;
  name: string;
  description: string | null;
  task_id: string;
  task_name: string;
  code_key: string;
  assignment: string;
  item_count: number;
  answered_count: number;
  status: "todo" | "not_assigned" | "done";
  done_via: string | null;
}

export interface ItemRecord {
  id: string;
  ordinal: number;
  kind: string;
  locator: Record<string, unknown>;
  features: Record<string, unknown>;
  answer: { choice?: string } | null;
}

export interface PartitionDetail {
  partition: { id: string; name: string; description: string | null };
  task: { id: string; name: string; code_key: string; code_version: number; config: TaskConfig };
  items: ItemRecord[];
  progress: { status: string; done_via: string | null } | null;
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(path, {
    ...init,
    credentials: "include",
    headers: {
      "Content-Type": "application/json",
      ...(init?.headers ?? {}),
    },
  });
  if (!response.ok) {
    let detail = response.statusText;
    try {
      const body = await response.json();
      if (typeof body.detail === "string") detail = body.detail;
    } catch {
      /* the body was not JSON */
    }
    throw new ApiError(response.status, detail);
  }
  if (response.status === 204) return undefined as T;
  return response.json() as Promise<T>;
}

export function mediaUrl(project: string, fileId: string): string {
  return `/api/p/${project}/media/${encodeURIComponent(fileId)}`;
}

export const api = {
  me: (project: string) => request<User>(`/api/p/${project}/auth/me`),
  register: (project: string, username: string, password: string, registrationKey: string) =>
    request<User>(`/api/p/${project}/auth/register`, {
      method: "POST",
      body: JSON.stringify({ username, password, registration_key: registrationKey }),
    }),
  login: (project: string, username: string, password: string) =>
    request<User>(`/api/p/${project}/auth/login`, {
      method: "POST",
      body: JSON.stringify({ username, password }),
    }),
  logout: (project: string) => request<{ ok: boolean }>(`/api/p/${project}/auth/logout`, { method: "POST" }),
  home: (project: string) =>
    request<Record<"todo" | "not_assigned" | "done", PartitionEntry[]>>(`/api/p/${project}/home`),
  partition: (project: string, id: string) =>
    request<PartitionDetail>(`/api/p/${project}/partitions/${id}`),
  markDone: (project: string, id: string) =>
    request<{ list_status: string }>(`/api/p/${project}/partitions/${id}/mark-done`, { method: "POST" }),
  reopen: (project: string, id: string) =>
    request<{ list_status: string }>(`/api/p/${project}/partitions/${id}/reopen`, { method: "POST" }),
  saveAnnotation: (project: string, itemId: string, value: Record<string, unknown>, elapsedMs: number) =>
    request<{ annotation: { value: Record<string, unknown> }; list_status: string }>(
      `/api/p/${project}/items/${itemId}/annotation`,
      { method: "PUT", body: JSON.stringify({ value, elapsed_ms: elapsedMs }) },
    ),
  admin: (project: string) => request<AdminPayload>(`/api/p/${project}/admin/partitions`),
  setAssignment: (project: string, id: string, mode: string, userIds: string[]) =>
    request(`/api/p/${project}/admin/partitions/${id}/assignment`, {
      method: "PUT",
      body: JSON.stringify({ mode, user_ids: userIds }),
    }),
  setArchived: (project: string, id: string, archived: boolean) =>
    request(`/api/p/${project}/admin/partitions/${id}/archive`, {
      method: "PUT",
      body: JSON.stringify({ archived }),
    }),
};

export interface AdminUser {
  id: string;
  username: string;
  is_admin: boolean;
}

export interface AdminPartition {
  id: string;
  name: string;
  task_name: string;
  assignment: "everyone" | "selected";
  archived_at: string | null;
  item_count: number;
  assignees: string[];
  users: { id: string; username: string; answered_count: number; status: string | null; done_via: string | null }[];
}

export interface AdminPayload {
  partitions: AdminPartition[];
  users: AdminUser[];
}
