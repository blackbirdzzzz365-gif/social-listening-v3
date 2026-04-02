import { Button, Code, Group, Stack, Text } from "@mantine/core";
import { useEffect, useState } from "react";
import { ActionBar } from "../components/ui/ActionBar";
import { KeyValueRow } from "../components/ui/KeyValueRow";
import { PageHeader } from "../components/ui/PageHeader";
import { PageSection } from "../components/ui/PageSection";
import { StatusBadge } from "../components/ui/StatusBadge";
import { apiUrl } from "../lib/api";
import { getBrowserSurfaceUrl } from "../lib/runtime";

type BrowserStatus = {
  session_status: "NOT_SETUP" | "VALID" | "EXPIRED";
  account_id_hash: string | null;
  health_status: "HEALTHY" | "CAUTION" | "BLOCKED";
  cooldown_until: string | null;
  last_checked: string | null;
  runnable: boolean;
  action_required: string | null;
  block_reason: string | null;
};

const initialStatus: BrowserStatus = {
  session_status: "NOT_SETUP",
  account_id_hash: null,
  health_status: "HEALTHY",
  cooldown_until: null,
  last_checked: null,
  runnable: false,
  action_required: "CONNECT_FACEBOOK",
  block_reason: "session_not_setup",
};

export function SetupPage() {
  const [status, setStatus] = useState<BrowserStatus>(initialStatus);
  const [isConnecting, setIsConnecting] = useState(false);
  const [message, setMessage] = useState("SetupPage is ready to connect Facebook.");

  useEffect(() => {
    let cancelled = false;
    let source: EventSource | null = null;

    const loadStatus = async () => {
      try {
        const response = await fetch(apiUrl("/api/browser/status"));
        if (!response.ok || cancelled) {
          return;
        }
        const payload = (await response.json()) as BrowserStatus;
        setStatus(payload);
        if (payload.session_status === "VALID") {
          setMessage(payload.runnable ? "Da ket noi — san sang." : "Session hop le nhung dang bi block boi health runtime.");
          setIsConnecting(false);
          return;
        }
        if (payload.session_status === "EXPIRED") {
          setMessage("Session het han. Hay ket noi lai Facebook truoc khi chay run moi.");
          setIsConnecting(false);
          return;
        }
        if (payload.action_required === "CONNECT_FACEBOOK") {
          setMessage("Chua co session Facebook. Hay ket noi tai day truoc.");
          setIsConnecting(false);
          return;
        }
        setMessage("SetupPage is ready to connect Facebook.");
      } catch {
        if (!cancelled) {
          setStatus(initialStatus);
          setMessage("Khong tai duoc browser status.");
          setIsConnecting(false);
        }
      }
    };

    const connectStream = () => {
      source = new EventSource(apiUrl("/api/browser/setup/stream"));
      source.addEventListener("browser_opened", () => {
        setMessage("Browser opened. Please connect Facebook.");
      });
      source.addEventListener("login_detected", (event) => {
        const payload = JSON.parse((event as MessageEvent).data) as {
          account_id_hash: string;
        };
        setMessage(`Login detected. account_id_hash=${payload.account_id_hash.slice(0, 8)}...`);
      });
      source.addEventListener("setup_complete", () => {
        setIsConnecting(false);
        setMessage("Da ket noi — san sang.");
        void loadStatus();
      });
      source.addEventListener("setup_failed", (event) => {
        setIsConnecting(false);
        setMessage(`Setup failed: ${(event as MessageEvent).data}`);
      });
    };

    void loadStatus();
    connectStream();
    const intervalId = window.setInterval(() => {
      void loadStatus();
    }, 5000);

    return () => {
      cancelled = true;
      window.clearInterval(intervalId);
      source?.close();
    };
  }, []);

  const onConnect = async () => {
    setIsConnecting(true);
    setMessage("Dang khoi dong setup flow...");
    await fetch(apiUrl("/api/browser/setup"), { method: "POST" });
  };

  return (
    <PageSection>
      <PageHeader
        description="One-time Facebook connect flow with reusable browser session."
        eyebrow="Setup"
        title="Ket noi Facebook 1 lan, reuse session ve sau."
      />
      <Stack gap="sm">
        <Group gap="xs" wrap="wrap">
          <StatusBadge label={`Session ${status.session_status}`} status={status.session_status} />
          <StatusBadge label={`Health ${status.health_status}`} status={status.health_status} />
          <StatusBadge label={`Runnable ${status.runnable ? "READY" : "BLOCKED"}`} status={status.runnable ? "READY" : "BLOCKED"} />
          {status.action_required ? <StatusBadge label={`Action ${status.action_required}`} status={status.action_required} /> : null}
        </Group>
        <Text size="sm">{message}</Text>
        {status.last_checked ? <KeyValueRow label="Last checked" value={status.last_checked} /> : null}
        {status.block_reason ? <KeyValueRow label="Block reason" value={status.block_reason} /> : null}
        {status.cooldown_until ? (
          <KeyValueRow label="Cooldown until" mono value={status.cooldown_until} />
        ) : null}
        {status.session_status !== "VALID" ? (
          <ActionBar>
            <Button disabled={isConnecting} onClick={onConnect}>
              {isConnecting ? "Dang ket noi..." : "Ket noi Facebook"}
            </Button>
            <Button component="a" href={getBrowserSurfaceUrl("/")} rel="noreferrer" target="_blank" variant="light">
              Mo Browser Web
            </Button>
          </ActionBar>
        ) : (
          <Stack gap="sm">
            <KeyValueRow
              label="Connected hash"
              value={status.account_id_hash ? <Code>{status.account_id_hash}</Code> : <Code>unknown</Code>}
            />
            <ActionBar>
              <Button component="a" href={getBrowserSurfaceUrl("/")} rel="noreferrer" target="_blank" variant="light">
                Mo Browser Web
              </Button>
            </ActionBar>
          </Stack>
        )}
      </Stack>
    </PageSection>
  );
}
