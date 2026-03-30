import type { ReactNode } from "react";
import { Children } from "react";
import { Box } from "@mantine/core";

type ActionBarProps = {
  children: ReactNode;
};

export function ActionBar({ children }: ActionBarProps) {
  const items = Children.toArray(children).filter(Boolean);

  return (
    <Box className="sl-action-bar">
      {items.map((child, index) => (
        <Box className="sl-action-item" key={index}>
          {child}
        </Box>
      ))}
    </Box>
  );
}
