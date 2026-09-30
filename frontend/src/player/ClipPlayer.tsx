import { useEffect } from "react";
import { SPEEDS, usePlayback } from "./usePlayback";

function formatTime(seconds: number): string {
  if (!Number.isFinite(seconds) || seconds < 0) return "0:00";
  const minutes = Math.floor(seconds / 60);
  const rest = Math.floor(seconds % 60);
  return `${minutes}:${rest.toString().padStart(2, "0")}`;
}

interface Props {
  src: string;
  start?: number;
  end?: number;
  fps?: number;
}

export default function ClipPlayer({ src, start, end, fps = 30 }: Props) {
  const loop = start != null && end != null ? { start, end } : undefined;
  const { videoRef, state, togglePlay, seek, setSpeed, stepFrame } = usePlayback(loop);

  useEffect(() => {
    const video = videoRef.current;
    if (!video) return;
    const onLoaded = () => {
      if (start != null) video.currentTime = start;
    };
    video.addEventListener("loadeddata", onLoaded);
    return () => video.removeEventListener("loadeddata", onLoaded);
  }, [src, start, videoRef]);

  const barStart = start ?? 0;
  const barEnd = end ?? state.duration;

  return (
    <div>
      <video
        ref={videoRef}
        src={src}
        preload="auto"
        playsInline
        style={{ width: "100%", borderRadius: 8, background: "#000", maxHeight: "50vh" }}
      />
      <div style={{ display: "flex", gap: 8, alignItems: "center", flexWrap: "wrap", marginTop: 8 }}>
        <button type="button" onClick={togglePlay}>{state.playing ? "Pause" : "Play"}</button>
        <button type="button" onClick={() => stepFrame(-1, fps)} title="Previous frame">− frame</button>
        <button type="button" onClick={() => stepFrame(1, fps)} title="Next frame">+ frame</button>
        {SPEEDS.map((rate) => (
          <button
            type="button"
            key={rate}
            onClick={() => setSpeed(rate)}
            aria-pressed={state.speed === rate}
          >
            {rate}x
          </button>
        ))}
        <span>{formatTime(state.currentTime)} / {formatTime(state.duration)}</span>
      </div>
      <input
        type="range"
        min={barStart}
        max={barEnd || 1}
        step={1 / fps}
        value={Math.min(Math.max(state.currentTime, barStart), barEnd || 1)}
        onChange={(event) => seek(Number(event.target.value))}
        style={{ width: "100%" }}
      />
    </div>
  );
}
