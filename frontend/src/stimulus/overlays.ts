export interface FrameFeatures {
  bbox?: number[];
  image_size?: number[];
  face_score?: number;
}

export function drawOverlays(
  ctx: CanvasRenderingContext2D,
  width: number,
  height: number,
  features: FrameFeatures,
  overlays: string[],
) {
  ctx.clearRect(0, 0, width, height);
  if (!overlays.includes("bbox") || !features.bbox || !features.image_size) return;
  const [x, y, boxWidth, boxHeight] = features.bbox;
  const [imageWidth, imageHeight] = features.image_size;
  if (!imageWidth || !imageHeight) return;
  const scaleX = width / imageWidth;
  const scaleY = height / imageHeight;
  ctx.strokeStyle = "#4ade80";
  ctx.lineWidth = 2;
  ctx.strokeRect(x * scaleX, y * scaleY, boxWidth * scaleX, boxHeight * scaleY);
}
