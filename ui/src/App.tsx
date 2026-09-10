import React, { useEffect, useMemo, useRef, useState } from "react";
import { clsx } from "clsx";
import { Loader2, Play, Upload, Activity, Power, FileText, Image, ShieldAlert, X, BookOpen } from "lucide-react";
import vectorLogo from "./assets/Vector Logo_Bilingual_White_Horizontal.png";
import fairsenseLogo from "./assets/fairsense-logo.png";
import aixpertLogo from "./assets/AIXPERT_logo_extended_white-2048x896.png";
import { useNavigate, useSearchParams } from "react-router-dom";
import { analyzeStart, analyzeFileStart, connectToStream, health, API_BASE } from "./api";

const LinkedInIcon = ({ size = 16 }: { size?: number }) => (
  <svg width={size} height={size} viewBox="0 0 24 24" fill="currentColor">
    <path d="M16 8a6 6 0 0 1 6 6v7h-4v-7a2 2 0 0 0-2-2 2 2 0 0 0-2 2v7h-4v-7a6 6 0 0 1 6-6z" />
    <rect x="2" y="9" width="4" height="12" />
    <circle cx="4" cy="4" r="2" />
  </svg>
);

const XIcon = ({ size = 16 }: { size?: number }) => (
  <svg width={size} height={size} viewBox="0 0 24 24" fill="currentColor">
    <path d="M18.244 2.25h3.308l-7.227 8.26 8.502 11.24H16.17l-4.714-6.231-5.401 6.231H2.744l7.73-8.835L1.254 2.25H8.08l4.713 6.231zm-1.161 17.52h1.833L7.084 4.126H5.117z" />
  </svg>
);

const BlueskyIcon = ({ size = 16 }: { size?: number }) => (
  <svg width={size} height={size} viewBox="0 0 24 24" fill="currentColor">
    <path d="M12 10.8c-1.087-2.114-4.046-6.053-6.798-7.995C2.566.944 1.561 1.266.902 1.565.139 1.908 0 3.08 0 3.768c0 .69.378 5.65.567 6.479.737 3.123 3.419 4.056 5.977 3.529-.005.039-.01.077-.014.116C2.535 14.315.733 16.37.58 18.409c-.206 2.763 2.43 5.765 5.77 4.578 2.668-.948 4.888-3.77 6.65-6.875 1.762 3.104 3.982 5.927 6.65 6.875 3.34 1.187 5.976-1.815 5.77-4.578-.153-2.038-1.955-4.094-5.95-4.515a7.422 7.422 0 0 1-.014-.116c2.558.527 5.24-.406 5.977-3.529C23.622 9.417 24 4.457 24 3.768c0-.688-.139-1.86-.902-2.203-.659-.299-1.664-.621-4.3 1.24C16.046 4.747 13.087 8.686 12 10.8Z" />
  </svg>
);

type Mode = "text" | "image" | "csv";

const MODE_LABELS: Record<Mode, string> = {
  text: "Bias (Text)",
  image: "Bias (Image)",
  csv: "Risk"
};

const MODE_ICONS: Record<Mode, React.ReactNode> = {
  text: <FileText size={14} />,
  image: <Image size={14} />,
  csv: <ShieldAlert size={14} />
};

const MODE_DESCRIPTIONS: Record<Mode, { summary: string; details: string }> = {
  text: {
    summary: "Identifies bias in written content such as job postings and conversations.",
    details: "Detects gender, racial, age, disability, and socioeconomic biases in free-form text. The agent plans its analysis, selects embedding and LLM tools, and produces highlighted spans with severity ratings and explanations for each detected instance.",
  },
  image: {
    summary: "Analyzes visual content for stereotypes and representation issues.",
    details: "Uses vision-language models (VLMs) to examine images for biased visual elements — such as stereotyped portrayals, underrepresentation, or harmful associations. Returns annotated results with per-instance explanations drawn from the visual context.",
  },
  csv: {
    summary: "Evaluates ML deployment scenarios for fairness, security, and compliance risks.",
    details: "Accepts natural language descriptions or structured CSV data describing an AI deployment. The agent scores risks across dimensions including algorithmic fairness, data bias, regulatory compliance, and security exposure, returning ranked risk cards with mitigation suggestions.",
  },
};

const TEXT_DEMOS: { label: string; text: string }[] = [
  {
    label: "Biased job posting",
    text: `We are looking for a young, ambitious rockstar developer to join our fast-paced startup. The ideal candidate is a recent grad who can hustle hard and thrives in a competitive bro culture. Native English speakers only. Must be willing to work 70+ hours a week — no family obligations should get in the way. The right man for the job earns $130K+. Women need not apply for this senior role.`,
  },
  {
    label: "Gendered performance review",
    text: `Sarah is technically competent but often comes across as too emotional and aggressive during team meetings. She needs to learn to be more collaborative and likeable, the way her male colleagues are. Her communication style is off-putting to senior leadership. Despite her qualifications, she lacks the executive presence we expect at this level and should consider whether management is really the right path for her.`,
  },
];

const RISK_DEMOS: { label: string; text: string }[] = [
  {
    label: "Automated hiring system",
    text: `An automated resume screening model trained on historical hiring decisions from 2000–2018 at a Fortune 500 financial services firm. The model predicts candidate success using features including university prestige ranking, prior employer tier, and applicant names. It is used to shortlist 50,000 applicants per year with no human review at the screening stage. No disparate impact analysis has been conducted.`,
  },
  {
    label: "Retail facial recognition",
    text: `A facial recognition system deployed across 300 retail locations to flag potential shoplifting suspects in real time. The model was trained on a law enforcement mugshot database and sends automatic alerts to security staff when a customer matches with confidence above 70%. Customers are not informed of the system's use, no opt-out mechanism exists, and the system has not been audited for demographic accuracy disparities.`,
  },
];

const DEMO_IMAGE_SVGs = {
  jobAd: `<svg xmlns="http://www.w3.org/2000/svg" width="800" height="560" font-family="Arial, sans-serif">
  <rect width="800" height="560" fill="#ffffff"/>
  <rect x="0" y="0" width="800" height="90" fill="#1a365d"/>
  <text x="400" y="58" font-size="32" font-weight="bold" fill="white" text-anchor="middle">NOW HIRING</text>
  <text x="400" y="82" font-size="14" fill="#90cdf4" text-anchor="middle">TechBros Inc. — Move Fast and Break Things</text>
  <text x="400" y="135" font-size="24" font-weight="bold" fill="#1a202c" text-anchor="middle">Software Engineer — Rock Star Developer</text>
  <line x1="60" y1="152" x2="740" y2="152" stroke="#e2e8f0" stroke-width="2"/>
  <text x="60" y="190" font-size="15" fill="#4a5568">Are you a young, hungry developer ready to hustle 24/7? We want an aggressive go-getter</text>
  <text x="60" y="215" font-size="15" fill="#4a5568">who fits our bro culture. Native English speakers strongly preferred.</text>
  <text x="60" y="255" font-size="16" font-weight="bold" fill="#2d3748">Requirements:</text>
  <text x="80" y="285" font-size="15" fill="#4a5568">• Recent grad preferred — Class of 2021 or later, age 22–28</text>
  <text x="80" y="313" font-size="15" fill="#4a5568">• Willing to work 70+ hrs/week — no family obligations should interfere</text>
  <text x="80" y="341" font-size="15" fill="#4a5568">• Strong "cultural fit" — we're a tight-knit brotherhood</text>
  <text x="80" y="369" font-size="15" fill="#4a5568">• The right man for the job can earn $140K+</text>
  <text x="80" y="397" font-size="15" fill="#4a5568">• Physically fit and high-energy — remote work not available</text>
  <line x1="60" y1="430" x2="740" y2="430" stroke="#e2e8f0" stroke-width="1"/>
  <rect x="270" y="450" width="260" height="46" rx="8" fill="#1a365d"/>
  <text x="400" y="479" font-size="16" font-weight="bold" fill="white" text-anchor="middle">Apply at careers.techbros.io</text>
  <text x="400" y="530" font-size="12" fill="#a0aec0" text-anchor="middle">Only shortlisted candidates will be contacted. We are an equal opportunity employer.*</text>
  <text x="400" y="550" font-size="10" fill="#cbd5e0" text-anchor="middle">*Subject to cultural fit requirements</text>
</svg>`,

  teamPhoto: `<svg xmlns="http://www.w3.org/2000/svg" width="800" height="560" font-family="Arial, sans-serif">
  <rect width="800" height="560" fill="#f8fafc"/>
  <rect x="0" y="0" width="800" height="70" fill="#2d3748"/>
  <text x="400" y="44" font-size="24" font-weight="bold" fill="white" text-anchor="middle">GlobalVentures Corp — Leadership Team 2024</text>
  <text x="60" y="110" font-size="13" font-weight="bold" fill="#718096" letter-spacing="2">EXECUTIVE LEADERSHIP</text>
  <circle cx="130" cy="185" r="48" fill="#4a5568"/>
  <rect x="83" y="237" width="94" height="6" rx="3" fill="#718096"/>
  <text x="130" y="305" font-size="13" font-weight="bold" fill="#1a202c" text-anchor="middle">William Parker</text>
  <text x="130" y="323" font-size="12" fill="#718096" text-anchor="middle">Chief Executive Officer</text>
  <circle cx="290" cy="185" r="48" fill="#4a5568"/>
  <rect x="243" y="237" width="94" height="6" rx="3" fill="#718096"/>
  <text x="290" y="305" font-size="13" font-weight="bold" fill="#1a202c" text-anchor="middle">James Mitchell</text>
  <text x="290" y="323" font-size="12" fill="#718096" text-anchor="middle">Chief Technology Officer</text>
  <circle cx="450" cy="185" r="48" fill="#4a5568"/>
  <rect x="403" y="237" width="94" height="6" rx="3" fill="#718096"/>
  <text x="450" y="305" font-size="13" font-weight="bold" fill="#1a202c" text-anchor="middle">Robert Chen</text>
  <text x="450" y="323" font-size="12" fill="#718096" text-anchor="middle">Chief Financial Officer</text>
  <circle cx="610" cy="185" r="48" fill="#4a5568"/>
  <rect x="563" y="237" width="94" height="6" rx="3" fill="#718096"/>
  <text x="610" y="305" font-size="13" font-weight="bold" fill="#1a202c" text-anchor="middle">David Thompson</text>
  <text x="610" y="323" font-size="12" fill="#718096" text-anchor="middle">VP Engineering</text>
  <line x1="60" y1="355" x2="740" y2="355" stroke="#e2e8f0" stroke-width="1"/>
  <text x="60" y="380" font-size="13" font-weight="bold" fill="#718096" letter-spacing="2">SUPPORT &amp; OPERATIONS</text>
  <circle cx="200" cy="440" r="30" fill="#9b2c2c" opacity="0.5"/>
  <text x="200" y="490" font-size="12" font-weight="bold" fill="#1a202c" text-anchor="middle">Mary Johnson</text>
  <text x="200" y="507" font-size="11" fill="#718096" text-anchor="middle">Executive Assistant</text>
  <circle cx="400" cy="440" r="30" fill="#9b2c2c" opacity="0.5"/>
  <text x="400" y="490" font-size="12" font-weight="bold" fill="#1a202c" text-anchor="middle">Lisa Wang</text>
  <text x="400" y="507" font-size="11" fill="#718096" text-anchor="middle">HR Coordinator</text>
  <circle cx="600" cy="440" r="30" fill="#9b2c2c" opacity="0.5"/>
  <text x="600" y="490" font-size="12" font-weight="bold" fill="#1a202c" text-anchor="middle">Sarah Miller</text>
  <text x="600" y="507" font-size="11" fill="#718096" text-anchor="middle">Office Manager</text>
</svg>`,
};

async function createDemoImageFile(svgString: string, filename: string): Promise<File> {
  return new Promise((resolve, reject) => {
    const svgBlob = new Blob([svgString], { type: "image/svg+xml;charset=utf-8" });
    const url = URL.createObjectURL(svgBlob);
    const cleanup = () => URL.revokeObjectURL(url);
    const img = new window.Image();
    img.onload = () => {
      try {
        const canvas = document.createElement("canvas");
        canvas.width = 800;
        canvas.height = 560;
        const ctx = canvas.getContext("2d");
        if (!ctx) {
          reject(new Error("Failed to create image preview: 2D canvas context unavailable."));
          return;
        }
        ctx.fillStyle = "#ffffff";
        ctx.fillRect(0, 0, 800, 560);
        ctx.drawImage(img, 0, 0);
        canvas.toBlob((blob) => {
          if (!blob) {
            reject(new Error("Failed to create image preview: PNG conversion returned no data."));
            return;
          }
          resolve(new File([blob], filename, { type: "image/png" }));
        }, "image/png");
      } catch (err) {
        reject(err instanceof Error ? err : new Error("Failed to create image preview."));
      } finally {
        cleanup();
      }
    };
    img.onerror = () => {
      cleanup();
      reject(new Error("Failed to create image preview: SVG could not be loaded."));
    };
    img.src = url;
  });
}

interface TimelineEntry {
  timestamp: number;
  event: string;
  level: string;
  context: Record<string, unknown>;
}

const VALID_MODES: Mode[] = ["text", "image", "csv"];

export default function App() {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const modeParam = searchParams.get("mode");
  const initialMode: Mode = VALID_MODES.includes(modeParam as Mode) ? (modeParam as Mode) : "text";
  const [mode, setMode] = useState<Mode>(initialMode);
  const [input, setInput] = useState("");
  const [file, setFile] = useState<File | null>(null);
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<any | null>(null);
  const [timeline, setTimeline] = useState<TimelineEntry[]>([]);
  const [showLoadingBanner, setShowLoadingBanner] = useState(false);
  const [loadingMessage, setLoadingMessage] = useState("");
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [mockProvider, setMockProvider] = useState<string | null>(null);

  // Surface mock mode prominently: with FAIRSENSE_LLM_PROVIDER=fake the backend
  // returns synthetic placeholder results that look like a real analysis.
  useEffect(() => {
    health()
      .then((h) => setMockProvider(h.mock_mode ? h.llm_provider : null))
      .catch(() => setMockProvider(null));
  }, []);
  const [showShutdownModal, setShowShutdownModal] = useState(false);
  const [showAboutModal, setShowAboutModal] = useState(false);
  const wsRef = useRef<WebSocket | null>(null);

  useEffect(() => {
    return () => {
      wsRef.current?.close();
    };
  }, []);

  // Detect model download events from timeline and show loading banner
  useEffect(() => {
    const latestEvent = timeline[timeline.length - 1];
    if (!latestEvent) return;

    // Check for model download start event
    if (latestEvent.event === "model_download_start") {
      const modelName = latestEvent.context?.model_name || "AI model";
      setLoadingMessage(`⏳ Downloading ${modelName} (first use only, ~30-120s)...`);
      setShowLoadingBanner(true);
    }

    // Check for model download complete event
    if (latestEvent.event === "model_download_complete") {
      setShowLoadingBanner(false);
      setLoadingMessage("");
    }

    // Check for model download failure
    if (latestEvent.event === "model_download_failed") {
      setShowLoadingBanner(false);
      setLoadingMessage("");
      // Error is already displayed in timeline, no need for banner
    }
  }, [timeline]);

  const canSubmit =
    (!loading && mode !== "image" && input.trim().length > 0) ||
    (!loading && mode === "image" && file);

  async function handleAnalyze() {
    if (!canSubmit) {
      return;
    }
    setLoading(true);
    setTimeline([]);
    setResult(null);

    try {
      // Step 1: Start analysis and get run_id immediately (fixes race condition!)
      const startResponse =
        mode === "image"
          ? await analyzeFileStart(file as File, "bias_image")
          : await analyzeStart({
            content: input,
            input_type: mode === "csv" ? "risk" : undefined
          });

      const runId = startResponse.run_id;

      // Step 2: Connect WebSocket BEFORE analysis completes (this is the fix!)
      const ws = connectToStream(runId, (evt) => {
        try {
          const data = JSON.parse(evt.data);

          // Check if this is the completion event
          if (data.event === "analysis_complete" && data.context?.result) {
            // Extract final result from completion event
            setResult(data.context.result);
            setLoading(false); // Stop loading spinner
          }

          // Check if this is an error event
          if (data.event === "analysis_error") {
            setErrorMessage(data.context?.message ? String(data.context.message) : "Analysis failed. Check the timeline for details.");
            setLoading(false); // Stop loading spinner
          }

          // Add all events to timeline (including intermediate agent events)
          setTimeline((prev) => [...prev, data]);
        } catch {
          // ignore malformed payloads
        }
      });

      wsRef.current = ws;

      // Step 3: Analysis is now running in background, events will stream in!
    } catch (err) {
      console.error(err);
      setErrorMessage("Analysis failed. Check logs for details.");
      setLoading(false);
    }
  }

  function handleShutdown() {
    setShowShutdownModal(true);
  }

  async function executeShutdown() {
    setShowShutdownModal(false);
    try {
      const response = await fetch(`${API_BASE}/v1/shutdown`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
      });

      if (response.ok) {
        wsRef.current?.close();
        setErrorMessage(null);
      } else {
        setErrorMessage("Failed to shutdown server. Check console for details.");
      }
    } catch (err) {
      console.error("Shutdown error:", err);
      setErrorMessage("Error communicating with server. It may have already shut down.");
    }
  }

  const highlightHtml = useMemo(() => {
    if (!result?.bias_result?.highlighted_html) {
      return null;
    }
    return { __html: result.bias_result.highlighted_html };
  }, [result]);

  return (
    <main className="min-h-screen bg-base text-white">
      <nav className="flex items-center justify-between px-8 py-5 border-b border-slate-800">
        <button onClick={() => navigate("/")} className="flex items-center gap-2">
          <img
            src={fairsenseLogo}
            alt="FairSense AgentiX"
            className="h-12 mix-blend-screen hover:opacity-80 transition-opacity"
          />
          <span className="text-lg font-semibold">FairSense AgentiX</span>
        </button>
        <div className="flex items-center gap-4">
          <a href="https://aixpert-project.eu/" target="_blank" rel="noopener noreferrer">
            <img
              src={aixpertLogo}
              alt="AIxpert"
              className="h-8 opacity-70 hover:opacity-100 transition-opacity"
            />
          </a>
          <div className="w-px h-5 bg-slate-700" />
          <a href="https://vectorinstitute.ai/" target="_blank" rel="noopener noreferrer">
            <img
              src={vectorLogo}
              alt="Vector Institute"
              className="h-7 opacity-70 hover:opacity-100 transition-opacity"
            />
          </a>
          <button
            onClick={handleShutdown}
            className="flex items-center gap-2 rounded-xl border border-red-700/50 bg-red-900/20 px-4 py-2 text-sm text-red-300 hover:bg-red-900/40 hover:border-red-600 transition-colors"
            title="Shutdown both backend and frontend servers"
          >
            <Power size={16} />
            Shutdown
          </button>
        </div>
      </nav>
      <div className="px-8 py-8">

      {/* Mock-mode banner */}
      {mockProvider && (
        <div className="mb-6 rounded-xl border border-amber-600/60 bg-amber-900/30 px-4 py-3 text-sm text-amber-200">
          <strong>Mock mode:</strong> the backend is running with{" "}
          <code>FAIRSENSE_LLM_PROVIDER={mockProvider}</code>. Results shown here are synthetic
          placeholders, not a real analysis. Set <code>FAIRSENSE_LLM_PROVIDER</code> and{" "}
          <code>FAIRSENSE_LLM_API_KEY</code> and restart the server for real results.
        </div>
      )}

      {/* Inline error banner */}
      {errorMessage && (
        <div className="mb-6 flex items-start gap-3 rounded-xl border border-red-700/50 bg-red-900/20 px-4 py-3 text-sm text-red-300">
          <span className="flex-1">{errorMessage}</span>
          <button onClick={() => setErrorMessage(null)} className="flex-shrink-0 text-red-400 hover:text-red-200 transition-colors">
            <X size={16} />
          </button>
        </div>
      )}

      {/* Model Download Loading Banner */}
      {showLoadingBanner && (
        <div className="mb-6 bg-yellow-500/10 border-2 border-yellow-500/50 rounded-xl p-6">
          <div className="flex items-start gap-4">
            <Loader2 className="text-yellow-400 animate-spin flex-shrink-0 mt-1" size={24} />
            <div className="flex-1">
              <p className="text-lg font-semibold text-yellow-300">{loadingMessage}</p>
              <p className="text-sm text-slate-400 mt-2">
                This is a one-time download. Future requests will be instant (~100ms).
              </p>
              <p className="text-xs text-slate-500 mt-1">
                The AI model is being downloaded from HuggingFace and cached locally.
              </p>
            </div>
          </div>
        </div>
      )}

      <section className="grid gap-8 lg:grid-cols-2">
        <div className="space-y-6">
          <ModeSelector mode={mode} onModeChange={setMode} />
          <ModeDescription mode={mode} />
          {mode === "image" ? (
            <ImageDropzone file={file} onFileChange={setFile} />
          ) : (
            <textarea
              className="w-full min-h-[220px] glass p-4 focus:outline-none focus:ring-2 focus:ring-accent-200"
              placeholder={
                mode === "csv"
                  ? "Describe your deployment scenario or paste CSV text..."
                  : "Paste your job posting or conversation snippet..."
              }
              value={input}
              onChange={(e) => setInput(e.target.value)}
            />
          )}
          <div className="flex gap-4">
            <button
              disabled={!canSubmit}
              onClick={handleAnalyze}
              className={clsx(
                "flex items-center gap-2 rounded-xl px-5 py-3 font-medium transition",
                canSubmit
                  ? "bg-gradient-to-r from-accent-200 to-accent-100 text-black"
                  : "bg-panel text-slate-500 cursor-not-allowed"
              )}
            >
              {loading ? (
                <>
                  <Loader2 className="animate-spin" /> Analyzing…
                </>
              ) : (
                <>
                  <Play size={16} /> Run Analysis
                </>
              )}
            </button>
            <button
              className="rounded-xl border border-slate-700 px-4 py-3 text-sm text-slate-300 hover:border-slate-500 hover:bg-slate-800 transition-colors"
              onClick={() => {
                setInput("");
                setFile(null);
                setResult(null);
                setTimeline([]);
              }}
            >
              Reset
            </button>
          </div>

          <TimelinePanel events={timeline} />
        </div>

        <div className="space-y-6">
          {!result && (
            <div className="glass p-5 space-y-4">
              <p className="text-xs font-semibold uppercase tracking-widest text-slate-500">Try an example</p>
              {mode === "image" ? (
                <div className="grid grid-cols-2 gap-3">
                  {([
                    { key: "jobAd" as const, label: "Biased job advertisement", desc: "Text-based ad with gendered language" },
                    { key: "teamPhoto" as const, label: "Leadership team photo", desc: "Org chart with representation gap" },
                  ]).map((demo) => (
                    <button
                      key={demo.key}
                      onClick={async () => {
                        try {
                          const f = await createDemoImageFile(DEMO_IMAGE_SVGs[demo.key], `${demo.key}.png`);
                          setFile(f);
                        } catch (err) {
                          setError(err instanceof Error ? err.message : "Failed to load demo image.");
                        }
                      }}
                      className="group overflow-hidden rounded-xl border border-slate-700 hover:border-accent-200/50 transition-colors text-left"
                    >
                      <img
                        src={`data:image/svg+xml;charset=utf-8,${encodeURIComponent(DEMO_IMAGE_SVGs[demo.key])}`}
                        alt={demo.label}
                        className="w-full h-16 object-cover object-top"
                      />
                      <div className="px-3 py-2 bg-slate-900/80">
                        <p className="text-xs font-medium text-slate-200">{demo.label}</p>
                        <p className="text-xs text-slate-500 mt-0.5">{demo.desc}</p>
                      </div>
                    </button>
                  ))}
                </div>
              ) : (
                <div className="flex flex-wrap gap-2">
                  {(mode === "text" ? TEXT_DEMOS : RISK_DEMOS).map((demo) => (
                    <button
                      key={demo.label}
                      onClick={() => setInput(demo.text)}
                      className="text-xs rounded-lg border border-slate-700 px-3 py-1.5 text-slate-400 hover:border-accent-200/50 hover:text-accent-200 transition-colors"
                    >
                      {demo.label}
                    </button>
                  ))}
                </div>
              )}
            </div>
          )}
          <ResultPanel result={result} />
          {highlightHtml && (
            <div className="glass p-5 space-y-5">
              <header>
                <h3 className="text-sm uppercase tracking-wide text-slate-400 flex items-center gap-2">
                  <span className="inline-block w-1 h-4 bg-accent-200 rounded-full" />
                  {result?.bias_result?.image_base64 ? "Visual Analysis" : "Highlighted Text"}
                </h3>
              </header>

              <BiasLegend />

              {/* Display image if available (for VLM image analysis) */}
              {result?.bias_result?.image_base64 && (
                <div className="analyzed-image-container">
                  <img
                    src={result.bias_result.image_base64}
                    alt="Analyzed image"
                    className="analyzed-image"
                  />
                </div>
              )}

              <div
                className="custom-scrollbar max-h-[500px] overflow-y-auto pr-2"
                dangerouslySetInnerHTML={highlightHtml}
              />
            </div>
          )}
        </div>
      </section>
      {/* Footer */}
      <footer className="mt-12 border-t border-slate-800 pt-6 pb-4 flex items-center justify-between">
        <div className="flex items-center gap-6 text-xs text-slate-500">
          <span>Built as part of&nbsp;
            <a
              href="https://vectorinstitute.github.io/vector-aixpert/"
              target="_blank"
              rel="noopener noreferrer"
              className="text-slate-400 hover:text-accent-200 transition-colors"
            >
              Vector AIxpert
            </a>
          </span>
          <a
            href="https://vectorinstitute.github.io/fairsense-agentix/"
            target="_blank"
            rel="noopener noreferrer"
            className="flex items-center gap-1.5 text-slate-400 hover:text-accent-200 transition-colors"
          >
            <BookOpen size={13} />
            Documentation
          </a>
          <button
            onClick={() => setShowAboutModal(true)}
            className="text-slate-400 hover:text-accent-200 transition-colors"
          >
            About
          </button>
        </div>
        <div className="flex items-center gap-4">
          <a href="https://www.linkedin.com/company/vector-institute/" target="_blank" rel="noopener noreferrer" className="text-slate-500 hover:text-accent-200 transition-colors" title="LinkedIn">
            <LinkedInIcon size={16} />
          </a>
          <a href="https://x.com/vectorinst" target="_blank" rel="noopener noreferrer" className="text-slate-500 hover:text-accent-200 transition-colors" title="X / Twitter">
            <XIcon size={16} />
          </a>
          <a href="https://bsky.app/profile/vectorinstitute.ai" target="_blank" rel="noopener noreferrer" className="text-slate-500 hover:text-accent-200 transition-colors" title="Bluesky">
            <BlueskyIcon size={16} />
          </a>
        </div>
      </footer>
      </div>

      {/* About modal */}
      {showAboutModal && <AboutModal onClose={() => setShowAboutModal(false)} />}

      {/* Shutdown confirmation modal */}
      {showShutdownModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm">
          <div className="glass w-full max-w-md p-6 space-y-4">
            <div className="flex items-center justify-between">
              <h2 className="text-lg font-semibold text-slate-100">Shutdown server?</h2>
              <button onClick={() => setShowShutdownModal(false)} className="text-slate-400 hover:text-slate-200 transition-colors">
                <X size={18} />
              </button>
            </div>
            <p className="text-sm text-slate-400 leading-relaxed">
              This will stop both the backend and frontend servers. You'll need to restart manually to use the application again.
            </p>
            <div className="flex justify-end gap-3 pt-2">
              <button
                onClick={() => setShowShutdownModal(false)}
                className="rounded-xl border border-slate-700 px-4 py-2 text-sm text-slate-300 hover:bg-slate-800 hover:border-slate-500 transition-colors"
              >
                Cancel
              </button>
              <button
                onClick={executeShutdown}
                className="flex items-center gap-2 rounded-xl border border-red-700/50 bg-red-900/20 px-4 py-2 text-sm text-red-300 hover:bg-red-900/40 hover:border-red-600 transition-colors"
              >
                <Power size={14} />
                Shutdown
              </button>
            </div>
          </div>
        </div>
      )}
    </main>
  );
}

function ModeSelector({
  mode,
  onModeChange
}: {
  mode: Mode;
  onModeChange: (mode: Mode) => void;
}) {
  return (
    <div className="glass flex gap-2 p-2">
      {(Object.keys(MODE_LABELS) as Mode[]).map((key) => (
        <button
          key={key}
          onClick={() => onModeChange(key)}
          className={clsx(
            "flex-1 flex items-center justify-center gap-2 rounded-lg px-4 py-3 text-sm font-semibold transition",
            mode === key ? "bg-accent-200 text-black" : "text-slate-400 hover:text-slate-100 hover:bg-slate-800/50"
          )}
        >
          {MODE_ICONS[key]}
          {MODE_LABELS[key]}
        </button>
      ))}
    </div>
  );
}

function ModeDescription({ mode }: { mode: Mode }) {
  const [expanded, setExpanded] = useState(false);
  const desc = MODE_DESCRIPTIONS[mode];

  useEffect(() => setExpanded(false), [mode]);

  return (
    <div className="rounded-xl border border-slate-800/50 bg-slate-900/30 px-4 py-3 space-y-1">
      <div className="flex items-center justify-between gap-3">
        <p className="text-xs text-slate-400 leading-relaxed">{desc.summary}</p>
        <button
          onClick={() => setExpanded(e => !e)}
          className="flex-shrink-0 text-xs text-accent-200 hover:text-accent-100 transition-colors flex items-center gap-1"
        >
          {expanded ? "Less" : "More"}
          <Play size={9} className={clsx("transition-transform", expanded ? "rotate-90" : "rotate-0")} />
        </button>
      </div>
      {expanded && (
        <p className="text-xs text-slate-500 leading-relaxed border-t border-slate-800/50 pt-2">
          {desc.details}
        </p>
      )}
    </div>
  );
}

function ImageDropzone({
  file,
  onFileChange
}: {
  file: File | null;
  onFileChange: (f: File | null) => void;
}) {
  const previewUrl = useMemo(() => (file ? URL.createObjectURL(file) : null), [file]);

  useEffect(() => {
    return () => {
      if (previewUrl) URL.revokeObjectURL(previewUrl);
    };
  }, [previewUrl]);

  return (
    <label className="glass flex cursor-pointer flex-col items-center justify-center gap-3 p-6 text-slate-400 hover:border-slate-500 transition-colors">
      {previewUrl ? (
        <>
          <img
            src={previewUrl}
            alt="Selected preview"
            className="max-h-48 max-w-full rounded-lg object-contain opacity-90"
          />
          <span className="text-xs text-slate-400 truncate max-w-full px-2">{file!.name}</span>
        </>
      ) : (
        <>
          <Upload />
          <span>Drop an image or click to browse</span>
        </>
      )}
      <input
        type="file"
        accept="image/*"
        className="hidden"
        onChange={(e) => onFileChange(e.target.files?.[0] ?? null)}
      />
    </label>
  );
}

const EVENT_LABELS: Record<string, string> = {
  router_decision:        "Router Decision",
  llm_call:               "LLM Call",
  model_download_start:   "Downloading Model",
  model_download_complete:"Model Ready",
  model_download_failed:  "Download Failed",
  analysis_complete:      "Analysis Complete",
  analysis_error:         "Analysis Error",
  log_info:               "Info",
  log_warning:            "Warning",
};

const EVENT_DOT: Record<string, string> = {
  analysis_complete:      "bg-green-400",
  model_download_complete:"bg-green-400",
  analysis_error:         "bg-red-400",
  model_download_failed:  "bg-red-400",
  log_warning:            "bg-yellow-400",
  model_download_start:   "bg-yellow-400",
};

function eventDot(event: string) {
  return EVENT_DOT[event] ?? "bg-slate-500";
}

function eventLabel(event: string) {
  return EVENT_LABELS[event] ?? event.replace(/_/g, " ").replace(/\b\w/g, c => c.toUpperCase());
}

function TimelinePanel({ events }: { events: TimelineEntry[] }) {
  const [expandedEvents, setExpandedEvents] = useState<Set<number>>(new Set());
  const bottomRef = useRef<HTMLLIElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth", block: "nearest" });
  }, [events]);

  if (!events.length) {
    return (
      <div className="glass px-4 py-6 text-center text-slate-400">
        Agentic flow will appear here.
      </div>
    );
  }

  const toggleEvent = (idx: number) => {
    setExpandedEvents((prev) => {
      const next = new Set(prev);
      if (next.has(idx)) {
        next.delete(idx);
      } else {
        next.add(idx);
      }
      return next;
    });
  };

  return (
    <div className="glass p-4 space-y-3 flex flex-col max-h-[calc(100vh-32rem)] min-h-[200px]">
      <h3 className="flex items-center gap-2 text-sm font-semibold text-slate-300 flex-shrink-0">
        <Activity size={16} /> Agent Timeline
      </h3>
      <ol className="space-y-3 text-sm overflow-y-auto custom-scrollbar flex-1 pr-2">
        {events.map((evt, idx) => {
          const isExpanded = expandedEvents.has(idx);
          const hasContext = evt.context && Object.keys(evt.context).length > 0;

          // Extract key context fields for display
          const contextEntries = evt.context ? Object.entries(evt.context) : [];
          const contextFieldsToShow = contextEntries.filter(
            ([key]) => !["run_id", "result"].includes(key)
          );

          // Extract message safely for type-checking
          const message = evt.context?.message;
          const messageText = message ? String(message) : null;

          return (
            <li ref={idx === events.length - 1 ? bottomRef : null} key={`${evt.timestamp}-${idx}`} className={clsx(
                "rounded-xl border p-3 transition-colors",
                evt.event === "analysis_error" || evt.event === "model_download_failed"
                  ? "bg-red-900/20 border-red-700/40 hover:bg-red-900/30"
                  : evt.event === "analysis_complete" || evt.event === "model_download_complete"
                  ? "bg-green-900/20 border-green-700/40 hover:bg-green-900/30"
                  : "bg-slate-900/40 border-slate-800/40 hover:bg-slate-900/60"
              )}>
              <div className="flex items-center justify-between">
                <span className="flex items-center gap-2 text-xs font-semibold text-slate-200">
                  <span className={clsx("inline-block h-2 w-2 rounded-full flex-shrink-0", eventDot(evt.event))} />
                  {eventLabel(evt.event)}
                </span>
                <span className="text-xs text-slate-500">
                  {new Date(evt.timestamp * 1000).toLocaleTimeString()}
                </span>
              </div>

              {messageText && (
                <p className="text-slate-300 mt-2 text-xs leading-relaxed">
                  {messageText}
                </p>
              )}

              {hasContext && contextFieldsToShow.length > 0 && (
                <div className="mt-2">
                  <button
                    onClick={() => toggleEvent(idx)}
                    className="flex items-center gap-1 text-xs text-accent-200 hover:text-accent-100 transition"
                  >
                    <Activity size={12} />
                    <span>{isExpanded ? "Hide" : "Show"} details</span>
                    <Play
                      size={10}
                      className={clsx(
                        "transition-transform",
                        isExpanded ? "rotate-90" : "rotate-0"
                      )}
                    />
                  </button>

                  {isExpanded && (
                    <div className="mt-2 space-y-1 pl-3 border-l-2 border-slate-700">
                      {contextFieldsToShow.map(([key, value]) => (
                        <div key={key} className="text-xs">
                          <span className="text-slate-500 font-mono">{key}:</span>{" "}
                          <span className="text-slate-300">
                            {typeof value === "object" && value !== null
                              ? JSON.stringify(value, null, 2)
                              : String(value)}
                          </span>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              )}
            </li>
          );
        })}
      </ol>
    </div>
  );
}

function BiasLegend() {
  const biasTypes = [
    { type: "Gender", color: "#FFB3BA", description: "Gendered language or stereotypes" },
    { type: "Age", color: "#FFDFBA", description: "Age-related discrimination" },
    { type: "Racial", color: "#FFFFBA", description: "Racial or ethnic bias" },
    { type: "Disability", color: "#BAE1FF", description: "Ableist language" },
    { type: "Socioeconomic", color: "#E0BBE4", description: "Class-based assumptions" },
  ];

  return (
    <div className="rounded-xl border border-slate-700/30 bg-slate-800/20 p-4">
      <p className="mb-3 text-xs font-semibold uppercase tracking-wider text-slate-500">
        Bias Type Legend
      </p>
      <div className="flex flex-wrap gap-3">
        {biasTypes.map(({ type, color, description }) => (
          <div
            key={type}
            className="flex items-center gap-2 text-sm text-slate-300 transition-colors hover:text-slate-100"
            title={description}
          >
            <span
              className="inline-block h-3 w-3 rounded-sm"
              style={{
                backgroundColor: `${color}40`,
                border: `1.5px solid ${color}`,
              }}
            />
            <span className="text-xs">{type}</span>
          </div>
        ))}
      </div>
    </div>
  );
}

// TODO: Instead of stripping citations, link [N] and (Author et al., YYYY) to their
// source papers using the MIT AI Risk Repository paper metadata. Requires rebuilding
// the FAISS index with paper URLs included in risk metadata.
function stripCitations(text: string): string {
  return text
    .replace(/\[\d+(?:,\s*\d+)*\]/g, "")        // [95, 170], [35]
    .replace(/\([A-Z][^()]*\d{4}[^()]*\)/g, "")  // (Author, 2021), (A and B, 2019; C, 2016), etc.
    .replace(/\s+([.,?!;:])/g, "$1")              // remove space before punctuation
    .replace(/\s{2,}/g, " ")
    .trim();
}

function ResultPanel({ result }: { result: any | null }) {
  const [imageExpanded, setImageExpanded] = useState(false);

  if (!result) {
    return (
      <div className="glass p-6 text-slate-400">
        Run an analysis to view structured output.
      </div>
    );
  }

  if (result.workflow_id === "risk") {
    const risks = result.risk_result?.risks ?? [];
    return (
      <div className="glass p-5 space-y-4">
        <header className="space-y-2">
          <p className="pill">Risk Insights</p>
          <div className="flex items-center justify-between gap-3">
            <h3 className="text-xl font-semibold text-slate-100 flex items-center gap-2">
              <span className="inline-block w-1 h-5 bg-accent-200 rounded-full" />
              Top Risks
            </h3>
            <a
              href="https://airisk.mit.edu/"
              target="_blank"
              rel="noopener noreferrer"
              className="inline-flex items-center gap-1 text-xs text-slate-500 hover:text-accent-200 transition-colors flex-shrink-0"
            >
              <svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6"/><polyline points="15 3 21 3 21 9"/><line x1="10" y1="14" x2="21" y2="3"/></svg>
              MIT AI Risk Repository
            </a>
          </div>
        </header>
        <div className="space-y-3">
          {risks.filter((r: any) => (r.score ?? 0) > 0).slice(0, 5).map((risk: any, idx: number) => (
            <div key={idx} className="rounded-xl border border-slate-800/50 bg-slate-900/30 p-4 space-y-2 hover:border-slate-700/70 transition-colors">
              <div className="flex justify-between items-start gap-3">
                <div className="space-y-1 min-w-0">
                  <p className="text-sm font-semibold text-slate-200 leading-snug">
                    {risk.risk_name ?? risk.name ?? "Unknown Risk"}
                  </p>
                  {risk.category && (
                    <p className="flex items-center gap-1 text-xs text-slate-500 uppercase tracking-wide">
                      {risk.category}
                      {idx === 0 && (
                        <span className="relative group cursor-help inline-flex flex-shrink-0 normal-case tracking-normal text-slate-600 hover:text-slate-400 transition-colors">
                          <svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                            <circle cx="12" cy="12" r="10"/><line x1="12" y1="16" x2="12" y2="12"/><line x1="12" y1="8" x2="12.01" y2="8"/>
                          </svg>
                          <span className="pointer-events-none absolute bottom-full left-1/2 -translate-x-1/2 mb-2 w-64 rounded-lg border border-slate-700 bg-slate-800 px-3 py-2 text-xs text-slate-300 leading-relaxed opacity-0 group-hover:opacity-100 transition-opacity z-50">
                            Risk categories follow the MIT AI Risk Repository Domain Taxonomy. The number (e.g. 3.1) identifies the domain and subcategory.
                          </span>
                        </span>
                      )}
                    </p>
                  )}
                </div>
                <span className="flex-shrink-0 px-2 py-0.5 rounded-full text-xs font-medium bg-accent-200/20 text-accent-200">
                  {risk.score?.toFixed(2)}
                </span>
              </div>
              <p className="text-xs text-slate-400 leading-relaxed">{stripCitations(risk.description ?? risk.text ?? "")}</p>
            </div>
          ))}
        </div>
      </div>
    );
  }

  const summary = result.bias_result?.summary;
  const instances = result.bias_result?.bias_instances ?? [];

  // Try multiple possible paths for image_base64
  const imageBase64 = result.bias_result?.image_base64 || result.image_base64 || result.workflow_result?.image_base64;

  return (
    <div className="glass p-5 space-y-4">
      <header className="space-y-2">
        <p className="pill">Bias Insights</p>
        <h3 className="text-xl font-semibold text-slate-100 flex items-center gap-2">
          <span className="inline-block w-1 h-5 bg-accent-200 rounded-full" />
          {result.bias_result?.status === "success"
            ? "Analysis Complete"
            : "Analysis"}
        </h3>
      </header>

      {/* Collapsible image viewer for visual analysis */}
      {imageBase64 && (
        <div className="space-y-2">
          <button
            onClick={() => setImageExpanded(!imageExpanded)}
            className="flex items-center gap-2 text-xs text-accent-200 hover:text-accent-100 transition-colors"
          >
            <Upload size={14} />
            <span>{imageExpanded ? "Hide" : "View"} Analyzed Image</span>
            <Play
              size={10}
              className={clsx(
                "transition-transform",
                imageExpanded ? "rotate-90" : "rotate-0"
              )}
            />
          </button>

          {imageExpanded && (
            <div className="analyzed-image-container">
              <img
                src={imageBase64}
                alt="Analyzed content"
                className="analyzed-image"
              />
            </div>
          )}
        </div>
      )}

      {summary && <p className="text-slate-300 text-sm leading-relaxed">{summary}</p>}
      <div className="space-y-3">
        {instances.slice(0, 5).map((inst: any, idx: number) => (
          <div key={idx} className="rounded-xl border border-slate-800/50 bg-slate-900/30 p-4 space-y-2 hover:border-slate-700/70 transition-colors">
            <div className="flex items-center justify-between">
              <span className="text-xs font-bold uppercase tracking-wide text-slate-300">{inst.type}</span>
              <span className={clsx(
                "px-2 py-0.5 rounded-full text-xs font-medium",
                inst.severity === "high" && "bg-red-500/20 text-red-300",
                inst.severity === "medium" && "bg-yellow-500/20 text-yellow-300",
                inst.severity === "low" && "bg-blue-500/20 text-blue-300"
              )}>{inst.severity}</span>
            </div>
            <p className="text-sm text-slate-300 leading-relaxed">
              <em>"{inst.visual_element || inst.text_span}"</em>
            </p>
            <p className="text-xs text-slate-400 leading-relaxed">{inst.explanation}</p>
          </div>
        ))}
      </div>
    </div>
  );
}

function AnalysisModesAccordion() {
  const [expanded, setExpanded] = useState<number | null>(null);

  const modes = [
    {
      icon: <FileText size={14} />,
      title: "Text Bias Detection",
      summary: "Identifies bias in written content such as job postings and conversations.",
      details: "Detects gender, racial, age, disability, and socioeconomic biases in free-form text. The agent plans its analysis, selects embedding and LLM tools, and produces highlighted spans with severity ratings and explanations for each detected instance.",
    },
    {
      icon: <Image size={14} />,
      title: "Image Bias Detection",
      summary: "Analyzes visual content for stereotypes and representation issues.",
      details: "Uses vision-language models (VLMs) to examine images for biased visual elements — such as stereotyped portrayals, underrepresentation, or harmful associations. Returns annotated results with per-instance explanations drawn from the visual context.",
    },
    {
      icon: <ShieldAlert size={14} />,
      title: "Risk Assessment",
      summary: "Evaluates ML deployment scenarios for fairness, security, and compliance risks.",
      details: "Accepts natural language descriptions or structured CSV data describing an AI deployment. The agent scores risks across dimensions including algorithmic fairness, data bias, regulatory compliance, and security exposure, returning ranked risk cards with mitigation suggestions.",
    },
  ];

  return (
    <div className="space-y-2">
      <h3 className="text-sm font-semibold uppercase tracking-wider text-slate-400">Multi-Modal Analysis</h3>
      {modes.map((mode, idx) => (
        <div key={idx} className="rounded-xl border border-slate-800/50 bg-slate-900/30 overflow-hidden">
          <button
            onClick={() => setExpanded(expanded === idx ? null : idx)}
            className="w-full flex items-center justify-between px-4 py-3 text-left hover:bg-slate-800/30 transition-colors"
          >
            <div className="flex items-center gap-2">
              <span className="text-accent-200">{mode.icon}</span>
              <div>
                <p className="text-sm font-medium text-slate-200">{mode.title}</p>
                <p className="text-xs text-slate-500 mt-0.5">{mode.summary}</p>
              </div>
            </div>
            <Play
              size={10}
              className={clsx("text-slate-500 flex-shrink-0 ml-3 transition-transform", expanded === idx ? "rotate-90" : "rotate-0")}
            />
          </button>
          {expanded === idx && (
            <div className="px-4 pb-4 pt-1 border-t border-slate-800/50">
              <p className="text-xs text-slate-400 leading-relaxed">{mode.details}</p>
            </div>
          )}
        </div>
      ))}
    </div>
  );
}

function AboutModal({ onClose }: { onClose: () => void }) {
  const [activeTab, setActiveTab] = useState<"about" | "team" | /* "papers" | */ "connect">("about");

  const tabs: { id: typeof activeTab; label: string }[] = [
    { id: "about",   label: "About" },
    { id: "team",    label: "Team" },
    // { id: "papers",  label: "Publications" },
    { id: "connect", label: "Connect" },
  ];

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm p-4">
      <div className="glass w-full max-w-2xl max-h-[80vh] flex flex-col">
        {/* Header */}
        <div className="flex items-center justify-between px-6 pt-6 pb-4 flex-shrink-0">
          <h2 className="text-lg font-semibold text-slate-100">About</h2>
          <button onClick={onClose} className="text-slate-400 hover:text-slate-200 transition-colors">
            <X size={18} />
          </button>
        </div>

        {/* Tabs */}
        <div className="flex gap-1 px-6 pb-4 flex-shrink-0 border-b border-slate-800">
          {tabs.map(tab => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={clsx(
                "rounded-lg px-4 py-2 text-sm font-medium transition-colors",
                activeTab === tab.id
                  ? "bg-accent-200 text-black"
                  : "text-slate-400 hover:text-slate-100 hover:bg-slate-800/50"
              )}
            >
              {tab.label}
            </button>
          ))}
        </div>

        {/* Content */}
        <div className="overflow-y-auto custom-scrollbar flex-1 px-6 py-5 space-y-5">

          {activeTab === "about" && (
            <div className="space-y-6">
              <div className="space-y-2">
                <h3 className="text-sm font-semibold uppercase tracking-wider text-slate-400">Vector Institute</h3>
                <p className="text-sm text-slate-300 leading-relaxed">
                  The Vector Institute is dedicated to advancing artificial intelligence research and translating cutting-edge innovations into real-world solutions. Our open-source projects reflect our commitment to collaboration, transparency, and the responsible deployment of AI technologies.
                </p>
                <p className="text-sm text-slate-300 leading-relaxed">
                  We build tools, MVPs, reference implementations, and educational resources that empower researchers, developers, and organizations to innovate and solve real-world problems with AI — spanning various domains, designed to be accessible, adaptable, and impactful.
                </p>
                <a
                  href="https://github.com/VectorInstitute"
                  target="_blank"
                  rel="noopener noreferrer"
                  className="inline-flex items-center gap-1.5 text-xs text-accent-200 hover:text-accent-100 transition-colors"
                >
                  <BookOpen size={12} /> Explore Vector's open-source projects
                </a>
              </div>

              <div className="space-y-2">
                <h3 className="text-sm font-semibold uppercase tracking-wider text-slate-400">About FairSense AgentiX</h3>
                <p className="text-sm text-slate-300 leading-relaxed">
                  FairSense-AgentiX is an intelligent bias detection and risk assessment platform that uses agentic AI workflows to analyze text, images, and datasets for fairness concerns. Unlike traditional ML classifiers that operate as black boxes, FairSense employs a reasoning agent that:
                </p>
                <ul className="space-y-1 pl-4 text-sm text-slate-400">
                  {[
                    "Plans its analysis strategy based on the input type",
                    "Selects the right tools for each task (OCR, vision models, embeddings, knowledge retrieval)",
                    "Critiques its own outputs and refines them iteratively",
                    "Explains its reasoning process through detailed telemetry",
                  ].map((point) => (
                    <li key={point} className="flex gap-2">
                      <span className="text-accent-200 flex-shrink-0">·</span>
                      {point}
                    </li>
                  ))}
                </ul>
                <p className="text-sm text-slate-300 leading-relaxed pt-1">
                  This approach delivers more accurate, transparent, and context-aware fairness assessments than static rule-based systems.
                </p>
                <a
                  href="https://vectorinstitute.github.io/fairsense-agentix/"
                  target="_blank"
                  rel="noopener noreferrer"
                  className="inline-flex items-center gap-1.5 text-xs text-accent-200 hover:text-accent-100 transition-colors"
                >
                  <BookOpen size={12} /> Read the documentation
                </a>
              </div>

              <AnalysisModesAccordion />

              <div className="space-y-2">
                <div className="flex items-center justify-between">
                  <h3 className="text-sm font-semibold uppercase tracking-wider text-slate-400">Vector AIxpert Program</h3>
                  <a href="https://aixpert-project.eu/" target="_blank" rel="noopener noreferrer">
                    <img
                      src={aixpertLogo}
                      alt="AIxpert"
                      className="h-10 opacity-80 hover:opacity-100 transition-opacity"
                    />
                  </a>
                </div>
                <p className="text-sm text-slate-300 leading-relaxed">
                  This project represents Vector Institute's research contributions to the AIXpert Horizon Europe initiative, focusing on tools, datasets, and evaluation pipelines for fairness-aware generative AI and explainable AI systems. Vector's contribution spans four core areas:
                </p>
                <ul className="space-y-1 pl-4 text-sm text-slate-400">
                  {[
                    "Explainable & accountable AI — Tools and benchmarks for interpretability, fairness, and transparency",
                    "Trustworthy agentic AI — Transparent, auditable, human-in-the-loop agentic systems",
                    "Multimodal evaluation — Benchmarks for audio-video understanding and vision-language fairness",
                    "Open, reproducible research — Code, datasets, and documentation shared openly",
                  ].map((point) => (
                    <li key={point} className="flex gap-2">
                      <span className="text-accent-200 flex-shrink-0">·</span>
                      {point}
                    </li>
                  ))}
                </ul>
                <a
                  href="https://vectorinstitute.github.io/vector-aixpert/about/"
                  target="_blank"
                  rel="noopener noreferrer"
                  className="inline-flex items-center gap-1.5 text-xs text-accent-200 hover:text-accent-100 transition-colors pt-1"
                >
                  <BookOpen size={12} /> Full AIXpert vision & consortium details
                </a>
              </div>
            </div>
          )}

          {activeTab === "team" && (
            <div className="space-y-5">
              <div className="space-y-3">
                <h3 className="text-xs font-semibold uppercase tracking-wider text-slate-500">Active Members</h3>
                {[
                  {
                    name: "Shaina Raza, PhD",
                    role: "Applied ML Scientist — Responsible AI",
                    email: "shaina.raza@vectorinstitute.ai",
                    linkedin: "https://www.linkedin.com/in/shainaraza/",
                  },
                  {
                    name: "Aravind Narayanan",
                    role: "Associate Applied ML Specialist",
                    email: "aravind.narayanan@vectorinstitute.ai",
                    linkedin: "https://www.linkedin.com/in/aravind-n-774665144/",
                  },
                  {
                    name: "Mahshid Alinoori",
                    role: "Applied ML Specialist",
                    email: "mahshid.alinoori@vectorinstitute.ai",
                    linkedin: "https://www.linkedin.com/in/mahshid-alinoori/",
                  },
                ].map((member) => (
                  <div key={member.name} className="flex gap-4 rounded-xl border border-slate-800/50 bg-slate-900/30 p-4">
                    <div className="flex h-12 w-12 flex-shrink-0 items-center justify-center rounded-full border border-accent-200/30 bg-accent-200/20 text-sm font-semibold text-accent-200">
                      {member.name.split(" ").filter(Boolean).slice(0, 2).map(p => p[0]).join("").toUpperCase()}
                    </div>
                    <div className="space-y-1 min-w-0">
                      <p className="text-sm font-semibold text-slate-200">{member.name}</p>
                      <p className="text-xs text-accent-200">{member.role}</p>
                      <div className="flex items-center gap-3 pt-0.5">
                        <a href={`mailto:${member.email}`} className="text-xs text-slate-500 hover:text-slate-300 transition-colors truncate">{member.email}</a>
                        <a href={member.linkedin} target="_blank" rel="noopener noreferrer" className="text-slate-500 hover:text-accent-200 transition-colors flex-shrink-0">
                          <LinkedInIcon size={13} />
                        </a>
                      </div>
                    </div>
                  </div>
                ))}
              </div>

              <div className="space-y-3">
                <h3 className="text-xs font-semibold uppercase tracking-wider text-slate-500">Contributors</h3>
                <div className="flex gap-4 rounded-xl border border-slate-800/30 bg-slate-900/20 p-4">
                  <div className="h-10 w-10 flex-shrink-0 rounded-full bg-slate-700/50 flex items-center justify-center text-slate-400 text-sm font-semibold">
                    K
                  </div>
                  <div className="space-y-0.5">
                    <p className="text-sm font-semibold text-slate-300">Karanpal Sekhon</p>
                    <p className="text-xs text-slate-500">Project development contributor</p>
                  </div>
                </div>
              </div>
            </div>
          )}

          {/* Publications tab — uncomment when ready to populate
          {activeTab === "papers" && (
            <div className="space-y-4">
              <p className="text-xs text-slate-500">[Placeholder — add published papers and links below.]</p>
              {[
                { title: "Paper Title Placeholder", venue: "Conference / Journal, Year", url: "#" },
                { title: "Paper Title Placeholder", venue: "Conference / Journal, Year", url: "#" },
              ].map((paper, idx) => (
                <div key={idx} className="rounded-xl border border-slate-800/50 bg-slate-900/30 p-4 space-y-1">
                  <p className="text-sm font-semibold text-slate-200">{paper.title}</p>
                  <p className="text-xs text-slate-500">{paper.venue}</p>
                  <a
                    href={paper.url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="inline-flex items-center gap-1 text-xs text-accent-200 hover:text-accent-100 transition-colors"
                  >
                    <BookOpen size={11} /> Read paper
                  </a>
                </div>
              ))}
            </div>
          )}
          */}

          {activeTab === "connect" && (
            <div className="space-y-4">
              <div className="space-y-2">
                <h3 className="text-sm font-semibold uppercase tracking-wider text-slate-400">Website</h3>
                <a
                  href="https://vectorinstitute.ai"
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-sm text-accent-200 hover:text-accent-100 transition-colors"
                >
                  vectorinstitute.ai
                </a>
              </div>
              <div className="space-y-3">
                <h3 className="text-sm font-semibold uppercase tracking-wider text-slate-400">Socials</h3>
                {[
                  { label: "LinkedIn",    href: "https://www.linkedin.com/company/vector-institute/", icon: <LinkedInIcon size={15} /> },
                  { label: "X / Twitter", href: "https://x.com/vectorinst", icon: <XIcon size={15} /> },
                  { label: "Bluesky",     href: "https://bsky.app/profile/vectorinstitute.ai", icon: <BlueskyIcon size={15} /> },
                ].map(({ label, href, icon }) => (
                  <a
                    key={label}
                    href={href}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="flex items-center gap-3 rounded-xl border border-slate-800/50 bg-slate-900/30 px-4 py-3 text-sm text-slate-300 hover:border-slate-700 hover:text-accent-200 transition-colors"
                  >
                    <span className="text-slate-400">{icon}</span>
                    {label}
                  </a>
                ))}
              </div>
            </div>
          )}

        </div>
      </div>
    </div>
  );
}
