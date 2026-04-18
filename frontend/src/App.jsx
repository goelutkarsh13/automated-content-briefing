import { useState, useRef, useEffect } from "react";

const STEPS = [
  "Extracting text",
  "Summarizing with BART",
  "Building narration script",
  "Rendering slides",
  "Generating narration",
  "Composing final video",
];

function SlideViewer({ slides }) {
  const [current, setCurrent] = useState(0);
  if (!slides || slides.length === 0) return null;

  return (
    <div className="mt-6">
      <h3 className="text-lg font-semibold text-gray-200 mb-3">Generated Slides</h3>
      <div className="relative bg-gray-900 rounded-xl overflow-hidden border border-gray-700">
        <img
          src={`/output/slides/${slides[current]}`}
          alt={`Slide ${current + 1}`}
          className="w-full"
        />
        <div className="absolute bottom-0 left-0 right-0 flex items-center justify-between px-4 py-2 bg-black/60">
          <button
            onClick={() => setCurrent(Math.max(0, current - 1))}
            disabled={current === 0}
            className="px-3 py-1 text-sm rounded bg-gray-700 text-gray-300 hover:bg-gray-600 disabled:opacity-30 disabled:cursor-not-allowed transition"
          >
            Prev
          </button>
          <span className="text-gray-400 text-sm">
            {current + 1} / {slides.length}
          </span>
          <button
            onClick={() => setCurrent(Math.min(slides.length - 1, current + 1))}
            disabled={current === slides.length - 1}
            className="px-3 py-1 text-sm rounded bg-gray-700 text-gray-300 hover:bg-gray-600 disabled:opacity-30 disabled:cursor-not-allowed transition"
          >
            Next
          </button>
        </div>
      </div>
    </div>
  );
}

function PipelineProgress({ step }) {
  return (
    <div className="mt-6 space-y-2">
      {STEPS.map((label, i) => (
        <div key={i} className="flex items-center gap-3">
          <div
            className={`w-7 h-7 rounded-full flex items-center justify-center text-xs font-bold transition-all duration-300 ${
              i < step
                ? "bg-emerald-500 text-white"
                : i === step
                ? "bg-amber-400 text-gray-900 animate-pulse"
                : "bg-gray-700 text-gray-500"
            }`}
          >
            {i < step ? "✓" : i + 1}
          </div>
          <span
            className={`text-sm transition-colors ${
              i < step
                ? "text-emerald-400"
                : i === step
                ? "text-amber-300 font-medium"
                : "text-gray-600"
            }`}
          >
            {label}
          </span>
        </div>
      ))}
    </div>
  );
}

export default function App() {
  const [inputText, setInputText] = useState("");
  const [file, setFile] = useState(null);
  const [loading, setLoading] = useState(false);
  const [step, setStep] = useState(-1);
  const [result, setResult] = useState(null);
  const [error, setError] = useState(null);
  const [tab, setTab] = useState("video");
  const fileRef = useRef();

  const handleSubmit = async () => {
    if (!inputText.trim() && !file) return;

    setLoading(true);
    setError(null);
    setResult(null);
    setStep(0);

    // Simulate progress (real progress would need SSE/WebSocket)
    const progressInterval = setInterval(() => {
      setStep((prev) => (prev < 5 ? prev + 1 : prev));
    }, 4000);

    try {
      const formData = new FormData();
      if (file) {
        formData.append("file", file);
      } else {
        formData.append("text", inputText);
      }
      formData.append("tts_backend", "pyttsx3");

      const res = await fetch("/api/briefing", {
        method: "POST",
        body: formData,
      });

      clearInterval(progressInterval);

      if (!res.ok) {
        const err = await res.json();
        throw new Error(err.detail || "Pipeline failed");
      }

      const data = await res.json();
      setStep(6);
      setResult(data);
    } catch (e) {
      clearInterval(progressInterval);
      setError(e.message);
      setStep(-1);
    } finally {
      setLoading(false);
    }
  };

  const handleFileDrop = (e) => {
    e.preventDefault();
    const f = e.dataTransfer?.files?.[0];
    if (f) setFile(f);
  };

  return (
    <div className="min-h-screen bg-gray-950 text-gray-100">
      {/* Header */}
      <header className="border-b border-gray-800 px-6 py-4">
        <div className="max-w-5xl mx-auto flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-9 h-9 rounded-lg bg-gradient-to-br from-violet-500 to-fuchsia-500 flex items-center justify-center text-white font-bold text-lg">
              T
            </div>
            <div>
              <h1 className="text-xl font-bold tracking-tight">BriefCast</h1>
              <p className="text-xs text-gray-500">Content Briefing System</p>
            </div>
          </div>
          <span className="text-xs text-gray-600">Built by Utkarsh Goel</span>
        </div>
      </header>

      {/* Main */}
      <main className="max-w-5xl mx-auto px-6 py-10">
        {!result ? (
          <div className="max-w-2xl mx-auto">
            <div className="text-center mb-8">
              <h2 className="text-3xl font-bold mb-2">
                Turn any text into a{" "}
                <span className="text-transparent bg-clip-text bg-gradient-to-r from-violet-400 to-fuchsia-400">
                  video briefing
                </span>
              </h2>
              <p className="text-gray-500">
                Paste long-form content or upload a file. The pipeline
                summarizes, generates slides, narrates, and composes a video.
              </p>
            </div>

            {/* Input area */}
            <div
              className="border border-gray-800 rounded-xl bg-gray-900/50 overflow-hidden"
              onDragOver={(e) => e.preventDefault()}
              onDrop={handleFileDrop}
            >
              <textarea
                value={inputText}
                onChange={(e) => {
                  setInputText(e.target.value);
                  setFile(null);
                }}
                placeholder="Paste your article, report, or educational content here..."
                className="w-full h-48 bg-transparent px-5 py-4 text-gray-300 placeholder-gray-600 resize-none focus:outline-none text-sm leading-relaxed"
                disabled={loading || !!file}
              />
              <div className="flex items-center justify-between px-5 py-3 border-t border-gray-800 bg-gray-900/30">
                <div className="flex items-center gap-3">
                  <button
                    onClick={() => fileRef.current?.click()}
                    className="text-xs text-gray-500 hover:text-gray-300 transition flex items-center gap-1"
                    disabled={loading}
                  >
                    <span>📎</span>
                    {file ? file.name : "Upload .txt / .pdf"}
                  </button>
                  <input
                    ref={fileRef}
                    type="file"
                    accept=".txt,.pdf,.md"
                    onChange={(e) => {
                      setFile(e.target.files?.[0] || null);
                      setInputText("");
                    }}
                    className="hidden"
                  />
                </div>
                <button
                  onClick={handleSubmit}
                  disabled={loading || (!inputText.trim() && !file)}
                  className="px-5 py-2 rounded-lg bg-gradient-to-r from-violet-600 to-fuchsia-600 text-white text-sm font-medium hover:from-violet-500 hover:to-fuchsia-500 disabled:opacity-30 disabled:cursor-not-allowed transition-all"
                >
                  {loading ? "Processing..." : "Generate Briefing"}
                </button>
              </div>
            </div>

            {/* Progress */}
            {loading && <PipelineProgress step={step} />}

            {/* Error */}
            {error && (
              <div className="mt-4 p-4 rounded-lg bg-red-900/30 border border-red-800 text-red-300 text-sm">
                {error}
              </div>
            )}

            {/* How it works */}
            <div className="mt-12 grid grid-cols-3 gap-4">
              {[
                { icon: "📝", title: "Summarize", desc: "BART-large-CNN extracts key points from your content" },
                { icon: "🎨", title: "Visualize", desc: "Template slides or AI-generated video clips" },
                { icon: "🎬", title: "Compose", desc: "Narration + visuals stitched into a final video" },
              ].map((item, i) => (
                <div
                  key={i}
                  className="p-4 rounded-xl bg-gray-900/40 border border-gray-800"
                >
                  <div className="text-2xl mb-2">{item.icon}</div>
                  <h4 className="font-semibold text-sm text-gray-300">{item.title}</h4>
                  <p className="text-xs text-gray-600 mt-1">{item.desc}</p>
                </div>
              ))}
            </div>
          </div>
        ) : (
          /* Results view */
          <div>
            <button
              onClick={() => {
                setResult(null);
                setStep(-1);
                setInputText("");
                setFile(null);
              }}
              className="text-sm text-gray-500 hover:text-gray-300 mb-6 flex items-center gap-1 transition"
            >
              ← New briefing
            </button>

            <h2 className="text-2xl font-bold mb-1">{result.briefing?.title}</h2>
            <p className="text-gray-500 text-sm mb-6">{result.briefing?.intro}</p>

            {/* Tabs */}
            <div className="flex gap-1 mb-6 border-b border-gray-800">
              {["video", "slides", "script"].map((t) => (
                <button
                  key={t}
                  onClick={() => setTab(t)}
                  className={`px-4 py-2 text-sm font-medium capitalize transition ${
                    tab === t
                      ? "text-violet-400 border-b-2 border-violet-400"
                      : "text-gray-500 hover:text-gray-300"
                  }`}
                >
                  {t}
                </button>
              ))}
            </div>

            {/* Video */}
            {tab === "video" && result.video && (
              <div className="rounded-xl overflow-hidden bg-gray-900 border border-gray-800">
                <video
                  controls
                  className="w-full"
                  src={result.video}
                />
                <div className="px-4 py-3 flex justify-end">
                  <a
                    href={result.video}
                    download
                    className="text-xs text-violet-400 hover:text-violet-300 transition"
                  >
                    Download MP4
                  </a>
                </div>
              </div>
            )}

            {/* Slides */}
            {tab === "slides" && <SlideViewer slides={result.slides} />}

            {/* Script */}
            {tab === "script" && (
              <pre className="p-5 rounded-xl bg-gray-900 border border-gray-800 text-gray-400 text-sm whitespace-pre-wrap leading-relaxed overflow-auto max-h-96">
                {result.script}
              </pre>
            )}

            {/* Sections */}
            <div className="mt-8 space-y-4">
              <h3 className="text-lg font-semibold text-gray-300">Briefing Sections</h3>
              {result.briefing?.sections?.map((section, i) => (
                <div
                  key={i}
                  className="p-4 rounded-xl bg-gray-900/40 border border-gray-800"
                >
                  <h4 className="font-medium text-gray-200 mb-2">
                    {i + 1}. {section.title}
                  </h4>
                  <ul className="space-y-1">
                    {section.bullets?.map((b, j) => (
                      <li key={j} className="text-sm text-gray-500 flex gap-2">
                        <span className="text-gray-700">•</span>
                        {b}
                      </li>
                    ))}
                  </ul>
                </div>
              ))}
            </div>
          </div>
        )}
      </main>

      {/* Footer */}
      <footer className="border-t border-gray-800 px-6 py-4 mt-20">
        <div className="max-w-5xl mx-auto flex justify-between text-xs text-gray-700">
          <span>BriefCast Content Briefing System</span>
          <span>Open-source • BART + FFmpeg + pyttsx3</span>
        </div>
      </footer>
    </div>
  );
}
