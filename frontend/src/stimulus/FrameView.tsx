import { useEffect, useRef, useState } from "react";
import { drawOverlays, type FrameFeatures } from "./overlays";

interface Props {
  src: string;
  features: FrameFeatures;
  overlays: string[];
  maxHeight?: string;
  alt?: string;
}

export default function FrameView({
  src,
  features,
  overlays,
  maxHeight = "68vh",
  alt = "Frame to annotate",
}: Props) {
  const imageRef = useRef<HTMLImageElement>(null);
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const [attempt, setAttempt] = useState(0);
  const [broken, setBroken] = useState(false);
  const shown = attempt > 0 ? `${src}${src.includes("?") ? "&" : "?"}retry=${attempt}` : src;

  useEffect(() => {
    setAttempt(0);
    setBroken(false);
  }, [src]);

  useEffect(() => {
    const image = imageRef.current;
    const canvas = canvasRef.current;
    if (!image || !canvas) return;

    const paint = () => {
      const width = image.clientWidth;
      const height = image.clientHeight;
      if (!width || !height) return;
      const ratio = window.devicePixelRatio || 1;
      canvas.width = Math.round(width * ratio);
      canvas.height = Math.round(height * ratio);
      canvas.style.width = `${width}px`;
      canvas.style.height = `${height}px`;
      const ctx = canvas.getContext("2d");
      if (!ctx) return;
      ctx.setTransform(ratio, 0, 0, ratio, 0, 0);
      drawOverlays(ctx, width, height, features, overlays);
    };

    paint();
    image.addEventListener("load", paint);
    window.addEventListener("resize", paint);
    return () => {
      image.removeEventListener("load", paint);
      window.removeEventListener("resize", paint);
    };
  }, [shown, features, overlays, maxHeight]);

  return (
    <div style={{ position: "relative", display: "inline-block", maxWidth: "100%" }}>
      <img
        ref={imageRef}
        src={shown}
        alt={alt}
        decoding="async"
        style={{ display: broken ? "none" : "block", maxWidth: "100%", maxHeight, background: "#000" }}
        onError={() => {
          if (attempt < 3) setAttempt((value) => value + 1);
          else setBroken(true);
        }}
      />
      {broken && (
        <button type="button" className="still-retry" onClick={() => { setBroken(false); setAttempt((value) => value + 1); }}>
          Could not load this frame. Retry
        </button>
      )}
      <canvas ref={canvasRef} style={{ position: "absolute", inset: 0, pointerEvents: "none" }} />
    </div>
  );
}
