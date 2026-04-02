import type { MantineColor } from "@mantine/core";

export type StatusLevel = "success" | "warning" | "danger" | "info" | "neutral";

export const STATUS_MAP: Record<string, StatusLevel> = {
  HEALTHY: "success",
  CAUTION: "warning",
  BLOCKED: "danger",
  VALID: "success",
  NOT_SETUP: "neutral",
  EXPIRED: "danger",
  RUNNING: "info",
  QUEUED: "warning",
  CANCELLING: "warning",
  DONE: "success",
  FAILED: "danger",
  PENDING: "neutral",
  COMPLETED: "success",
  PAUSED: "warning",
  CANCELLED: "neutral",
  ANSWER_READY: "success",
  NO_ELIGIBLE_RECORDS: "neutral",
  NO_ANSWER_CONTENT: "warning",
  REAUTH_REQUIRED: "warning",
  AUTH_SESSION_EXPIRED: "danger",
  AUTH_SESSION_UNAVAILABLE: "warning",
  CONNECT_FACEBOOK: "warning",
  WAIT_COOLDOWN: "warning",
  MANUAL_RESET_REQUIRED: "warning",
  READY: "success",
  INFRA_BROWSER_BOOT_FAILURE: "danger",
  STEP_STUCK_TIMEOUT: "danger",
  IDLE: "neutral",
  CONNECTING: "info",
  CONNECTED: "success",
  COMPLETE: "neutral",
  DISCONNECTED: "warning",
  POSITIVE: "success",
  NEGATIVE: "danger",
  NEUTRAL: "neutral",
  READ: "info",
  WRITE: "danger",
};

const STATUS_COLORS: Record<StatusLevel, MantineColor> = {
  success: "green",
  warning: "yellow",
  danger: "red",
  info: "blue",
  neutral: "gray",
};

export function normalizeStatus(status?: string | null): string {
  return status?.trim().toUpperCase() ?? "";
}

export function getStatusLevel(status?: string | null): StatusLevel {
  return STATUS_MAP[normalizeStatus(status)] ?? "neutral";
}

export function getStatusColor(status?: string | null): MantineColor {
  return STATUS_COLORS[getStatusLevel(status)];
}
