# SkillProofAI Demo Video — Narration Script

**Target runtime:** approximately 2 minutes 35 seconds

**Narration style:** warm, confident, clear English; around 130–140 words per minute.
**Screen source:** record the actual SkillProofAI instance that will be submitted. Until deployment is available, rehearse locally. Do not present local screens as a live deployment.

## 00:00–00:13 — Title

**On-screen title:** “SkillProofAI — Evidence-Based Career Intelligence Platform”

**Narration:**

“SkillProofAI helps job seekers move from listing skills to showing evidence. It is an evidence-based career intelligence platform that turns a resume and a target role into clear, practical next steps.”

## 00:13–00:31 — The problem

**On-screen:** Open the real application’s overview page; keep the upload panel visible.

**Narration:**

“Candidates often read a job description and wonder: does my resume actually demonstrate what this role asks for? A keyword match cannot answer that, and an unexplained score does not tell someone what to improve. SkillProofAI focuses on the proof a resume contains—and on what is not yet visible.”

## 00:31–00:47 — Introduce the workflow

**On-screen:** Show the application and identify the role, PDF selector, and job description. State whether this is the deployed public instance; if it is not deployed, record locally and do not call it live.

**Narration:**

“The workflow is simple: choose a role, add a PDF resume, and paste the job requirements. This recording uses the clearly fictional sample resume included with the demo materials. The app processes selectable PDF text in memory and does not upload the resume to a separate AI service.”

## 00:47–01:06 — Analyze and coverage

**On-screen:** Select `assets/sample_resume_fictional.pdf`, use the prepared demo job description, and submit. Wait for the real request and result. Show the resulting coverage value and counts without editing them.

**Narration:**

“Now I’ll build the evidence map. The coverage indicator summarizes the strength of the evidence found across the role’s requirements; it is not a hiring score or a prediction. Here, SkillProofAI separates requirements into demonstrated, partial support, and not evidenced, based on the content of this particular sample resume.”

## 01:06–01:27 — Evidence and skill gaps

**On-screen:** Open real skill rows from more than one category. Show source anchors and a skill with no anchor.

**Narration:**

“Each classification can be traced to resume text. A demonstrated result has a direct mention supported by an action or outcome. Partial support means there is related context but more proof would help. Not evidenced means this document did not provide a reliable anchor—it does not mean the person lacks that ability. Every match should be reviewed by a person.”

## 01:27–01:47 — Action plan

**On-screen:** Open Action plan and show the actual two-day proof projects and checklist from this run.

**Narration:**

“For gaps, the app suggests focused two-day portfolio sprints with concrete deliverables. Instead of stopping at a missing keyword, a candidate gets a practical route to build a project, document the work, and strengthen the evidence in a future resume.”

## 01:47–02:02 — Interview preparation

**On-screen:** Open Interview prep and show the actual role-specific prompts from this result.

**Narration:**

“Interview preparation is tied to the same skills. The questions invite candidates to explain context, their actions, technical decisions, results, and what they learned—so practice connects back to real work.”

## 02:02–02:17 — Report and technical overview

**On-screen:** If signed in with an authorized demo account, export the real PDF report and open it. Briefly show the stack graphic or tasteful lower-third. Never show account details, resume contact details, secrets, or browser developer tools.

**Narration:**

“Signed-in users can save analysis history and export a PDF evidence report. React and Vite power the interface; FastAPI and Python serve the API; SQLite stores accounts and saved analyses; PyMuPDF extracts PDF text; and ReportLab produces the reports. Supabase authentication is optional and must be configured by the operator.”

## 02:17–02:36 — Impact and close

**On-screen:** Return to the app’s actual results, then fade to a simple title card.

**Narration:**

“SkillProofAI gives students and job seekers a clearer way to improve: show what the resume proves, identify what needs stronger evidence, and plan what to build next. SkillProofAI — Show your skills. Strengthen your evidence. Build your future.”

## Recording notes

- Replace all on-screen result references with what the application actually returns during recording.
- The resume is explicitly fictional, but its analysis output must still be generated live by the application.
- Do not claim a live public URL unless it is deployed and independently tested.
- Do not show personal email, billing dashboards, provider account settings, authentication secrets, tokens, local file paths, or real applicant data.
- If a guest session cannot export the report, record PDF export only with an authorized signed-in demo account, or clearly identify it as a feature awaiting auth configuration; do not simulate the download.
