import { Badge, Box } from "@mantine/core";
import { getStatusColor, normalizeStatus } from "../../theme/status";

type StatusBadgeProps = {
  status?: string | null;
  label?: string;
  withDot?: boolean;
};

export function StatusBadge({
  status,
  label,
  withDot = false,
}: StatusBadgeProps) {
  const normalizedStatus = normalizeStatus(status);
  const color = getStatusColor(status);
  const displayLabel = label ?? (normalizedStatus || "UNKNOWN");

  return (
    <Badge
      color={color}
      style={{ maxWidth: "100%", whiteSpace: "normal" }}
      leftSection={
        withDot ? (
          <Box
            bg={`${color}.6`}
            component="span"
            h={6}
            style={{ borderRadius: "999px", display: "inline-block" }}
            w={6}
          />
        ) : undefined
      }
      variant="light"
    >
      {displayLabel}
    </Badge>
  );
}
