export type RuntimeMetadata = {
  app_name: string;
  display_name: string;
  app_version: string;
  current_phase: string | null;
  current_phase_number: number | null;
  current_phase_name: string | null;
  current_phase_summary: string | null;
  release_notes_href: string | null;
  release_notes_available: boolean;
};

export type ReleaseNote = {
  phase: string;
  display_name: string;
  title: string;
  summary: string;
  published_at: string | null;
  status: string | null;
  hero: {
    eyebrow?: string;
    headline?: string;
    subheadline?: string;
  };
  highlights: Array<{
    title: string;
    description: string;
  }>;
  sections: Array<{
    title: string;
    items: string[];
  }>;
  story_refs: string[];
  cta: {
    label?: string;
    href?: string;
  };
};

export type AppRoute =
  | { name: "home" }
  | { name: "release-notes"; phaseId?: string };

export function readHashRoute(hash = window.location.hash): AppRoute {
  const normalized = hash.replace(/^#/, "").trim() || "/";
  const parts = normalized.replace(/^\//, "").split("/").filter(Boolean);
  if (parts[0] === "release-notes") {
    return {
      name: "release-notes",
      phaseId: parts[1],
    };
  }
  return { name: "home" };
}

export function getBrowserSurfaceUrl(path = "/"): string {
  const normalizedPath = path.startsWith("/") ? path : `/${path}`;
  const { protocol, hostname, port } = window.location;

  if (hostname === "localhost" || hostname === "127.0.0.1") {
    return `${protocol}//${hostname}:6080${normalizedPath}`;
  }

  if (hostname.startsWith("social-listening-v3.")) {
    return `${protocol}//${hostname.replace(/^social-listening-v3\./, "live-browser.")}${normalizedPath}`;
  }

  if (port === "8000") {
    return `${protocol}//${hostname}:6080${normalizedPath}`;
  }

  return `${protocol}//${hostname}${normalizedPath}`;
}
