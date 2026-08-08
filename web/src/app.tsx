import { useCallback, useState } from "react";

import { createCoachingPlan, getAgentVideoCoachingReport, getCoachingPlanReport, getDemonstrationReport, getReport, type AgentVideoCoachingReport, type AnalysisJob, type CoachDemonstrationReport, type CoachingPlanReport, type CoachingReport } from "./api/client";
import { CoachingPlanPage, type CoachingPlanDraft } from "./features/coaching-plan/CoachingPlanPage";
import { CoachingPlanWorkspace } from "./features/coaching-plan/CoachingPlanWorkspace";
import { DemonstrationPage } from "./features/demonstration/DemonstrationPage";
import { DemonstrationWorkspace } from "./features/demonstration/DemonstrationWorkspace";
import { AnalysisProgress } from "./features/progress/AnalysisProgress";
import { PlayerSetupPage } from "./features/setup/PlayerSetupPage";
import { UploadPage } from "./features/upload/UploadPage";
import { EvidenceWorkspace } from "./features/workspace/EvidenceWorkspace";
import { AgentVideoWorkspace } from "./features/workspace/AgentVideoWorkspace";

type Screen = "demonstration" | "coaching-plan" | "upload" | "progress" | "setup" | "workspace" | "agent-workspace" | "demonstration-workspace" | "coaching-plan-workspace";
type Mode = "video" | "agent-video" | "demonstration" | "coaching-plan";

export function App() {
  const [screen, setScreen] = useState<Screen>("upload");
  const [mode, setMode] = useState<Mode>("agent-video");
  const [job, setJob] = useState<AnalysisJob | null>(null);
  const [report, setReport] = useState<CoachingReport | null>(null);
  const [agentReport, setAgentReport] = useState<AgentVideoCoachingReport | null>(null);
  const [demonstrationReport, setDemonstrationReport] = useState<CoachDemonstrationReport | null>(null);
  const [coachingPlanReport, setCoachingPlanReport] = useState<CoachingPlanReport | null>(null);
  const [coachingDraft, setCoachingDraft] = useState<CoachingPlanDraft | null>(null);

  const loadReport = useCallback(async () => {
    if (!job) return;
    if (mode === "agent-video") {
      setAgentReport(await getAgentVideoCoachingReport(job));
      setScreen("agent-workspace");
    } else if (mode === "coaching-plan") {
      setCoachingPlanReport(await getCoachingPlanReport(job));
      setScreen("coaching-plan-workspace");
    } else if (mode === "demonstration") {
      setDemonstrationReport(await getDemonstrationReport(job));
      setScreen("demonstration-workspace");
    } else {
      setReport(await getReport(job));
      setScreen("workspace");
    }
  }, [job, mode]);

  function createdVideo(createdJob: AnalysisJob): void { setMode("agent-video"); setJob(createdJob); setScreen("progress"); }
  function createdDemonstration(createdJob: AnalysisJob): void { setMode("demonstration"); setJob(createdJob); setScreen("progress"); }
  function createdCoachingPlan(createdJob: AnalysisJob, draft: CoachingPlanDraft): void { setMode("coaching-plan"); setCoachingDraft(draft); setJob(createdJob); setScreen("progress"); }
  async function switchCoachingLens(coachId: string): Promise<void> {
    if (!coachingDraft) throw new Error("当前结构化观察已不可用，请返回重新提交。");
    const draft = { ...coachingDraft, coach_id: coachId };
    const createdJob = await createCoachingPlan(draft);
    setCoachingDraft(draft);
    setCoachingPlanReport(null);
    setMode("coaching-plan");
    setJob(createdJob);
    setScreen("progress");
  }
  function setupSubmitted(updatedJob: AnalysisJob): void { setJob(updatedJob); setScreen("progress"); }
  function reset(target: "demonstration" | "coaching-plan" | "upload" = "upload"): void { setJob(null); setReport(null); setAgentReport(null); setDemonstrationReport(null); setCoachingPlanReport(null); setCoachingDraft(null); setMode(target === "upload" ? "agent-video" : target === "coaching-plan" ? "coaching-plan" : "demonstration"); setScreen(target); }

  if (screen === "demonstration-workspace" && job && demonstrationReport) return <DemonstrationWorkspace job={job} report={demonstrationReport} onBack={() => reset("demonstration")} />;
  if (screen === "coaching-plan-workspace" && job && coachingPlanReport) return <CoachingPlanWorkspace job={job} report={coachingPlanReport} onBack={() => reset("coaching-plan")} onSwitchCoach={switchCoachingLens} />;
  if (screen === "agent-workspace" && job && agentReport) return <AgentVideoWorkspace job={job} report={agentReport} onBack={() => reset("upload")} onDeleted={() => reset("upload")} />;
  if (screen === "workspace" && job && report) return <EvidenceWorkspace job={job} report={report} onBack={() => reset("upload")} onDeleted={() => reset("upload")} />;
  if (screen === "setup" && job) return <PlayerSetupPage job={job} onSubmitted={setupSubmitted} onBack={() => reset("upload")} />;
  if (screen === "progress" && job) return <AnalysisProgress job={job} variant={mode} onComplete={() => void loadReport()} onNeedsSetup={() => setScreen("setup")} onExpired={() => reset(mode === "video" || mode === "agent-video" ? "upload" : mode === "coaching-plan" ? "coaching-plan" : "demonstration")} />;
  if (screen === "upload") return <UploadPage onCreated={createdVideo} onShowDemonstrations={() => reset("demonstration")} />;
  if (screen === "coaching-plan") return <CoachingPlanPage onCreated={createdCoachingPlan} onShowDemonstrations={() => reset("demonstration")} />;
  return <DemonstrationPage onCreated={createdDemonstration} onShowVideoAnalysis={() => reset("upload")} onShowCoachingPlan={() => reset("coaching-plan")} />;
}
