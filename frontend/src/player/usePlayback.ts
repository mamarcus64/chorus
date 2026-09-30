import { useCallback, useEffect, useRef, useState } from "react";

export interface PlaybackState {
  currentTime: number;
  duration: number;
  playing: boolean;
  speed: number;
}

export const SPEEDS = [0.25, 0.5, 1, 1.5, 2];

export function usePlayback(loop?: { start: number; end: number }) {
  const videoRef = useRef<HTMLVideoElement>(null);
  const loopRef = useRef(loop);
  useEffect(() => {
    loopRef.current = loop;
  }, [loop]);
  const [state, setState] = useState<PlaybackState>({
    currentTime: 0,
    duration: 0,
    playing: false,
    speed: 1,
  });

  useEffect(() => {
    const video = videoRef.current;
    if (!video) return;

    const onTimeUpdate = () => {
      const bounds = loopRef.current;
      if (bounds && video.currentTime >= bounds.end) {
        video.currentTime = bounds.start;
      }
      setState((prev) => ({ ...prev, currentTime: video.currentTime }));
    };
    const onDurationChange = () =>
      setState((prev) => ({ ...prev, duration: video.duration || 0 }));
    const onPlay = () => setState((prev) => ({ ...prev, playing: true }));
    const onPause = () => setState((prev) => ({ ...prev, playing: false }));
    const onRateChange = () => setState((prev) => ({ ...prev, speed: video.playbackRate }));

    video.addEventListener("timeupdate", onTimeUpdate);
    video.addEventListener("durationchange", onDurationChange);
    video.addEventListener("play", onPlay);
    video.addEventListener("pause", onPause);
    video.addEventListener("ratechange", onRateChange);
    return () => {
      video.removeEventListener("timeupdate", onTimeUpdate);
      video.removeEventListener("durationchange", onDurationChange);
      video.removeEventListener("play", onPlay);
      video.removeEventListener("pause", onPause);
      video.removeEventListener("ratechange", onRateChange);
    };
  }, []);

  const togglePlay = useCallback(() => {
    const video = videoRef.current;
    if (!video) return;
    if (video.paused) void video.play();
    else video.pause();
  }, []);

  const seek = useCallback((time: number) => {
    const video = videoRef.current;
    if (!video) return;
    const bounds = loopRef.current;
    const next = bounds ? Math.max(bounds.start, Math.min(time, bounds.end)) : time;
    video.currentTime = next;
  }, []);

  const setSpeed = useCallback((rate: number) => {
    const video = videoRef.current;
    if (!video) return;
    video.playbackRate = rate;
  }, []);

  const stepFrame = useCallback((direction: -1 | 1, fps = 30) => {
    const video = videoRef.current;
    if (!video) return;
    video.pause();
    seek(video.currentTime + direction / fps);
  }, [seek]);

  return { videoRef, state, togglePlay, seek, setSpeed, stepFrame };
}
