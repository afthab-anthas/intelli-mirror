# Intelli-Mirror Documentation

This folder contains comprehensive documentation for the Intelli-Mirror Smart Mirror Engine project. All documentation is evidence-based and derived from analysis of the actual codebase.

## 📚 Documentation Files

The documentation is organized into 7 comprehensive context packs:

### 1. **ARCHITECTURE.md** 
System architecture overview, component relationships, data flow, technology stack, and integration patterns.
- When to read: Understanding the big picture and how components interact
- Key topics: System design, component roles, external integrations, scalability

### 2. **STRUCTURE.md**
Project organization, folder structure, module dependencies, entry points, and configuration setup.
- When to read: Navigating the codebase and understanding project layout
- Key topics: Directory structure, module organization, configuration, build setup

### 3. **CODE.md**
Key functions, classes, algorithms, code patterns, critical paths, and performance-sensitive sections.
- When to read: Understanding implementation details and code organization
- Key topics: Key functions, patterns, critical algorithms, error handling

### 4. **DATAFLOW.md**
Data models, transformation pipelines, input/output flows, database interactions, and state management.
- When to read: Understanding how data moves through the system
- Key topics: Data models, pipelines, APIs, persistence, Firebase integration

### 5. **DECISIONS.md**
Architectural Decision Records (ADRs), technology rationale, design patterns, trade-offs, and technical debt.
- When to read: Understanding why certain choices were made
- Key topics: ADRs, technology choices, design patterns, technical debt

### 6. **GLOSSARY.md**
Domain-specific terminology, technical terms, business logic concepts, APIs, configuration, and status codes.
- When to read: Looking up terms, understanding domain concepts
- Key topics: Terminology, abbreviations, API definitions, configuration parameters

### 7. **RISK.md**
Security vulnerabilities, performance bottlenecks, technical debt, scalability limitations, and mitigation strategies.
- When to read: Assessing project health and identifying issues
- Key topics: Security concerns, performance risks, technical debt, external dependencies

## 🎯 Quick Navigation

**First time reading?** Start with:
1. **ARCHITECTURE.md** — Understand the system design
2. **STRUCTURE.md** — Learn the codebase layout
3. **GLOSSARY.md** — Get familiar with terminology

**Implementing a feature?** Read:
1. **CODE.md** — Understand existing patterns
2. **DATAFLOW.md** — See how data flows
3. **DECISIONS.md** — Understand architectural choices

**Debugging or optimizing?** Read:
1. **RISK.md** — Identify known issues
2. **CODE.md** — Find performance-critical sections
3. **DECISIONS.md** — Understand technical debt

## 📋 Project Overview

**Intelli-Mirror** is a comprehensive Smart Mirror Engine featuring:
- 🎭 **SFace Hybrid AI Face Recognition** — Enrollment and recognition using hybrid ML models
- 🤚 **MediaPipe Hand Gesture Tracking** — Real-time hand pose detection and gesture recognition
- 🎤 **Voice Command Orchestration** — Speech recognition and text-to-speech with multi-service support
- 🔐 **Security Dashboard** — MQTT-based security events and surveillance integration
- 💻 **Local PWA Interface** — Progressive Web App frontend displayed on mirror hardware
- 🌐 **Remote Dashboard** — Cross-platform web UI for monitoring and management

## 🛠️ Technology Stack

**Core:**
- Python 3.x (backend engine)
- Vanilla HTML / CSS / JavaScript (mirror PWA, security dashboard, website — see `website/`, `security_pwa/`, `lib/redact.mjs`)
- WebSocket (`websocket-server`) & MQTT (`paho-mqtt`) for real-time communication

**AI & ML:**
- MediaPipe (hand tracking, pose estimation)
- OpenCV (computer vision)
- scikit-learn (ML utilities)
- SFace models (face recognition)

**Services:**
- Google APIs (speech, calendar, Gmail)
- Spotify API (music control)
- Firebase (backend services)
- Google Generative AI (narration/reasoning)

**Dependencies:** See `requirements.txt` for complete list

## 🔄 Documentation Updates

> **Generated**: 2026-07-03  
> **Method**: Evidence-based analysis of all source files  
> **Convention**: Every claim is traceable to actual code locations  
> **Maintenance**: Update these docs whenever architecture or significant code patterns change

## 📝 How to Use These Docs

1. **Read the relevant sections** based on your task
2. **Cross-reference** between docs using markdown links
3. **Check code citations** to verify claims or see implementation details
4. **Use the Glossary** when encountering unfamiliar terms
5. **Review DECISIONS** to understand the "why" behind design choices
6. **Check RISK** before making significant changes

## ⚠️ Known Issues & Technical Debt

See **KNOWN-ISSUES.md** for:
- Current limitations and workarounds
- Performance considerations
- Security recommendations
- Future improvements

---

**For questions about specific components or patterns, refer to the relevant doc and check the code citations provided.**
