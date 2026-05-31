# Support Agent Academy

Certification-only gamification: levels reflect capability; they do **not** change live runtime behavior.

## Agent jobs

Each tenant has one **agent job** (chosen at creation, not changeable later):

| Job ID | Label | Core path | Specializations |
|--------|--------|-----------|-----------------|
| `customer_support` | Customer Support | Confused Intern → Helpdesk Rookie → Certified Chat Ranger | Deal Whisperer, Bug Buster, Parcel Pathfinder |
| `ceo` | CEO | Curious Observer → Strategic Advisor → Executive Voice | Vision Architect, Stakeholder Diplomat, Culture Champion |

Definitions: `shadou/training/levels.yaml` under `jobs:`. Eval packs: `shadou/training/packs/{job_id}/` → `{SHADOU_HOME}/eval/training/{job_id}/`.

Workspace + DB fields: `training.agent_job`, `tenants.training_job`.

## Studio

- **New agent wizard:** job picker on step 1.
- **Dashboard:** `AgentSprite` + job label per tenant card.
- **Academy:** progression tree and exams for that tenant's job only.

## API

- `GET /tenants/training-jobs` — job catalog
- `GET /tenants/{id}/training` — status (includes `agent_job`, levels, badges for that job)
- `POST /tenants/{id}/training/assess` — `{ "level": null | 1-3, "specialization": null | "<badge_id>" }`

## CLI

```bash
export SHADOU_HOME=/path/to/tenant
cd /path/to/shadou
python3 -m shadou.training.assess_all --shadou-home "$SHADOU_HOME" --compact
```

Ensure `workspace.yaml` → `training.agent_job` matches the intended job before assessing.
