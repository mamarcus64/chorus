import { useEffect, useState } from "react";
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

function ReferenceImage({ src, alt }: { src: string; alt: string }) {
  const [attempt, setAttempt] = useState(0);
  const [broken, setBroken] = useState(false);
  const shown = attempt > 0 ? `${src}${src.includes("?") ? "&" : "?"}retry=${attempt}` : src;

  useEffect(() => {
    setAttempt(0);
    setBroken(false);
  }, [src]);

  if (broken) {
    return (
      <button
        type="button"
        className="still-retry"
        onClick={() => {
          setBroken(false);
          setAttempt((value) => value + 1);
        }}
      >
        Retry
      </button>
    );
  }

  return (
    <img
      src={shown}
      alt={alt}
      decoding="async"
      onError={() => {
        if (attempt < 3) setAttempt((value) => value + 1);
        else setBroken(true);
      }}
    />
  );
}

function stageNote(overlays: string[]): string {
  if (overlays.includes("gaze")) {
    return "An arrow is the estimated direction of each eye. A circle means the estimate points toward the camera.";
  }
  if (overlays.includes("pose")) {
    return "Red is left–right, green is up–down, and blue is the direction the face points. Blue shrinks to a dot when the estimate faces the camera.";
  }
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
  const paired = overlays.includes("gaze") || overlays.includes("pose");
  const features = item.features as FrameFeatures;

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

  const judged = (
    <FrameView
      src={mediaUrl(project, still)}
      features={features}
      overlays={paired ? [] : overlays}
      maxHeight={references.length > 0 ? "48vh" : paired ? "62vh" : "68vh"}
      alt="Frame to judge"
    />
  );

  return (
    <div className="choice-task">
      <h2 className="prompt">{prompt}</h2>
      {references.length > 0 && (
        <section className="ref-block" aria-label="Other frames from this interview">
          <h3>Other frames from this interview</h3>
          <p className="muted">Other moments from this interview. Not the frame to judge.</p>
          <div className="reference-row">
            {references.map((fileId, index) => (
              <ReferenceImage
                key={fileId}
                src={mediaUrl(project, fileId)}
                alt={`Other frame ${index + 1} from this interview`}
              />
            ))}
          </div>
        </section>
      )}
      <div className="judge-card">
        {paired ? (
          <div className="compare">
            <figure>
              <figcaption>Photograph</figcaption>
              {judged}
            </figure>
            <figure>
              <figcaption>Estimate</figcaption>
              <FrameView
                src={mediaUrl(project, still)}
                features={features}
                overlays={overlays}
                maxHeight="62vh"
                alt="Frame with the estimate drawn on it"
              />
            </figure>
          </div>
        ) : (
          <>
            {references.length > 0 && <p className="stage-label">Frame to judge</p>}
            {judged}
          </>
        )}
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
