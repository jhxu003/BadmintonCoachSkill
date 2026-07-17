import { useCallback, useState } from "react";

import { getReport, type AnalysisJob, type CoachingReport } from "./api/client";
import { AnalysisProgress } from "./features/progress/AnalysisProgress";
import { PlayerSetupPage } from "./features/setup/PlayerSetupPage";
import { UploadPage } from "./features/upload/UploadPage";
import { EvidenceWorkspace } from "./features/workspace/EvidenceWorkspace";

type Screen = "upload" | "progress" | "setup" | "workspace";

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
  function setupSubmitted(updatedJob: AnalysisJob): void { setJob(updatedJob); setScreen("progress"); }
  function reset(): void { setJob(null); setReport(null); setScreen("upload"); }

  if (screen === "workspace" && job && report) return <EvidenceWorkspace job={job} report={report} onBack={reset} onDeleted={reset} />;
  if (screen === "setup" && job) return <PlayerSetupPage job={job} onSubmitted={setupSubmitted} onBack={reset} />;
  if (screen === "progress" && job) return <AnalysisProgress job={job} onComplete={() => void loadReport()} onNeedsSetup={() => setScreen("setup")} onExpired={reset} />;
  return <UploadPage onCreated={created} />;
}
