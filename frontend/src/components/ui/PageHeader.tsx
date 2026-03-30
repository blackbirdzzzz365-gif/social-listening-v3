import { Stack, Text, Title } from "@mantine/core";

type PageHeaderProps = {
  eyebrow: string;
  title: string;
  description?: string;
};

export function PageHeader({ eyebrow, title, description }: PageHeaderProps) {
  return (
    <Stack className="sl-page-header" gap={4}>
      <Text c="dimmed" fw={700} size="xs" style={{ letterSpacing: "0.1em" }} tt="uppercase">
        {eyebrow}
      </Text>
      <Title order={3} style={{ overflowWrap: "anywhere" }}>
        {title}
      </Title>
      {description ? (
        <Text c="dimmed" className="sl-page-header__description" size="sm">
          {description}
        </Text>
      ) : null}
    </Stack>
  );
}
