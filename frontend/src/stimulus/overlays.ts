export interface FrameFeatures {
  bbox?: number[];
  image_size?: number[];
  face_score?: number;
  landmarks?: number[][];
}

export function drawOverlays(
  ctx: CanvasRenderingContext2D,
  width: number,
  height: number,
  features: FrameFeatures,
  overlays: string[],
) {
  ctx.clearRect(0, 0, width, height);
  if (!features.image_size) return;
  const [imageWidth, imageHeight] = features.image_size;
  if (!imageWidth || !imageHeight) return;
  const scaleX = width / imageWidth;
  const scaleY = height / imageHeight;
  if (overlays.includes("bbox") && features.bbox) {
    const [x, y, boxWidth, boxHeight] = features.bbox;
    ctx.strokeStyle = "#4ade80";
    ctx.lineWidth = Math.max(2, Math.min(width, height) / 220);
    ctx.strokeRect(x * scaleX, y * scaleY, boxWidth * scaleX, boxHeight * scaleY);
  }
  if (!overlays.includes("landmarks") || !features.landmarks) return;
  const radius = Math.max(2.2, Math.min(width, height) / 150);
  for (const point of features.landmarks) {
    if (!Array.isArray(point) || point.length < 2) continue;
    const px = point[0] * scaleX;
    const py = point[1] * scaleY;
    ctx.beginPath();
    ctx.fillStyle = "rgba(15, 23, 42, 0.9)";
    ctx.arc(px, py, radius + 1.1, 0, Math.PI * 2);
    ctx.fill();
    ctx.beginPath();
    ctx.fillStyle = "#f8fafc";
    ctx.arc(px, py, radius, 0, Math.PI * 2);
    ctx.fill();
  }
}
