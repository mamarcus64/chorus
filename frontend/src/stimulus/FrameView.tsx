import { useEffect, useRef } from "react";
import { drawOverlays, type FrameFeatures } from "./overlays";

interface Props {
  src: string;
  features: FrameFeatures;
  overlays: string[];
}

export default function FrameView({ src, features, overlays }: Props) {
  const imageRef = useRef<HTMLImageElement>(null);
  const canvasRef = useRef<HTMLCanvasElement>(null);

  useEffect(() => {
    const image = imageRef.current;
    const canvas = canvasRef.current;
    if (!image || !canvas) return;

    const paint = () => {
      const width = image.clientWidth;
      const height = image.clientHeight;
      if (!width || !height) return;
      canvas.width = width;
      canvas.height = height;
      canvas.style.width = `${width}px`;
      canvas.style.height = `${height}px`;
      const ctx = canvas.getContext("2d");
      if (!ctx) return;
      drawOverlays(ctx, width, height, features, overlays);
    };

    paint();
    image.addEventListener("load", paint);
    window.addEventListener("resize", paint);
    return () => {
      image.removeEventListener("load", paint);
      window.removeEventListener("resize", paint);
    };
  }, [src, features, overlays]);

  return (
    <div style={{ position: "relative", display: "inline-block", maxWidth: "100%" }}>
      <img
        ref={imageRef}
        src={src}
        alt="Frame to annotate"
        style={{ display: "block", maxWidth: "100%", maxHeight: "70vh", background: "#000" }}
      />
      <canvas ref={canvasRef} style={{ position: "absolute", inset: 0, pointerEvents: "none" }} />
    </div>
  );
}
