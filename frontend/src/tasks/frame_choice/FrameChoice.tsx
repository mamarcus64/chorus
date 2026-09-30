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

export default function FrameChoice({ project, task, item, answer, onAnswer, disabled }: Props) {
  const { choices, overlays, prompt } = task.config;
  const still = String(item.locator.still ?? "");

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
    <div>
      <h2 style={{ marginTop: 0 }}>{prompt}</h2>
      <FrameView src={mediaUrl(project, still)} features={item.features as FrameFeatures} overlays={overlays} />
      <div style={{ display: "flex", gap: 8, marginTop: 16 }}>
        {choices.map((choice) => (
          <button
            type="button"
            key={choice.value}
            disabled={disabled}
            aria-pressed={answer?.choice === choice.value}
            onClick={() => onAnswer({ choice: choice.value })}
          >
            {choice.key}. {choice.label}
          </button>
        ))}
      </div>
    </div>
  );
}
