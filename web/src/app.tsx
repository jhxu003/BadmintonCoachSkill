import { useCallback, useState } from "react";

import { getReport, type AnalysisJob, type CoachingReport } from "./api/client";
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
    const loaded = await getReport(job);
    setReport(loaded);
    setScreen("workspace");
  }, [job]);

  function created(createdJob: AnalysisJob): void { setJob(createdJob); setScreen("progress"); }
  function reset(): void { setJob(null); setReport(null); setScreen("upload"); }

  if (screen === "workspace" && job && report) return <EvidenceWorkspace job={job} report={report} onBack={reset} onDeleted={reset} />;
  if (screen === "progress" && job) return <AnalysisProgress job={job} onComplete={() => void loadReport()} onExpired={reset} />;
  return <UploadPage onCreated={created} />;
}
