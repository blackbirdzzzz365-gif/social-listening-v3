import type { ReactNode } from "react";
import { Box, Text } from "@mantine/core";

type KeyValueRowProps = {
  label: string;
  value: ReactNode;
  mono?: boolean;
};

export function KeyValueRow({ label, value, mono = false }: KeyValueRowProps) {
  return (
    <Box className="sl-key-value-row">
      <Text c="dimmed" fw={600} size="sm">
        {label}:
      </Text>
      <Box
        className="sl-key-value-value"
        style={{
          fontFamily: mono ? "var(--mantine-font-family-monospace)" : undefined,
        }}
      >
        {value}
      </Box>
    </Box>
  );
}
