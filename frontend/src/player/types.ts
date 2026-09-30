export interface Word {
  text: string;
  ms: number;
}

export interface Utterance {
  speaker: "interviewer" | "interviewee";
  tag: string | null;
  text: string;
  start_ms: number;
  end_ms: number;
  words?: Word[];
  type?: "non_verbal";
}
