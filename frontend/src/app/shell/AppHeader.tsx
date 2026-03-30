import {
  ActionIcon,
  Badge,
  Button,
  Container,
  Group,
  Stack,
  Text,
  useComputedColorScheme,
  useMantineColorScheme,
} from "@mantine/core";
import { apiUrl } from "../../lib/api";
import { getBrowserSurfaceUrl } from "../../lib/runtime";

type AppHeaderProps = {
  displayName: string;
  currentPhaseName?: string | null;
  releaseNotesHref?: string | null;
};

export function AppHeader({ displayName, currentPhaseName, releaseNotesHref }: AppHeaderProps) {
  const { setColorScheme } = useMantineColorScheme();
  const colorScheme = useComputedColorScheme("light", {
    getInitialValueInEffect: true,
  });
  const nextColorScheme = colorScheme === "dark" ? "light" : "dark";
  const links = [
    { label: "Browser Web", href: getBrowserSurfaceUrl("/") },
    { label: "Browser API", href: apiUrl("/api/browser/status") },
    { label: "Health API", href: apiUrl("/api/health/status") },
    { label: "Sessions API", href: apiUrl("/api/sessions") },
    { label: "Runs API", href: apiUrl("/api/runs") },
  ];

  return (
    <Container
      className="sl-shell-header"
      h="100%"
      size="xl"
    >
      <div className="sl-shell-header__row">
        <Button component="a" href="#/" px={0} styles={{ root: { height: "auto" } }} variant="subtle">
          <Stack className="sl-shell-brand" gap={2}>
            <Text fw={700} size="sm">
              {displayName}
            </Text>
            {currentPhaseName ? (
              <Text c="dimmed" size="xs">
                {currentPhaseName}
              </Text>
            ) : null}
          </Stack>
        </Button>

        <Group gap="xs" justify="flex-end" wrap="wrap">
          {currentPhaseName ? (
            <Badge radius="sm" variant="light">
              {currentPhaseName}
            </Badge>
          ) : null}
          {releaseNotesHref ? (
            <Button component="a" href={releaseNotesHref} size="compact-sm" variant="light">
              Release Notes
            </Button>
          ) : null}
          <ActionIcon
            aria-label={`Switch to ${nextColorScheme} mode`}
            onClick={() => setColorScheme(nextColorScheme)}
            size="lg"
            variant="default"
          >
            {colorScheme === "dark" ? "L" : "D"}
          </ActionIcon>
        </Group>
      </div>

      <div className="sl-shell-header__links">
        {links.map((link) => (
          <Button
            component="a"
            href={link.href}
            key={link.href}
            rel="noreferrer"
            size="compact-sm"
            target={link.href.startsWith("http") ? "_blank" : "_self"}
            variant={link.label === "Browser Web" ? "light" : "subtle"}
          >
            {link.label}
          </Button>
        ))}
      </div>
    </Container>
  );
}
