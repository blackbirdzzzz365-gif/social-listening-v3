import type { ReactNode } from "react";
import {
  AppShell,
  Container,
  useComputedColorScheme,
} from "@mantine/core";
import { semanticColors } from "../../theme/tokens";
import { AppHeader } from "./AppHeader";

type AppLayoutProps = {
  children: ReactNode;
  displayName: string;
  currentPhaseName?: string | null;
  releaseNotesHref?: string | null;
};

export function AppLayout({
  children,
  displayName,
  currentPhaseName,
  releaseNotesHref,
}: AppLayoutProps) {
  const colorScheme = useComputedColorScheme("light", {
    getInitialValueInEffect: true,
  });
  const palette = colorScheme === "dark" ? semanticColors.dark : semanticColors.light;

  return (
    <AppShell
      header={{ height: { base: 118, sm: 84 } }}
      padding={{ base: "xs", sm: "md" }}
      styles={{
        header: {
          backgroundColor: palette.panel,
          borderColor: palette.border,
        },
        main: {
          backgroundColor: palette.app,
          color: palette.textPrimary,
          minHeight: "100vh",
        },
      }}
    >
      <AppShell.Header>
        <AppHeader
          currentPhaseName={currentPhaseName}
          displayName={displayName}
          releaseNotesHref={releaseNotesHref}
        />
      </AppShell.Header>
      <AppShell.Main>
        <Container px={{ base: 0, xs: "xs", sm: "md" }} py={{ base: "md", sm: "lg" }} size="xl">
          {children}
        </Container>
      </AppShell.Main>
    </AppShell>
  );
}
