import { Box, Button, SimpleGrid, Stack, Text } from "@mantine/core";
import { useEffect, useState } from "react";
import { AppLayout } from "./app/shell/AppLayout";
import { HealthBadge } from "./components/HealthBadge";
import { PageSection } from "./components/ui/PageSection";
import { fetchJson } from "./lib/api";
import { readHashRoute, type AppRoute, type RuntimeMetadata } from "./lib/runtime";
import { ApprovePage } from "./pages/ApprovePage";
import { KeywordPage } from "./pages/KeywordPage";
import { MonitorPage } from "./pages/MonitorPage";
import { PlanPage } from "./pages/PlanPage";
import { ReleaseNotesPage } from "./pages/ReleaseNotesPage";
import { SetupPage } from "./pages/SetupPage";
import { ThemesPage } from "./pages/ThemesPage";

export default function App() {
  const [activeContextId, setActiveContextId] = useState("");
  const [activePlanId, setActivePlanId] = useState("");
  const [activeRunId, setActiveRunId] = useState("");
  const [route, setRoute] = useState<AppRoute>(() => readHashRoute());
  const [runtimeMetadata, setRuntimeMetadata] = useState<RuntimeMetadata | null>(null);

  const handleContextReady = (contextId: string) => {
    setActiveContextId(contextId);
    setActivePlanId("");
    setActiveRunId("");
  };

  const handlePlanReady = (planId: string) => {
    setActivePlanId(planId);
    setActiveRunId("");
  };

  const handleRunReady = (runId: string) => {
    setActiveRunId(runId);
  };

  useEffect(() => {
    const handleHashChange = () => setRoute(readHashRoute());
    window.addEventListener("hashchange", handleHashChange);
    return () => window.removeEventListener("hashchange", handleHashChange);
  }, []);

  useEffect(() => {
    let cancelled = false;

    async function loadRuntimeMetadata() {
      try {
        const payload = await fetchJson<RuntimeMetadata>("/api/runtime/metadata");
        if (!cancelled) {
          setRuntimeMetadata(payload);
        }
      } catch {
        if (!cancelled) {
          setRuntimeMetadata(null);
        }
      }
    }

    void loadRuntimeMetadata();
    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => {
    const displayName = runtimeMetadata?.display_name ?? "Social Listening v3";
    document.title = route.name === "release-notes" ? `${displayName} Release Notes` : displayName;
  }, [route.name, runtimeMetadata?.display_name]);

  const sectionLinks = [
    { label: "Setup", target: "workflow-setup" },
    { label: "Health", target: "workflow-health" },
    { label: "Keywords", target: "workflow-keywords" },
    { label: "Plan", target: "workflow-plan" },
    { label: "Approve", target: "workflow-approve" },
    { label: "Monitor", target: "workflow-monitor" },
    { label: "Themes", target: "workflow-themes" },
  ];

  const scrollToSection = (target: string) => {
    document.getElementById(target)?.scrollIntoView({ behavior: "smooth", block: "start" });
  };

  return (
    <AppLayout
      currentPhaseName={runtimeMetadata?.current_phase_name}
      displayName={runtimeMetadata?.display_name ?? "Social Listening v3"}
      releaseNotesHref={runtimeMetadata?.release_notes_href}
    >
      {route.name === "release-notes" ? (
        <ReleaseNotesPage phaseId={route.phaseId ?? runtimeMetadata?.current_phase ?? undefined} />
      ) : (
        <Stack gap="lg">
          <PageSection p="md">
            <Stack gap="xs">
              <Text c="dimmed" size="sm">
                Jump quickly between the main web surfaces on small screens.
              </Text>
              <div className="sl-mobile-nav-grid">
                {sectionLinks.map((section) => (
                  <Button
                    key={section.target}
                    onClick={() => scrollToSection(section.target)}
                    size="compact-sm"
                    variant="light"
                  >
                    {section.label}
                  </Button>
                ))}
              </div>
            </Stack>
          </PageSection>

          <SimpleGrid cols={{ base: 1, sm: 2 }}>
            <Box id="workflow-setup">
              <SetupPage />
            </Box>
            <Box id="workflow-health">
              <HealthBadge />
            </Box>
          </SimpleGrid>

          <SimpleGrid cols={{ base: 1, md: 2 }}>
            <Box id="workflow-keywords">
              <KeywordPage onContextReady={handleContextReady} />
            </Box>
            <Box id="workflow-plan">
              <PlanPage initialContextId={activeContextId} onPlanReady={handlePlanReady} />
            </Box>
            <Box id="workflow-approve">
              <ApprovePage initialPlanId={activePlanId} onRunReady={handleRunReady} />
            </Box>
            <Box id="workflow-monitor">
              <MonitorPage initialRunId={activeRunId} onRunSelected={handleRunReady} />
            </Box>
            <Box id="workflow-themes">
              <ThemesPage initialRunId={activeRunId} />
            </Box>
          </SimpleGrid>
        </Stack>
      )}
    </AppLayout>
  );
}
