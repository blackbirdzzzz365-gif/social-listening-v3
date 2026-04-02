import { Alert, List, Stack, Text } from "@mantine/core";

export type RuntimeReadiness = {
  runnable: boolean;
  session_status: string;
  health_status: string;
  action_required?: string | null;
  block_reason?: string | null;
  last_checked?: string | null;
  summary: string;
  next_steps: string[];
};

type RuntimeReadinessPanelProps = {
  readiness: RuntimeReadiness | null;
};

export function RuntimeReadinessPanel({ readiness }: RuntimeReadinessPanelProps) {
  if (!readiness) {
    return null;
  }

  const color = readiness.runnable ? "green" : readiness.action_required === "WAIT_COOLDOWN" ? "yellow" : "orange";

  return (
    <Alert color={color} title="Research runtime readiness" variant="light">
      <Stack gap={6}>
        <Text size="sm">{readiness.summary}</Text>
        <Text c="dimmed" size="sm">
          session {readiness.session_status} · health {readiness.health_status}
          {readiness.action_required ? ` · action ${readiness.action_required}` : ""}
        </Text>
        {readiness.last_checked ? (
          <Text c="dimmed" size="xs">
            last checked: {readiness.last_checked}
          </Text>
        ) : null}
        {readiness.next_steps.length ? (
          <List size="sm" spacing={4}>
            {readiness.next_steps.map((step) => (
              <List.Item key={step}>{step}</List.Item>
            ))}
          </List>
        ) : null}
      </Stack>
    </Alert>
  );
}
