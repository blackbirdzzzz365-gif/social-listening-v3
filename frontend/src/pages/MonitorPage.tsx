import {
  Alert,
  Badge,
  Button,
  Code,
  Paper,
  Stack,
  Text,
  TextInput,
} from "@mantine/core";
import { useEffect, useRef, useState } from "react";
import { ActionBar } from "../components/ui/ActionBar";
import { KeyValueRow } from "../components/ui/KeyValueRow";
import { PageHeader } from "../components/ui/PageHeader";
import { PageSection } from "../components/ui/PageSection";
import { StatusBadge } from "../components/ui/StatusBadge";
import { apiUrl, fetchJson } from "../lib/api";

type StepRun = {
  step_run_id: string;
  step_id: string;
  action_type: string;
  status: string;
  actual_count: number | null;
};

type RunResponse = {
  run_id: string;
  status: string;
  total_records: number;
  steps: StepRun[];
};

type LabelSummaryResponse = {
  run_id: string;
  label_job_id: string | null;
  status: string;
  taxonomy_version: string;
  records_total: number;
  records_labeled: number;
  records_fallback: number;
  records_failed: number;
  counts_by_author_role: Record<string, number>;
  warning: string | null;
};

type MonitorPageProps = {
  initialRunId?: string;
  onRunSelected?: (runId: string) => void;
};

export function MonitorPage({ initialRunId = "", onRunSelected }: MonitorPageProps) {
  const [runId, setRunId] = useState("");
  const [run, setRun] = useState<RunResponse | null>(null);
  const [events, setEvents] = useState<string[]>([]);
  const [streamStatus, setStreamStatus] = useState("idle");
  const [statusMessage, setStatusMessage] = useState("");
  const [error, setError] = useState("");
  const [isControlling, setIsControlling] = useState(false);
  const [labelSummary, setLabelSummary] = useState<LabelSummaryResponse | null>(null);
  const [labelError, setLabelError] = useState("");
  const [labelStatusMessage, setLabelStatusMessage] = useState("");
  const [isLabelLoading, setIsLabelLoading] = useState(false);
  const [isStartingLabeling, setIsStartingLabeling] = useState(false);
  const sourceRef = useRef<EventSource | null>(null);

  const refreshRun = async (targetRunId = runId) => {
    if (!targetRunId) return;
    try {
      const payload = await fetchJson<RunResponse>(`/api/runs/${targetRunId}`);
      setRun(payload);
      void refreshLabelSummary(targetRunId);
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : "Refresh run failed");
    }
  };

  const refreshLabelSummary = async (targetRunId = runId) => {
    if (!targetRunId) return;
    setIsLabelLoading(true);
    setLabelError("");
    try {
      const payload = await fetchJson<LabelSummaryResponse>(`/api/runs/${targetRunId}/labels/summary`);
      setLabelSummary(payload);
      setLabelStatusMessage(
        payload.label_job_id
          ? `Label job ${payload.label_job_id} is ${payload.status.toLowerCase()}.`
          : "No label job has started for this run yet."
      );
    } catch (requestError) {
      setLabelSummary(null);
      setLabelError(requestError instanceof Error ? requestError.message : "Refresh labeling failed");
    } finally {
      setIsLabelLoading(false);
    }
  };

  useEffect(() => {
    return () => {
      sourceRef.current?.close();
      sourceRef.current = null;
    };
  }, []);

  useEffect(() => {
    if (!runId.trim()) {
      return;
    }
    if (!labelSummary || !["RUNNING", "PENDING"].includes(labelSummary.status)) {
      return;
    }
    const handle = window.setInterval(() => {
      void refreshLabelSummary(runId);
    }, 3000);
    return () => window.clearInterval(handle);
  }, [runId, labelSummary?.status]);

  useEffect(() => {
    if (!initialRunId || initialRunId === runId) {
      return;
    }
    setRunId(initialRunId);
    setStatusMessage(`Run received from approval flow: ${initialRunId}`);
    onRunSelected?.(initialRunId);
    void connectStream(initialRunId);
    void refreshLabelSummary(initialRunId);
  }, [initialRunId]);

  const connectStream = async (targetRunId = runId) => {
    const normalizedRunId = targetRunId.trim();
    if (!normalizedRunId) return;
    onRunSelected?.(normalizedRunId);
    sourceRef.current?.close();
    sourceRef.current = null;
    setEvents([]);
    setError("");
    setStreamStatus("connecting");
    setStatusMessage(`Connecting stream for ${normalizedRunId}...`);
    const source = new EventSource(apiUrl(`/api/runs/${normalizedRunId}/stream`));
    const knownEvents = [
      "run_started",
      "step_started",
      "step_done",
      "step_failed",
      "run_paused",
      "run_resumed",
      "run_done",
      "run_failed",
      "run_cancelled",
      "stream_complete",
    ];
    source.onopen = () => {
      setStreamStatus("connected");
      setStatusMessage(`Stream connected for ${normalizedRunId}.`);
    };
    knownEvents.forEach((eventName) => {
      source.addEventListener(eventName, (event) => {
        setEvents((current) => [...current.slice(-7), `${eventName}: ${event.data}`]);
        if (eventName === "run_done" || eventName === "run_failed" || eventName === "run_cancelled") {
          setStreamStatus("complete");
          setStatusMessage(`Run reached terminal status via ${eventName} for ${normalizedRunId}.`);
          source.close();
          sourceRef.current = null;
        } else if (eventName === "stream_complete") {
          setStreamStatus("complete");
          setStatusMessage(`Stream complete for ${normalizedRunId}.`);
          source.close();
          sourceRef.current = null;
        }
        void refreshRun(normalizedRunId);
      });
    });
    source.onerror = () => {
      setEvents((current) => [...current.slice(-7), "stream: disconnected"]);
      if (sourceRef.current === source) {
        setStreamStatus("disconnected");
        setStatusMessage(`Stream disconnected for ${normalizedRunId}.`);
        source.close();
        sourceRef.current = null;
      }
    };
    sourceRef.current = source;
    await refreshRun(normalizedRunId);
  };

  const controlRun = async (action: "pause" | "resume" | "stop") => {
    if (!runId) return;
    setIsControlling(true);
    setError("");
    try {
      const payload = await fetchJson<RunResponse>(`/api/runs/${runId}/${action}`, { method: "POST" });
      setRun(payload);
      setEvents((current) => [...current.slice(-7), `control_${action}: accepted`]);
      setStatusMessage(`${action} command accepted for ${runId}.`);
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : `${action} failed`);
    } finally {
      setIsControlling(false);
    }
  };

  const startLabeling = async () => {
    if (!runId.trim()) return;
    setIsStartingLabeling(true);
    setLabelError("");
    try {
      const payload = await fetchJson<LabelSummaryResponse>(`/api/runs/${runId}/labels/jobs`, { method: "POST" });
      setLabelSummary(payload);
      setLabelStatusMessage(
        payload.label_job_id
          ? `Labeling accepted for ${runId}. Job ${payload.label_job_id} is ${payload.status.toLowerCase()}.`
          : `Labeling accepted for ${runId}.`
      );
    } catch (requestError) {
      setLabelError(requestError instanceof Error ? requestError.message : "Start labeling failed");
    } finally {
      setIsStartingLabeling(false);
    }
  };

  return (
    <PageSection>
      <PageHeader
        description="Realtime execution stream, run controls, and labeling progress in one shell panel."
        eyebrow="Monitor"
        title="Realtime execution monitor with stream updates."
      />
      <Stack gap="sm">
        <TextInput
          onChange={(event) => setRunId(event.target.value)}
          placeholder="Enter run_id"
          value={runId}
        />
        <ActionBar>
          <Button onClick={() => void connectStream()} disabled={!runId.trim() || streamStatus === "connecting"}>
            {streamStatus === "connecting"
              ? "Connecting..."
              : streamStatus === "connected"
                ? "Reconnect Stream"
                : "Connect Stream"}
          </Button>
          <Button onClick={() => void controlRun("pause")} disabled={!runId.trim() || isControlling || !run} variant="light">
            Pause
          </Button>
          <Button onClick={() => void controlRun("resume")} disabled={!runId.trim() || isControlling || !run} variant="light">
            Resume
          </Button>
          <Button onClick={() => void controlRun("stop")} disabled={!runId.trim() || isControlling || !run} variant="light">
            {isControlling ? "Sending..." : "Stop"}
          </Button>
          <Button
            onClick={() => void startLabeling()}
            disabled={!runId.trim() || isStartingLabeling}
            variant="light"
          >
            {isStartingLabeling ? "Starting Labeling..." : "Start Labeling"}
          </Button>
          <Button
            onClick={() => void refreshLabelSummary()}
            disabled={!runId.trim() || isLabelLoading}
            variant="light"
          >
            {isLabelLoading ? "Refreshing Labels..." : "Refresh Labels"}
          </Button>
        </ActionBar>
        {error ? (
          <Alert color="red" variant="light">
            {error}
          </Alert>
        ) : null}
        {labelError ? (
          <Alert color="red" variant="light">
            {labelError}
          </Alert>
        ) : null}
        {runId ? <KeyValueRow label="run_id" mono value={runId} /> : null}
        <StatusBadge label={`Stream ${streamStatus}`} status={streamStatus} />
        {statusMessage ? <Text size="sm">monitor: {statusMessage}</Text> : null}
        {run ? (
          <Stack gap="sm">
            <StatusBadge label={`Run ${run.status}`} status={run.status} />
            <KeyValueRow label="records" value={run.total_records} />
            {run.steps.map((step) => (
              <Paper key={step.step_run_id} p="sm" radius="md" withBorder>
                <Stack gap={6}>
                  <Text fw={700} size="sm">
                    {step.step_id} · {step.action_type}
                  </Text>
                  <StatusBadge label={`Step ${step.status}`} status={step.status} />
                  <KeyValueRow label="actual count" value={step.actual_count ?? 0} />
                </Stack>
              </Paper>
            ))}
            <Paper p="sm" radius="md" withBorder>
              <Code block className="sl-code-block">
                {events.join("\n") || "No events yet."}
              </Code>
            </Paper>
          </Stack>
        ) : null}
        {labelSummary ? (
          <Paper p="sm" radius="md" withBorder>
            <Stack gap="sm">
              <StatusBadge label={`Labeling ${labelSummary.status}`} status={labelSummary.status} />
              <KeyValueRow label="taxonomy" value={labelSummary.taxonomy_version} />
              <KeyValueRow
                label="labeled"
                value={`${labelSummary.records_labeled}/${labelSummary.records_total}`}
              />
              <KeyValueRow label="fallback" value={labelSummary.records_fallback} />
              <KeyValueRow label="failed" value={labelSummary.records_failed} />
              {labelStatusMessage ? <Text size="sm">labels: {labelStatusMessage}</Text> : null}
              {labelSummary.warning ? (
                <Alert color="yellow" variant="light">
                  {labelSummary.warning}
                </Alert>
              ) : null}
              <Stack gap="xs">
                {Object.entries(labelSummary.counts_by_author_role).map(([role, count]) => (
                  <Badge key={role} variant="light">
                    {role}: {count}
                  </Badge>
                ))}
              </Stack>
            </Stack>
          </Paper>
        ) : null}
      </Stack>
    </PageSection>
  );
}
