import { useCallback, useEffect, useRef, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { api, type ItemRecord, type PartitionDetail } from "../api";
import { useAuth } from "../auth";
import HelpModal from "../player/HelpModal";
import ClipPlayer from "../player/ClipPlayer";
import TranscriptTrack from "../player/TranscriptTrack";
import type { Utterance } from "../player/types";
import FrameChoice from "../tasks/frame_choice/FrameChoice";

export default function Annotate() {
  const { project = "voices", partitionId = "" } = useParams();
  const { user, loading } = useAuth();
  const navigate = useNavigate();
  const [detail, setDetail] = useState<PartitionDetail | null>(null);
  const [index, setIndex] = useState(0);
  const [error, setError] = useState("");
  const [saving, setSaving] = useState(false);
  const [showHelp, setShowHelp] = useState(true);
  const [listStatus, setListStatus] = useState<string | null>(null);
  const started = useRef(0);

  useEffect(() => {
    if (loading) return;
    if (!user) navigate(`/p/${project}/login`);
  }, [loading, user, navigate, project]);

  useEffect(() => {
    if (!user) return;
    let cancelled = false;
    api.partition(project, partitionId)
      .then((next) => {
        if (cancelled) return;
        setDetail(next);
        setListStatus(next.progress?.status ?? "todo");
        const first = next.items.findIndex((item) => !item.answer);
        setIndex(first < 0 ? 0 : first);
        setShowHelp(true);
      })
      .catch((err: Error) => {
        if (!cancelled) setError(err.message);
      });
    return () => {
      cancelled = true;
    };
  }, [project, partitionId, user]);

  const item: ItemRecord | undefined = detail?.items[index];
  useEffect(() => {
    started.current = Date.now();
  }, [item?.id]);

  const go = useCallback((next: number) => {
    if (!detail) return;
    if (next < 0 || next >= detail.items.length) return;
    setIndex(next);
  }, [detail]);

  useEffect(() => {
    const onKey = (event: KeyboardEvent) => {
      const target = event.target;
      if (target instanceof HTMLInputElement || target instanceof HTMLTextAreaElement) return;
      if (event.key === "ArrowLeft") go(index - 1);
      if (event.key === "ArrowRight") go(index + 1);
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [go, index]);

  async function onAnswer(value: { choice: string }) {
    if (!detail || !item || saving) return;
    setSaving(true);
    setError("");
    try {
      const elapsed = Date.now() - started.current;
      const saved = await api.saveAnnotation(project, item.id, value, elapsed);
      setListStatus(saved.list_status);
      const items = detail.items.map((row) =>
        row.id === item.id ? { ...row, answer: saved.annotation.value } : row,
      );
      setDetail({ ...detail, items });
      if (index < items.length - 1) setIndex(index + 1);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Save failed");
    } finally {
      setSaving(false);
    }
  }

  async function mark(done: boolean) {
    const result = done
      ? await api.markDone(project, partitionId)
      : await api.reopen(project, partitionId);
    setListStatus(result.list_status);
  }

  if (!user) return null;
  if (error && !detail) return <main><p className="error">{error}</p></main>;
  if (!detail || !item) return <main><p>Loading…</p></main>;

  const utterances = (item.locator.utterances as Utterance[] | undefined) ?? [];
  const start = typeof item.locator.start_s === "number" ? item.locator.start_s : undefined;
  const end = typeof item.locator.end_s === "number" ? item.locator.end_s : undefined;
  const fileId = typeof item.locator.file === "string" ? item.locator.file : "";

  return (
    <main className="annotate">
      <header className="bar">
        <Link to={`/p/${project}`}>Home</Link>
        <strong>{detail.task.name}</strong>
        <span>{detail.partition.name}</span>
        <span>{index + 1} / {detail.items.length}</span>
        <button type="button" onClick={() => go(index - 1)} disabled={index === 0}>Previous</button>
        <button type="button" onClick={() => go(index + 1)} disabled={index === detail.items.length - 1}>Next</button>
        <label>
          Jump
          <input
            style={{ width: 64 }}
            onKeyDown={(event) => {
              if (event.key !== "Enter") return;
              const next = Number((event.target as HTMLInputElement).value);
              if (Number.isFinite(next)) go(next - 1);
            }}
          />
        </label>
        <span className="muted">{listStatus}</span>
        {listStatus === "done" ? (
          <button type="button" onClick={() => void mark(false)}>Reopen</button>
        ) : (
          <button type="button" onClick={() => void mark(true)}>Mark done</button>
        )}
        <button type="button" onClick={() => setShowHelp(true)}>Instructions</button>
      </header>
      {error && <p className="error">{error}</p>}
      {item.kind === "video" && fileId && (
        <ClipPlayer src={`/api/p/${project}/media/${encodeURIComponent(fileId)}`} start={start} end={end} />
      )}
      {utterances.length > 0 && (
        <TranscriptTrack
          utterances={utterances}
          currentTimeMs={(start ?? 0) * 1000}
          onSeek={() => undefined}
        />
      )}
      {detail.task.code_key === "frame_choice" ? (
        <FrameChoice
          project={project}
          task={detail.task}
          item={item}
          answer={item.answer}
          onAnswer={(value) => void onAnswer(value)}
          disabled={saving}
        />
      ) : (
        <p>No viewer is registered for {detail.task.code_key}.</p>
      )}
      {showHelp && (
        <HelpModal
          title={detail.task.name}
          instructions={detail.task.config.instructions || "No instructions for this task."}
          onClose={() => setShowHelp(false)}
        />
      )}
    </main>
  );
}
