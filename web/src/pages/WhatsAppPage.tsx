import { FormEvent, useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";

type Message = {
  id: number;
  author: "agent" | "user";
  text: string;
  time: string;
};

const INITIAL_MESSAGES: Message[] = [
  {
    id: 1,
    author: "agent",
    text: "Hola, soy el asistente de Mesa de Ayuda OITSI-MTC. ¿En qué podemos ayudarte?",
    time: "09:41",
  },
  {
    id: 2,
    author: "user",
    text: "La impresora Kyocera 7003 no imprime y necesito que la configuren de nuevo.",
    time: "09:42",
  },
  {
    id: 3,
    author: "agent",
    text: "Entendido. Voy a registrar el problema para que el equipo técnico encuentre una solución.",
    time: "09:42",
  },
];

function transcriptFrom(messages: Message[]) {
  return messages
    .map(({ author, text }) => `${author === "user" ? "Usuario" : "WhatsApp"}: ${text}`)
    .join("\n");
}

export default function WhatsAppPage() {
  const navigate = useNavigate();
  const [messages, setMessages] = useState(INITIAL_MESSAGES);
  const [draft, setDraft] = useState("");
  const [error, setError] = useState("");

  const hasUserMessage = useMemo(
    () => messages.some((message) => message.author === "user"),
    [messages]
  );

  const sendMessage = (event: FormEvent) => {
    event.preventDefault();
    const text = draft.trim();
    if (!text) return;

    setMessages((current) => [
      ...current,
      {
        id: Date.now(),
        author: "user",
        text,
        time: new Date().toLocaleTimeString("es-PE", {
          hour: "2-digit",
          minute: "2-digit",
        }),
      },
    ]);
    setDraft("");
    setError("");
  };

  const sendToPipeline = () => {
    if (!hasUserMessage) {
      setError("Agrega al menos un mensaje del usuario antes de continuar.");
      return;
    }

    navigate("/", {
      state: {
        whatsappText: transcriptFrom(messages),
      },
    });
  };

  return (
    <div className="max-w-3xl mx-auto p-4">
      <div className="card overflow-hidden bg-[#e5ddd5] shadow-xl">
        <div className="flex items-center gap-3 bg-[#075e54] px-4 py-3 text-white">
          <div className="flex h-10 w-10 items-center justify-center rounded-full bg-white/20 text-lg">
            M
          </div>
          <div>
            <p className="font-semibold">Mesa de Ayuda OITSI-MTC</p>
            <p className="text-xs text-white/75">WhatsApp · asistente en línea</p>
          </div>
          <span className="ml-auto badge border-0 bg-white/15 text-white">Demo</span>
        </div>

        <div className="min-h-[28rem] space-y-3 bg-[radial-gradient(#d6ccc4_1px,transparent_1px)] bg-[size:16px_16px] p-4">
          <div className="mx-auto mb-4 w-fit rounded-lg bg-[#fff3c4] px-3 py-1 text-center text-[11px] text-base-content/60 shadow-sm">
            Conversación simulada para demostrar el recorrido hacia el pipeline
          </div>
          {messages.map((message) => (
            <div
              key={message.id}
              className={`flex ${message.author === "user" ? "justify-end" : "justify-start"}`}
            >
              <div
                className={`max-w-[85%] rounded-lg px-3 py-2 text-sm shadow-sm ${
                  message.author === "user"
                    ? "rounded-tr-none bg-[#dcf8c6]"
                    : "rounded-tl-none bg-white"
                }`}
              >
                <p>{message.text}</p>
                <p className="mt-1 text-right text-[10px] text-base-content/50">
                  {message.time} {message.author === "user" && "✓✓"}
                </p>
              </div>
            </div>
          ))}
        </div>

        <form onSubmit={sendMessage} className="flex gap-2 bg-[#f0f0f0] p-3">
          <input
            className="input input-sm min-w-0 flex-1 rounded-full bg-white"
            value={draft}
            onChange={(event) => setDraft(event.target.value)}
            placeholder="Escribe un mensaje..."
            aria-label="Mensaje de WhatsApp"
          />
          <button type="submit" className="btn btn-sm btn-circle bg-[#128c7e] text-white">
            →
          </button>
        </form>
      </div>

      <div className="card mt-4 bg-base-100 shadow">
        <div className="card-body gap-3 p-4">
          <div>
            <h1 className="card-title text-base">Continuar con el pipeline</h1>
            <p className="text-sm text-base-content/70">
              Envía esta conversación al operador para ejecutar clasificación, priorización y
              recuperación RAG.
            </p>
          </div>
          <button
            type="button"
            className="btn btn-success w-full sm:w-auto sm:self-end"
            onClick={sendToPipeline}
            disabled={!hasUserMessage}
          >
            Enviar al pipeline →
          </button>
          {error && <p className="text-sm text-error">{error}</p>}
        </div>
      </div>
    </div>
  );
}
