import {
  Alert,
  Button,
  Paper,
  Stack,
  Text,
  TextInput,
  Textarea,
} from "@mantine/core";
import { useEffect, useState } from "react";
import { RuntimeReadiness, RuntimeReadinessPanel } from "../components/research/RuntimeReadinessPanel";
import { ActionBar } from "../components/ui/ActionBar";
import { KeyValueRow } from "../components/ui/KeyValueRow";
import { PageHeader } from "../components/ui/PageHeader";
import { PageSection } from "../components/ui/PageSection";
import { StatusBadge } from "../components/ui/StatusBadge";
import { fetchJson } from "../lib/api";

type KeywordMap = {
  brand: string[];
  pain_points: string[];
  sentiment: string[];
  behavior: string[];
  comparison: string[];
};

const emptyKeywords: KeywordMap = {
  brand: [],
  pain_points: [],
  sentiment: [],
  behavior: [],
  comparison: [],
};

type SessionResponse = {
  context_id: string;
  topic: string;
  status: string;
  clarifying_questions: string[] | null;
  keywords: KeywordMap | null;
  clarification_history: { question: string; answer: string }[];
  runtime_readiness?: RuntimeReadiness | null;
};

type KeywordPageProps = {
  onContextReady?: (contextId: string) => void;
};

export function KeywordPage({ onContextReady }: KeywordPageProps) {
  const [topic, setTopic] = useState("Khach hang nghi gi ve TPBank EVO?");
  const [resumeContextId, setResumeContextId] = useState("");
  const [contextId, setContextId] = useState("");
  const [status, setStatus] = useState("");
  const [keywords, setKeywords] = useState<KeywordMap>(emptyKeywords);
  const [questions, setQuestions] = useState<string[]>([]);
  const [answers, setAnswers] = useState<string[]>([]);
  const [clarificationHistory, setClarificationHistory] = useState<{ question: string; answer: string }[]>([]);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [isLoadingContext, setIsLoadingContext] = useState(false);
  const [isSubmittingClarification, setIsSubmittingClarification] = useState(false);
  const [error, setError] = useState("");
  const [statusMessage, setStatusMessage] = useState("");
  const [runtimeReadiness, setRuntimeReadiness] = useState<RuntimeReadiness | null>(null);

  const refreshRuntimeReadiness = async () => {
    try {
      const payload = await fetchJson<RuntimeReadiness>("/api/browser/status");
      setRuntimeReadiness(payload);
    } catch {
      setRuntimeReadiness(null);
    }
  };

  useEffect(() => {
    void refreshRuntimeReadiness();
  }, []);

  const applySession = (payload: SessionResponse) => {
    setTopic(payload.topic);
    setResumeContextId(payload.context_id);
    setContextId(payload.context_id);
    setStatus(payload.status);
    setQuestions(payload.clarifying_questions ?? []);
    setAnswers((payload.clarifying_questions ?? []).map(() => ""));
    setKeywords(payload.keywords ?? emptyKeywords);
    setClarificationHistory(payload.clarification_history ?? []);
    setRuntimeReadiness(payload.runtime_readiness ?? null);
    onContextReady?.(payload.context_id);
  };

  const submit = async () => {
    setIsSubmitting(true);
    setError("");
    setStatusMessage("Analyzing topic...");
    try {
      const payload = await fetchJson<SessionResponse>("/api/sessions", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ topic }),
      });
      applySession(payload);
      setStatusMessage(
        payload.status === "clarification_required"
          ? "Clarification required. Answer the questions below to continue."
          : "Keywords ready."
      );
    } catch (requestError) {
      setContextId("");
      setStatus("");
      setQuestions([]);
      setAnswers([]);
      setKeywords(emptyKeywords);
      setClarificationHistory([]);
      setStatusMessage("");
      void refreshRuntimeReadiness();
      setError(requestError instanceof Error ? requestError.message : "Analyze topic failed");
    } finally {
      setIsSubmitting(false);
    }
  };

  const loadContext = async () => {
    if (!resumeContextId.trim()) {
      setError("Enter a context_id to load.");
      return;
    }
    setIsLoadingContext(true);
    setError("");
    setStatusMessage(`Loading ${resumeContextId.trim()}...`);
    try {
      const payload = await fetchJson<SessionResponse>(`/api/sessions/${resumeContextId.trim()}`);
      applySession(payload);
      setStatusMessage(
        payload.status === "clarification_required"
          ? "Clarification required. Answer the questions below to continue."
          : "Context loaded."
      );
    } catch (requestError) {
      setStatusMessage("");
      void refreshRuntimeReadiness();
      setError(requestError instanceof Error ? requestError.message : "Load context failed");
    } finally {
      setIsLoadingContext(false);
    }
  };

  const submitClarifications = async () => {
    if (!contextId) {
      setError("Analyze or load a context before submitting clarification answers.");
      return;
    }
    setIsSubmittingClarification(true);
    setError("");
    setStatusMessage("Submitting clarification answers...");
    try {
      const payload = await fetchJson<SessionResponse>(`/api/sessions/${contextId}/clarifications`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ answers }),
      });
      applySession(payload);
      setStatusMessage(
        payload.status === "clarification_required"
          ? "Still need one more clarification round."
          : "Keywords ready."
      );
    } catch (requestError) {
      void refreshRuntimeReadiness();
      setError(requestError instanceof Error ? requestError.message : "Clarification submit failed");
    } finally {
      setIsSubmittingClarification(false);
    }
  };

  const isClarificationDisabled =
    isSubmittingClarification ||
    !contextId ||
    runtimeReadiness?.runnable === false ||
    answers.length !== questions.length ||
    answers.some((answer) => !answer.trim());

  return (
    <PageSection>
      <PageHeader
        description="Generate keyword groups and resolve clarification loops for a topic."
        eyebrow="Keyword analysis"
        title="Topic to keyword groups."
      />
      <Stack gap="sm">
        <RuntimeReadinessPanel readiness={runtimeReadiness} />
        <TextInput
          onChange={(event) => setTopic(event.target.value)}
          value={topic}
        />
        <ActionBar>
          <Button onClick={submit} disabled={isSubmitting || isLoadingContext || runtimeReadiness?.runnable === false}>
            {isSubmitting ? "Analyzing..." : "Analyze Topic"}
          </Button>
        </ActionBar>
        <TextInput
          onChange={(event) => setResumeContextId(event.target.value)}
          placeholder="Load existing context_id"
          value={resumeContextId}
        />
        <ActionBar>
          <Button onClick={loadContext} disabled={isLoadingContext || isSubmitting} variant="light">
            {isLoadingContext ? "Loading..." : "Load Context"}
          </Button>
        </ActionBar>
        {error ? (
          <Alert color="red" variant="light">
            {error}
          </Alert>
        ) : null}
        {statusMessage ? <Text size="sm">{statusMessage}</Text> : null}
        {contextId ? <KeyValueRow label="context_id" mono value={contextId} /> : null}
        {status ? <StatusBadge label={status} status={status} /> : null}
        {clarificationHistory.length ? (
          <Stack gap="sm">
            <Text fw={600} size="sm">
              Clarification history
            </Text>
            {clarificationHistory.map((item, index) => (
              <Paper key={`${item.question}-${index}`} p="sm" radius="sm" withBorder>
                <Stack gap={4}>
                  <Text size="sm">
                    <Text component="span" fw={700}>
                      Q:
                    </Text>{" "}
                    {item.question}
                  </Text>
                  <Text size="sm">
                    <Text component="span" fw={700}>
                      A:
                    </Text>{" "}
                    {item.answer}
                  </Text>
                </Stack>
              </Paper>
            ))}
          </Stack>
        ) : null}
        {questions.length ? (
          <Stack gap="sm">
            <Text fw={600} size="sm">
              Answer these questions to continue
            </Text>
            {questions.map((question, index) => (
              <Textarea
                autosize
                key={question}
                label={question}
                minRows={3}
                onChange={(event) =>
                  setAnswers((current) => current.map((answer, answerIndex) => (answerIndex === index ? event.target.value : answer)))
                }
                placeholder="Type your answer"
                value={answers[index] ?? ""}
              />
            ))}
            <ActionBar>
              <Button onClick={submitClarifications} disabled={isClarificationDisabled}>
                {isSubmittingClarification ? "Submitting..." : "Submit Answers"}
              </Button>
            </ActionBar>
          </Stack>
        ) : (
          <Stack gap="sm">
            {Object.entries(keywords).map(([group, values]) => (
              <Paper key={group} p="sm" radius="sm" withBorder>
                <Stack gap={4}>
                  <Text fw={600} size="sm">
                    {group}
                  </Text>
                  <Text size="sm">{values.join(", ") || "No keywords yet"}</Text>
                </Stack>
              </Paper>
            ))}
          </Stack>
        )}
      </Stack>
    </PageSection>
  );
}
