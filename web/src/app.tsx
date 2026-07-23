import { useCallback, useState } from "react";

import { getDemonstrationReport, getReport, type AnalysisJob, type CoachDemonstrationReport, type CoachingReport } from "./api/client";
import { DemonstrationPage } from "./features/demonstration/DemonstrationPage";
import { DemonstrationWorkspace } from "./features/demonstration/DemonstrationWorkspace";
import { AnalysisProgress } from "./features/progress/AnalysisProgress";
import { PlayerSetupPage } from "./features/setup/PlayerSetupPage";
import { UploadPage } from "./features/upload/UploadPage";
import { EvidenceWorkspace } from "./features/workspace/EvidenceWorkspace";

type Screen = "demonstration" | "upload" | "progress" | "setup" | "workspace" | "demonstration-workspace";
type Mode = "video" | "demonstration";

export function App() {
  const [screen, setScreen] = useState<Screen>("demonstration");
  const [mode, setMode] = useState<Mode>("demonstration");
  const [job, setJob] = useState<AnalysisJob | null>(null);
  const [report, setReport] = useState<CoachingReport | null>(null);
  const [demonstrationReport, setDemonstrationReport] = useState<CoachDemonstrationReport | null>(null);

  const loadReport = useCallback(async () => {
    if (!job) return;
    if (mode === "demonstration") {
      setDemonstrationReport(await getDemonstrationReport(job));
      setScreen("demonstration-workspace");
    } else {
      setReport(await getReport(job));
      setScreen("workspace");
    }
  }, [job, mode]);

  function createdVideo(createdJob: AnalysisJob): void { setMode("video"); setJob(createdJob); setScreen("progress"); }
  function createdDemonstration(createdJob: AnalysisJob): void { setMode("demonstration"); setJob(createdJob); setScreen("progress"); }
  function setupSubmitted(updatedJob: AnalysisJob): void { setJob(updatedJob); setScreen("progress"); }
  function reset(target: "demonstration" | "upload" = "demonstration"): void { setJob(null); setReport(null); setDemonstrationReport(null); setMode(target === "upload" ? "video" : "demonstration"); setScreen(target); }

  if (screen === "demonstration-workspace" && job && demonstrationReport) return <DemonstrationWorkspace job={job} report={demonstrationReport} onBack={() => reset("demonstration")} />;
  if (screen === "workspace" && job && report) return <EvidenceWorkspace job={job} report={report} onBack={() => reset("upload")} onDeleted={() => reset("upload")} />;
  if (screen === "setup" && job) return <PlayerSetupPage job={job} onSubmitted={setupSubmitted} onBack={() => reset("upload")} />;
  if (screen === "progress" && job) return <AnalysisProgress job={job} variant={mode} onComplete={() => void loadReport()} onNeedsSetup={() => setScreen("setup")} onExpired={() => reset(mode === "video" ? "upload" : "demonstration")} />;
  if (screen === "upload") return <UploadPage onCreated={createdVideo} onShowDemonstrations={() => reset("demonstration")} />;
  return <DemonstrationPage onCreated={createdDemonstration} onShowVideoAnalysis={() => reset("upload")} />;
}
