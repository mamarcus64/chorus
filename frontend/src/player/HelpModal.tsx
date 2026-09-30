import { useEffect } from "react";

interface Props {
  title: string;
  instructions: string;
  onClose: () => void;
}

export default function HelpModal({ title, instructions, onClose }: Props) {
  useEffect(() => {
    const onKey = (event: KeyboardEvent) => {
      if (event.key === "Escape") onClose();
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [onClose]);

  return (
    <div
      onClick={onClose}
      style={{
        position: "fixed",
        inset: 0,
        zIndex: 1000,
        backgroundColor: "rgba(0,0,0,0.65)",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
      }}
    >
      <div
        onClick={(event) => event.stopPropagation()}
        style={{
          backgroundColor: "#1e293b",
          borderRadius: 12,
          padding: "28px 32px",
          maxWidth: 640,
          width: "90vw",
          maxHeight: "88vh",
          overflowY: "auto",
          color: "#e2e8f0",
        }}
      >
        <div style={{ display: "flex", justifyContent: "space-between", gap: 12 }}>
          <h2 style={{ margin: 0 }}>{title}</h2>
          <button type="button" onClick={onClose} aria-label="Close">✕</button>
        </div>
        <pre style={{ whiteSpace: "pre-wrap", fontFamily: "inherit", lineHeight: 1.6 }}>{instructions}</pre>
        <button type="button" onClick={onClose} style={{ width: "100%" }}>
          Got it — start annotating
        </button>
      </div>
    </div>
  );
}
