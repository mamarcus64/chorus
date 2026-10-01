import { useEffect } from "react";
import { mediaUrl, type ItemRecord, type TaskConfig } from "../../api";
import FrameView from "../../stimulus/FrameView";
import type { FrameFeatures } from "../../stimulus/overlays";

interface Props {
  project: string;
  task: { config: TaskConfig };
  item: ItemRecord;
  answer: { choice?: string } | null;
  onAnswer: (value: { choice: string }) => void;
  disabled: boolean;
}

function referenceIds(locator: Record<string, unknown>): string[] {
  const refs = locator.references;
  if (!Array.isArray(refs)) return [];
  return refs.filter((item): item is string => typeof item === "string" && item.length > 0);
}

function stageNote(overlays: string[]): string {
  const notes: string[] = [];
  if (overlays.includes("bbox")) notes.push("The box is the region to judge.");
  if (overlays.includes("landmarks")) {
    notes.push("The points mark the detected eyes, brows, nose, mouth, and jaw.");
  }
  return notes.join(" ");
}

export default function FrameChoice({ project, task, item, answer, onAnswer, disabled }: Props) {
  const { choices, overlays, prompt } = task.config;
  const still = String(item.locator.still ?? "");
  const references = referenceIds(item.locator);

  useEffect(() => {
    const onKey = (event: KeyboardEvent) => {
      const target = event.target;
      if (target instanceof HTMLInputElement || target instanceof HTMLTextAreaElement) return;
      const choice = choices.find((itemChoice) => itemChoice.key === event.key);
      if (!choice || disabled) return;
      event.preventDefault();
      onAnswer({ choice: choice.value });
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [choices, disabled, onAnswer]);

  return (
    <div className="choice-task">
      <h2 className="prompt">{prompt}</h2>
      {references.length > 0 && (
        <section className="ref-block" aria-label="Other frames from this interview">
          <h3>Other frames from this interview</h3>
          <p className="muted">Other moments from this interview. Not the frame to judge.</p>
          <div className="reference-row">
            {references.map((fileId, index) => (
              <img
                key={fileId}
                src={mediaUrl(project, fileId)}
                alt={`Other frame ${index + 1} from this interview`}
              />
            ))}
          </div>
        </section>
      )}
      <div className="judge-card">
        {references.length > 0 && <p className="stage-label">Frame to judge</p>}
        <FrameView
          src={mediaUrl(project, still)}
          features={item.features as FrameFeatures}
          overlays={overlays}
          maxHeight={references.length > 0 ? "54vh" : "68vh"}
        />
        {stageNote(overlays) && <p className="stage-note">{stageNote(overlays)}</p>}
      </div>
      <div className="choices" role="group" aria-label={prompt}>
        {choices.map((choice) => (
          <button
            type="button"
            key={choice.value}
            disabled={disabled}
            aria-pressed={answer?.choice === choice.value}
            onClick={() => onAnswer({ choice: choice.value })}
          >
            <kbd>{choice.key}</kbd>
            {choice.label}
          </button>
        ))}
      </div>
    </div>
  );
}
