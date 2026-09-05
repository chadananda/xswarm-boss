<!-- PROPOSED by goal-propose.py. Inferred from repo evidence, not
     confirmed by Chad. Raise at the next planning meeting. -->

# Goal (PROPOSED)

## What this is for

Chad, and only Chad for now — one developer holding ~25 active projects across several machines (Boss, Aorus, Jafar, Tower-NAS, laptop). The bottleneck is not writing code; agents already do that. It is knowing, at any given moment, what is running, what finished overnight, what broke, and what deserves the next hour. xswarm-boss exists to be the single place that state lives and the single interface that reports it — a persistent assistant with memory, a task queue, and a schedule, reachable by keyboard at the desk and by voice or phone when away from it. The change for the user: he stops opening five terminals to reconstruct where things stand, and starts the day being told. (Inferred — the repo has no stated user or customer, but the personas, the local-first voice stack, and the fact that every commit serves a one-person workflow all point at an audience of one.)

## What success looks like

Chad's workday begins and ends inside this tool rather than inside `herdr`, WezTerm tabs, and ad-hoc `ssh boss` calls. Ninety days after it stabilizes: the task list in xswarm-boss is the authoritative one — nothing important lives only in his head or in a `tmp/work-plan.md` — and the morning schedule it produces is the one he actually follows, not one he reads and overrides. The Cloudflare side (`boss-ai`, Twilio, SendGrid, Turso) means a phone away from the desk is a full-fidelity client, not a degraded one. Checkable: for four consecutive weeks, every dispatched piece of overnight work was queued and reported through this system, and he can answer "what happened last night" without reading a terminal.

## What would falsify this

Chad keeps using `Assistant/` and `herdr` as his daily driver and xswarm-boss's task database stops receiving new tasks — no new task rows for two straight weeks while real work continues elsewhere. That is the observation that kills the premise, and the repo already leans that way: `Assistant/` claims the same job ("manages a portfolio of 26 projects", morning briefing, overnight workers, phone operation) and is built directly on Claude Code, which means it inherits agent capability for free while xswarm-boss has to reimplement it in Python and a Worker.

Second falsifier, narrower: voice. If a month of usage logs shows the wake word firing under ~5 times a week while the Textual TUI is used daily, then "voice-first" is decoration on a keyboard app, and the Moshi/Vosk/torch dependency chain is a cost with no return.

## Explicitly not the goal

**Not a product.** The Stripe CLI installer in `postinstall`, the Stripe webhook secrets in `wrangler.toml`, and the `support@xswarm.io` author field describe a SaaS that no one has asked for. Building for a second user forces multi-tenancy, onboarding, and persona polish — work that competes directly with the thing that makes it valuable to Chad, which is being ruthlessly fitted to one person's machines and habits.

**Not an agent runtime.** Claude Code, herdr, and the dispatch skill already run agents. This should schedule, remember, and report; the moment it starts owning execution it becomes a worse Claude Code.

**Not a personality showcase.** Eleven personas and five separate Sauron animation scripts are cost, not progress.

## Where I am guessing

- **That xswarm-boss and `Assistant/` are meant to converge, and one should absorb the other.** Highest-stakes guess. If Chad says they are deliberately separate — Assistant as the Claude-Code-native orchestrator, xswarm-boss as the voice/comms front end that talks to it — then the goal above is wrong in scope and should be rewritten as "be the interface layer for Assistant," which is a much smaller and more achievable target.
- **That this is single-user, not a product.** The billing infrastructure is real and deployed; I am reading it as aspirational scaffolding. If commercial intent is live, nearly everything above changes.
- **That the GTD work is the real direction.** Versions 0.31–0.33 are all task prioritization, auto-scheduling, semantic dedup, and meeting reminders — personal productivity. The README sells cross-machine fleet orchestration. I have written the goal assuming the commits tell the truth and the README is stale. If the README is the plan, say so, because the last three months of work then went sideways.
- **That voice matters.** Weak inference. Nothing in the recent commit history touches voice; the last visible voice work is in a separate Rust repo (`xswarm-boss-voice`, a Moshi voice-builder for Apple Silicon), which suggests voice stalled and the TUI became the product.
- **That `sub-projects/omarchy-defender` is unrelated.** It is a browser game for teaching Hyprland hotkeys, sitting inside an assistant repo and consuming recent commits. I assume it was parked here for convenience. If it is meant to ship as part of this, the goal has a second, unexplained half.
