import type { ComponentType } from "react";
import type { ItemRecord, TaskConfig } from "../api";
import FrameChoice from "./frame_choice/FrameChoice";

export interface TaskProps {
  project: string;
  task: { config: TaskConfig };
  item: ItemRecord;
  answer: { choice?: string } | null;
  onAnswer: (value: { choice: string }) => void;
  disabled: boolean;
}

const registry: Record<string, ComponentType<TaskProps>> = {
  frame_choice: FrameChoice,
};

export function taskComponent(codeKey: string): ComponentType<TaskProps> | null {
  return registry[codeKey] ?? null;
}
