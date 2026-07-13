import { useCallback, useEffect, useState } from "react";

import { getAnalysis, getReport, type AnalysisJob, type CoachingReport } from "./api/client";
import { AnalysisProgress } from "./features/progress/AnalysisProgress";
import { UploadPage } from "./features/upload/UploadPage";
import { EvidenceWorkspace } from "./features/workspace/EvidenceWorkspace";

type Screen = "upload" | "progress" | "workspace";

export function App() {
  const [screen, setScreen] = useState<Screen>("upload");
  const [job, setJob] = useState<AnalysisJob | null>(null);
  const [report, setReport] = useState<CoachingReport | null>(null);

  const loadReport = useCallback(async () => {
    if (!job) return;
    const loaded = await getReport(job.analysis_id);
    setReport(loaded);
    setScreen("workspace");
  }, [job]);

  useEffect(() => {
    const id = new URLSearchParams(window.location.search).get("analysis");
    if (!id) return;
    getAnalysis(id).then((loaded) => { setJob(loaded); setScreen(loaded.state === "completed" ? "workspace" : "progress"); if (loaded.state === "completed") return getReport(id).then(setReport); return undefined; }).catch(() => setScreen("upload"));
  }, []);

  function created(createdJob: AnalysisJob): void { setJob(createdJob); window.history.replaceState({}, "", `?analysis=${createdJob.analysis_id}`); setScreen("progress"); }
  function reset(): void { setJob(null); setReport(null); window.history.replaceState({}, "", window.location.pathname); setScreen("upload"); }

  if (screen === "workspace" && job && report) return <EvidenceWorkspace job={job} report={report} onBack={reset} onDeleted={reset} />;
  if (screen === "progress" && job) return <AnalysisProgress job={job} onComplete={() => void loadReport()} onExpired={reset} />;
  return <UploadPage onCreated={created} />;
}
