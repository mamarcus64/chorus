export interface FrameFeatures {
  bbox?: number[];
  image_size?: number[];
  face_score?: number;
  landmarks?: number[][];
  eyes?: number[][];
  gaze_pitch?: number;
  gaze_yaw?: number;
  head_pitch?: number;
  head_roll?: number;
  head_yaw?: number;
}

function scaleOf(width: number, height: number, features: FrameFeatures): [number, number] | null {
  if (!features.image_size) return null;
  const [imageWidth, imageHeight] = features.image_size;
  if (!imageWidth || !imageHeight) return null;
  return [width / imageWidth, height / imageHeight];
}

function drawArrow(
  ctx: CanvasRenderingContext2D,
  x0: number,
  y0: number,
  x1: number,
  y1: number,
  color: string,
  width: number,
) {
  const dx = x1 - x0;
  const dy = y1 - y0;
  const length = Math.hypot(dx, dy);
  if (length < 2) return;
  const angle = Math.atan2(dy, dx);
  const head = Math.min(width * 5.5, Math.max(8, length * 0.32));
  ctx.save();
  ctx.lineCap = "round";
  ctx.lineJoin = "round";
  ctx.strokeStyle = "rgba(15, 23, 42, 0.85)";
  ctx.lineWidth = width + 2.4;
  ctx.beginPath();
  ctx.moveTo(x0, y0);
  ctx.lineTo(x1, y1);
  ctx.stroke();
  ctx.strokeStyle = color;
  ctx.fillStyle = color;
  ctx.lineWidth = width;
  ctx.beginPath();
  ctx.moveTo(x0, y0);
  ctx.lineTo(x1, y1);
  ctx.stroke();
  ctx.beginPath();
  ctx.moveTo(x1, y1);
  ctx.lineTo(x1 - head * Math.cos(angle - 0.42), y1 - head * Math.sin(angle - 0.42));
  ctx.lineTo(x1 - head * Math.cos(angle + 0.42), y1 - head * Math.sin(angle + 0.42));
  ctx.closePath();
  ctx.fill();
  ctx.restore();
}

function drawGaze(
  ctx: CanvasRenderingContext2D,
  width: number,
  height: number,
  features: FrameFeatures,
) {
  const scale = scaleOf(width, height, features);
  const pitch = features.gaze_pitch;
  const yaw = features.gaze_yaw;
  const box = features.bbox;
  if (!scale || pitch === undefined || yaw === undefined || !box) return;
  const [scaleX, scaleY] = scale;
  const [, , boxWidth, boxHeight] = box;
  const dxUnit = Math.sin(yaw) * Math.cos(pitch);
  const dyUnit = -Math.sin(pitch);
  const magnitude = Math.hypot(dxUnit, dyUnit);
  const origins =
    features.eyes && features.eyes.length === 2
      ? features.eyes
      : [[box[0] + boxWidth / 2, box[1] + boxHeight / 2]];
  const face = Math.min(boxWidth * scaleX, boxHeight * scaleY);
  const line = Math.max(2.4, face / 48);
  for (const origin of origins) {
    if (!Array.isArray(origin) || origin.length < 2) continue;
    const x = origin[0] * scaleX;
    const y = origin[1] * scaleY;
    if (magnitude < 0.12) {
      const radius = Math.max(7, face * 0.07);
      ctx.beginPath();
      ctx.strokeStyle = "rgba(15, 23, 42, 0.9)";
      ctx.lineWidth = line + 2.2;
      ctx.arc(x, y, radius, 0, Math.PI * 2);
      ctx.stroke();
      ctx.beginPath();
      ctx.strokeStyle = "#facc15";
      ctx.lineWidth = line;
      ctx.arc(x, y, radius, 0, Math.PI * 2);
      ctx.stroke();
      continue;
    }
    const length = face * Math.min(1.05, 0.35 + magnitude);
    drawArrow(ctx, x, y, x + dxUnit * length, y + dyUnit * length, "#facc15", line);
  }
}

function drawPose(
  ctx: CanvasRenderingContext2D,
  width: number,
  height: number,
  features: FrameFeatures,
) {
  const scale = scaleOf(width, height, features);
  const box = features.bbox;
  const { head_pitch: pitch, head_roll: roll, head_yaw: yaw } = features;
  if (!scale || !box || pitch === undefined || roll === undefined || yaw === undefined) return;
  const [scaleX, scaleY] = scale;
  const [x, y, boxWidth, boxHeight] = box;
  const tdx = (x + boxWidth / 2) * scaleX;
  const tdy = (y + boxHeight / 2) * scaleY;
  const size = Math.min(boxWidth * scaleX, boxHeight * scaleY) / 2;
  const drawnYaw = -yaw;
  const cosYaw = Math.cos(drawnYaw);
  const sinYaw = Math.sin(drawnYaw);
  const cosPitch = Math.cos(pitch);
  const sinPitch = Math.sin(pitch);
  const cosRoll = Math.cos(roll);
  const sinRoll = Math.sin(roll);
  const axes: Array<[number, number, string]> = [
    [size * (cosYaw * cosRoll), size * (cosPitch * sinRoll + cosRoll * sinPitch * sinYaw), "#f87171"],
    [size * (-cosYaw * sinRoll), size * (cosPitch * cosRoll - sinPitch * sinYaw * sinRoll), "#4ade80"],
    [size * sinYaw, size * (-cosYaw * sinPitch), "#60a5fa"],
  ];
  const line = Math.max(2.4, size / 28);
  ctx.beginPath();
  ctx.fillStyle = "#93c5fd";
  ctx.arc(tdx, tdy, Math.max(3.5, line), 0, Math.PI * 2);
  ctx.fill();
  for (const [dx, dy, color] of axes) {
    if (Math.hypot(dx, dy) < 4) continue;
    drawArrow(ctx, tdx, tdy, tdx + dx, tdy + dy, color, line);
  }
}

export function drawOverlays(
  ctx: CanvasRenderingContext2D,
  width: number,
  height: number,
  features: FrameFeatures,
  overlays: string[],
) {
  ctx.clearRect(0, 0, width, height);
  const scale = scaleOf(width, height, features);
  if (!scale) return;
  const [scaleX, scaleY] = scale;
  if (overlays.includes("bbox") && features.bbox) {
    const [x, y, boxWidth, boxHeight] = features.bbox;
    ctx.strokeStyle = "#4ade80";
    ctx.lineWidth = Math.max(2, Math.min(width, height) / 220);
    ctx.strokeRect(x * scaleX, y * scaleY, boxWidth * scaleX, boxHeight * scaleY);
  }
  if (overlays.includes("landmarks") && features.landmarks) {
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
  if (overlays.includes("gaze")) drawGaze(ctx, width, height, features);
  if (overlays.includes("pose")) drawPose(ctx, width, height, features);
}
