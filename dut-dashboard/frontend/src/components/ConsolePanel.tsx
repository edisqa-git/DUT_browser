import { FormEvent, useEffect, useRef, useState } from "react";

type Props = {
  lines: string[];
  onSend: (text: string) => Promise<void>;
};

export default function ConsolePanel({ lines, onSend }: Props) {
  const [command, setCommand] = useState("");
  const consoleRef = useRef<HTMLDivElement | null>(null);
  const [stickToBottom, setStickToBottom] = useState(true);

  function scrollToBottom() {
    if (!consoleRef.current) {
      return;
    }
    consoleRef.current.scrollTop = consoleRef.current.scrollHeight;
  }

  function handleConsoleScroll() {
    if (!consoleRef.current) {
      return;
    }
    const { scrollTop, scrollHeight, clientHeight } = consoleRef.current;
    const isNearBottom = scrollHeight - (scrollTop + clientHeight) < 20;
    setStickToBottom(isNearBottom);
  }

  useEffect(() => {
    if (stickToBottom) {
      scrollToBottom();
    }
  }, [lines, command, stickToBottom]);

  async function handleSubmit(event: FormEvent) {
    event.preventDefault();
    if (!command.trim()) {
      return;
    }
    const payload = command.endsWith("\n") ? command : `${command}\n`;
    await onSend(payload);
    setCommand("");
  }

  return (
    <div style={{ border: "1px solid #ddd", padding: 12 }}>
      <h3 style={{ marginTop: 0 }}>Serial Console</h3>
      <div
        ref={consoleRef}
        onScroll={handleConsoleScroll}
        style={{
          height: 320,
          overflowY: "auto",
          background: "#121212",
          color: "#f5f5f5",
          fontFamily: "monospace",
          fontSize: 12,
          padding: 8,
          whiteSpace: "pre-wrap",
        }}
      >
        {lines.join("\n")}
      </div>
      <form onSubmit={handleSubmit} style={{ marginTop: 8, display: "flex", gap: 8 }}>
        <input
          value={command}
          onChange={(e) => setCommand(e.target.value)}
          placeholder="Type command"
          style={{ flex: 1 }}
        />
        <button type="submit">Send</button>
      </form>
    </div>
  );
}
