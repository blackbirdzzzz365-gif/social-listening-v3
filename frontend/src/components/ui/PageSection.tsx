import type { ReactNode } from "react";
import { Paper, Stack, useComputedColorScheme } from "@mantine/core";
import { semanticColors } from "../../theme/tokens";

type PageSectionProps = {
  children: ReactNode;
  sectionId?: string;
  p?: "xs" | "sm" | "md" | "lg" | "xl";
  withBorder?: boolean;
};

export function PageSection({
  children,
  sectionId,
  p = "lg",
  withBorder = true,
}: PageSectionProps) {
  const colorScheme = useComputedColorScheme("light", {
    getInitialValueInEffect: true,
  });
  const palette = colorScheme === "dark" ? semanticColors.dark : semanticColors.light;
  const responsivePadding = p === "lg" ? { base: "md", sm: "lg" } : p === "xl" ? { base: "lg", sm: "xl" } : p;

  return (
    <Paper
      className="sl-page-section"
      bg={palette.panel}
      id={sectionId}
      p={responsivePadding}
      radius="lg"
      shadow="xs"
      style={{ minHeight: "100%", overflowWrap: "anywhere" }}
      withBorder={withBorder}
    >
      <Stack gap="md">{children}</Stack>
    </Paper>
  );
}
