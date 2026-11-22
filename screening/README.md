# OsdagBridge software testing screening

Candidate: Krithik M.
Deadline: 23 November 2026, 10:00 AM IST.

## Execution status

Installation, real desktop startup, and GUI-driven designs verified. Two GUI sessions produced
seven design runs: baseline, custom girder steel, custom deck concrete, span change, reset to
baseline, carriageway 7 m, and return to 5 m. A separate probe compared per-field validation
with `.osi` load validation on 18 boundary values. Findings are mapped to existing upstream
issues; evidence was added as comments on six existing issues (#20, #113, #92, #112, #96, #129).
The fork branch is pushed; the collaborator invitation and final submission are still pending.

- Upstream: https://github.com/Nidhikhare12/OsdagBridge
- Fork: https://github.com/krithikmohan30/OsdagBridge
- Tested base revision: `d74f56dd7f22925fb8148cabf5740ed8d1e39ff3`
- Local task branch: `screening/software-testing`
- Test register: [tests/test-matrix.csv](tests/test-matrix.csv)
- Setup record: [environment/setup-notes.md](environment/setup-notes.md)
- Consolidated report: [report/OsdagBridge-Testing-Report.pdf](report/OsdagBridge-Testing-Report.pdf)
- Findings and issue mapping: [findings/confirmed-findings.md](findings/confirmed-findings.md)
- Submission archive: supplied separately with the submission (not committed)

The register distinguishes PASS, FAIL, PARTIAL, BLOCKED, and NOT RUN. Each row references the
saved inputs, dictionary snapshots, logs, and GUI evidence behind its status.

## Evidence conventions

- Each application session and design run receives an ID.
- Preserve full `.osi` inputs and exact custom values.
- Compare UI values, backend dictionaries, output docks, and generated reports
  with explicit units and display rounding.
- Record GUI-driven and direct-backend tests distinctly.
- A successful calculation is not sufficient evidence that the GUI refreshed.
- Record diagnostic instrumentation and setup workarounds against the base revision.
- Check existing upstream issues before preparing any new issue.

## Submission assets

The final package will include the testing PDF, test register, actual `.osi`
cases, diagnostic scripts, logs, screenshots, issue/comment links, video link,
and the candidate's current one-page resume. Pending assets are not represented
by empty placeholder evidence files.
