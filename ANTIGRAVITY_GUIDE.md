# Google Antigravity (AGY) Setup & Development Guide

This repository contains the **Vibe Now** agent and built-in **Google Antigravity Customizations & Skills** system.

---

## 🚀 Overview of Google Antigravity (AGY)

**Google Antigravity** is an AI-first development platform for designing, running, testing, and deploying autonomous AI agents.

### Key Components

1. **Antigravity CLI (`agy`)**: Command-line orchestration tool for building, evaluating, and launching agents.
2. **Antigravity IDE & 2.0 Canvas**: Workspace environment providing live agent chat, background execution tasks, auxiliary panes, and automated Playwright browser testing.
3. **Customizations System**: Framework for extending agent behavior using **Skills**, **Rules**, **Hooks**, **Plugins**, and **MCP Servers**.

---

## 🛠️ Repository Skills Directory (`.agents/skills/`)

The workspace `.agents/skills/` directory contains modular skills that extend agent workflows:

| Skill Directory | Description |
| :--- | :--- |
| [antigravity-guide](.agents/skills/antigravity-guide/SKILL.md) | Comprehensive sitemap & guide for AGY CLI, IDE, 2.0 canvas, and Python SDK. |
| [record-demo](.agents/skills/record-demo/SKILL.md) | Automated agent demo recorder using Playwright Chromium & Google Lyria (`lyria-002`) audio synthesis. |
| [build-agent-frontend](.agents/skills/build-agent-frontend/SKILL.md) | Single-page FastAPI + HTML/CSS dark glassmorphism chat UI builder. |
| [enable-a2ui](.agents/skills/enable-a2ui/SKILL.md) | A2UI (Agent-to-User Interface) v0.8 schema manager & UI surface renderer. |
| [setup-memory-bank](.agents/skills/setup-memory-bank/SKILL.md) | Vertex AI Memory Bank Service integration guide for persistent user preferences. |
| [build-rag](.agents/skills/build-rag/SKILL.md) | RAG architecture & vector storage integration patterns. |
| [publish-to-github](.agents/skills/publish-to-github/SKILL.md) | Automated GitHub repository packaging and publishing workflow. |
| [troubleshoot-lab-setup](.agents/skills/troubleshoot-lab-setup/SKILL.md) | Diagnostic & troubleshooting guide for Google Cloud environment setup. |

---

## 💻 Working with Antigravity Customizations

Customizations are auto-loaded by Antigravity agents from two locations:
1. **Global Root**: `/config/.gemini/config`
2. **Workspace Root**: `.agents/` (inside project root)

### Skill File Format

Each skill must contain a `SKILL.md` file formatted with YAML frontmatter:

```yaml
---
name: my-skill-name
description: Clear, human-readable summary of when this skill should be activated.
---

# Skill Instructions
Step-by-step instructions and references for the agent.
```

---

## 🎥 Recording Agent Demos

To record an automated interactive browser demo with upbeat background music:

```bash
node .agents/skills/record-demo/record-agent.js \
  -u "http://localhost:8080/" \
  -q "Find cozy cafes and vibe spots in Groningen" \
  -q "Generate a travel postcard image of a cozy Groningen cafe" \
  -o agent_demo.webm \
  --wait 35000 \
  --speed 1.2 \
  --title "Vibe Now — AI Local Discovery" \
  --music "upbeat lo-fi chill hip-hop, mellow Rhodes piano, soft vinyl crackle, relaxed downtempo beat"
```

To convert the resulting `.webm` video to an inline looping GIF:

```bash
ffmpeg -y -i agent_demo.webm -vf "fps=15,scale=800:-1:flags=lanczos,split[s0][s1];[s0]palettegen[p];[s1][p]paletteuse" demo.gif
```

---

## 🌐 Documentation References

- **Antigravity CLI**: `https://antigravity.google/docs/cli`
- **Skills System**: `https://antigravity.google/docs/skills`
- **Plugins & MCP**: `https://antigravity.google/docs/plugins`
- **Python SDK**: `https://github.com/google-antigravity/antigravity-sdk-python`
