import { useEffect, useState } from "react";
import {
  Badge,
  Button,
  Group,
  List,
  Paper,
  SimpleGrid,
  Skeleton,
  Stack,
  Text,
  ThemeIcon,
  Title,
  useComputedColorScheme,
} from "@mantine/core";
import { fetchJson } from "../lib/api";
import type { ReleaseNote } from "../lib/runtime";
import { semanticColors } from "../theme/tokens";
import { PageSection } from "../components/ui/PageSection";

type ReleaseNotesPageProps = {
  phaseId?: string;
};

export function ReleaseNotesPage({ phaseId }: ReleaseNotesPageProps) {
  const [releaseNote, setReleaseNote] = useState<ReleaseNote | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const colorScheme = useComputedColorScheme("light", {
    getInitialValueInEffect: true,
  });
  const palette = colorScheme === "dark" ? semanticColors.dark : semanticColors.light;

  useEffect(() => {
    let cancelled = false;

    async function loadReleaseNote() {
      setIsLoading(true);
      setError(null);
      try {
        const path = phaseId ? `/api/runtime/release-notes/${phaseId}` : "/api/runtime/release-notes/current";
        const payload = await fetchJson<ReleaseNote>(path);
        if (!cancelled) {
          setReleaseNote(payload);
        }
      } catch (loadError) {
        if (!cancelled) {
          setReleaseNote(null);
          setError(loadError instanceof Error ? loadError.message : "Unable to load release notes");
        }
      } finally {
        if (!cancelled) {
          setIsLoading(false);
        }
      }
    }

    void loadReleaseNote();
    return () => {
      cancelled = true;
    };
  }, [phaseId]);

  if (isLoading) {
    return (
      <Stack gap="lg">
        <Skeleton height={220} radius="xl" />
        <SimpleGrid cols={{ base: 1, md: 2 }}>
          <Skeleton height={180} radius="xl" />
          <Skeleton height={180} radius="xl" />
        </SimpleGrid>
      </Stack>
    );
  }

  if (error || !releaseNote) {
    return (
      <PageSection>
        <Stack gap="sm">
          <Badge color="red" variant="light" w="fit-content">
            Release notes unavailable
          </Badge>
          <Title order={2}>Khong tai duoc release note</Title>
          <Text c="dimmed" maw={640}>
            {error ?? "Phase nay chua co release note duoc publish."}
          </Text>
          <Button component="a" href="#/" variant="light" w="fit-content">
            Quay lai workflow
          </Button>
        </Stack>
      </PageSection>
    );
  }

  return (
    <Stack gap="lg">
      <Paper
        p={{ base: "lg", sm: "xl" }}
        radius="xl"
        style={{
          background: colorScheme === "dark"
            ? "linear-gradient(135deg, rgba(61,95,125,0.28), rgba(26,27,30,0.96))"
            : "linear-gradient(135deg, rgba(238,243,248,0.98), rgba(255,255,255,0.98))",
          border: `1px solid ${palette.border}`,
        }}
        withBorder
      >
        <Stack gap="lg">
          <SimpleGrid cols={{ base: 1, lg: 2 }} spacing="lg">
            <Stack gap="md" maw={780}>
              <Badge radius="sm" size="lg" variant="light" w="fit-content">
                {releaseNote.hero.eyebrow ?? "Release Notes"}
              </Badge>
              <Title order={1}>{releaseNote.hero.headline ?? releaseNote.title}</Title>
              <Text c="dimmed" size="lg">
                {releaseNote.hero.subheadline ?? releaseNote.summary}
              </Text>
            </Stack>

            <PageSection p="md">
              <Stack gap="xs">
                <Text c="dimmed" fw={700} size="xs" tt="uppercase">
                  Build Snapshot
                </Text>
                <Text fw={700} size="lg">
                  {releaseNote.display_name}
                </Text>
                {releaseNote.published_at ? <Text size="sm">Published {releaseNote.published_at}</Text> : null}
                {releaseNote.status ? (
                  <Badge color="blue" radius="sm" variant="light" w="fit-content">
                    {releaseNote.status}
                  </Badge>
                ) : null}
              </Stack>
            </PageSection>
          </SimpleGrid>

          <Group gap="xs">
            {releaseNote.story_refs.map((storyRef) => (
              <Badge key={storyRef} radius="sm" variant="outline">
                {storyRef}
              </Badge>
            ))}
          </Group>
        </Stack>
      </Paper>

      <SimpleGrid cols={{ base: 1, md: 2 }}>
        {releaseNote.highlights.map((highlight) => (
          <PageSection key={highlight.title}>
            <Stack gap="sm">
              <ThemeIcon color="blue" radius="md" size={40} variant="light">
                {highlight.title.slice(0, 1).toUpperCase()}
              </ThemeIcon>
              <Title order={3}>{highlight.title}</Title>
              <Text c="dimmed">{highlight.description}</Text>
            </Stack>
          </PageSection>
        ))}
      </SimpleGrid>

      <SimpleGrid cols={{ base: 1, lg: 3 }}>
        {releaseNote.sections.map((section) => (
          <PageSection key={section.title}>
            <Stack gap="sm">
              <Title order={3}>{section.title}</Title>
              <List
                spacing="sm"
                icon={
                  <ThemeIcon color="blue" radius="xl" size={20} variant="light">
                    •
                  </ThemeIcon>
                }
              >
                {section.items.map((item) => (
                  <List.Item key={item}>
                    <Text>{item}</Text>
                  </List.Item>
                ))}
              </List>
            </Stack>
          </PageSection>
        ))}
      </SimpleGrid>

      <PageSection>
        <Stack gap="md">
          <Stack gap={4}>
            <Text fw={700}>Ready to continue?</Text>
            <Text c="dimmed" size="sm">
              Release notes da duoc attach vao phase hien hanh. Ban co the quay lai workflow ngay bay gio.
            </Text>
          </Stack>
          <Button component="a" href={releaseNote.cta.href || "#/"} w={{ base: "100%", xs: "fit-content" }}>
            {releaseNote.cta.label || "Open workflow"}
          </Button>
        </Stack>
      </PageSection>
    </Stack>
  );
}
