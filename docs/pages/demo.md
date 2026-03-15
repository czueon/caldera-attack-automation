---
layout: default
title: Demo
nav_order: 8
---

# Demo
{: .no_toc }

---

## Demo Video

> 🎬 Demo video coming soon.

<!-- Uncomment when available:

<div style="position: relative; padding-bottom: 56.25%; height: 0; overflow: hidden; max-width: 100%;">
  <iframe
    src="https://www.youtube.com/embed/YOUR_VIDEO_ID"
    style="position: absolute; top: 0; left: 0; width: 100%; height: 100%;"
    frameborder="0"
    allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture"
    allowfullscreen>
  </iframe>
</div>

-->

---

## System Figures

### System Overview
![System Overview]({{ site.baseurl }}/assets/images/system-overview.png)

### 5-Step Pipeline Architecture
![Pipeline Architecture]({{ site.baseurl }}/assets/images/system-architecture.png)

---

## Example Walkthrough: TTPs#1

**Scenario**: Homepage-based Internal Network Compromise

**Input**: KISA TTP Report #1 (PDF) + `environment_ttps1.md`

**Pipeline execution**:

1. **Step 1** — Extracted 32 pages of Korean text from the PDF
2. **Step 2** — Generated abstract attack flow with attack goals (Initial Access → Execution → Privilege Escalation → Lateral Movement → Collection → Exfiltration)
3. **Step 3** — Applied environment spec: assigned real IPs, paths, credentials; determined dependency edges (e.g., PrintSpoofer privilege escalation → 4 subsequent steps)
4. **Step 4** — Generated ~33 Caldera Abilities and 1 Adversary profile
5. **Step 5** — Initial execution: ~52% success → after 3 Self-Correcting iterations: ~70% success

**Notable Self-Correcting fix**: When `sc.exe start "WindowsDefenderUpdate"` failed because the service didn't exist (preceding step partial failure), the LLM generated a combined `sc.exe create ... && sc.exe start ...` command — resolving the dependency within the single ability.

---

## Intermediate Outputs (Example Structure)

All intermediate YAML outputs are saved and can be inspected:

```yaml
# step3_concrete.yaml (excerpt)
concrete_flow:
  nodes:
    - id: "node_008"
      name: "Privilege Escalation via PrintSpoofer"
      tactic: "privilege-escalation"
      technique:
        id: "T1068"
        name: "Exploitation for Privilege Escalation"
      environment_specific:
        target: "192.168.x.x"
        commands: "C:\\Users\\Public\\data\\PrintSpoofer64.exe -i -c cmd"
  edges:
    - source: "node_008"
      target: "node_009"
      dependency_type: "requires"
    - source: "node_008"
      target: "node_010"
      dependency_type: "requires"
  execution_order: [..., "node_008", "node_009", "node_010", ...]
```
