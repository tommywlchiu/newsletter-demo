# Research: agentic AI in production: what is actually shipping, where deployments are failing, and what changed in the last few months

Agentic AI is shipping in production, but mostly as bounded systems inside customer service, software development, and workflow automation—not as unrestricted autonomous employees. The latest evidence shows a widening gap between experimentation and governed scale: context quality, long-horizon reliability, human oversight, and cost control are the main deployment constraints, while vendors are spending the past few months productizing registries, tenancy, tool permissions, and agent APIs.

## 1. Most organizations are experimenting or deploying; relatively few have scaled autonomous workflows.

The production story is a narrow funnel, not a wholesale shift to autonomous digital workers. Deloitte’s current survey found 42% of participating organizations had tested or deployed AI agents, but only 15% had scaled orchestrated, multi-agent adoption; just 5% said their business processes were highly prepared for agents, and 70% said they did not feel able to trust and govern them. McKinsey’s broader figures are more favorable but use a looser definition: 40% of respondents at organizations above $1 billion in revenue said they were scaling agents in at least one function, compared with 22% at smaller organizations. The writer should distinguish “has an agent project,” “has deployed an agent,” and “has scaled a governed multi-agent workflow.”

- **42%** — Organizations that had tested or deployed AI agents in Deloitte’s April–June 2026 survey of 501 U.S. senior-manager-to-C-suite respondents  
  <https://www.deloitte.com/us/en/about/press-room/deloitte-survey-examines-ai-readiness-agentic-ai-success.html>
- **15%** — Organizations reporting scaled, orchestrated, multi-agent adoption  
  <https://www.deloitte.com/us/en/about/press-room/deloitte-survey-examines-ai-readiness-agentic-ai-success.html>
- **5%** — Organizations saying their business processes were highly prepared for AI agents  
  <https://www.deloitte.com/us/en/about/press-room/deloitte-survey-examines-ai-readiness-agentic-ai-success.html>
- **70%** — Leaders saying they did not feel able to trust and govern agents  
  <https://www.deloitte.com/us/en/about/press-room/deloitte-survey-examines-ai-readiness-agentic-ai-success.html>
- **40%** — Respondents at organizations with more than $1 billion in annual revenue reporting that they were scaling AI agents in at least one business function  
  <https://www.mckinsey.com/capabilities/quantumblack/our-insights/the-state-of-ai?page=58&onlycontent=1>
- **22%** — Respondents at smaller organizations reporting that they were scaling AI agents in at least one function  
  <https://www.mckinsey.com/capabilities/quantumblack/our-insights/the-state-of-ai?page=58&onlycontent=1>
- **1,719 respondents in 97 countries** — McKinsey global survey sample and geographic coverage; fieldwork ran May 4–June 8, 2026  
  <https://www.mckinsey.com/capabilities/quantumblack/our-insights/the-state-of-ai?page=58&onlycontent=1>

  - source: <https://www.deloitte.com/us/en/about/press-room/deloitte-survey-examines-ai-readiness-agentic-ai-success.html>
  - source: <https://www.mckinsey.com/capabilities/quantumblack/our-insights/the-state-of-ai?page=58&onlycontent=1>

## 2. What is actually shipping: agents embedded in business systems, especially service and software workflows.

There is concrete production shipping, but it is concentrated in bounded, auditable work—customer-service actions, record updates, workflow triggers, coding, and DevOps—rather than unrestricted autonomy. Salesforce’s own fiscal results provide unusually direct production telemetry: the company says its agents executed billions of discrete tasks across Agentforce and Slack. Recent product releases also show the market moving from standalone chat interfaces toward agent registries, single-tenant deployment, tool permissions, and developer APIs—the operational layer needed to put agents inside existing systems.

- **7.0 billion AWUs** — Agentic Work Units delivered to date across Salesforce Agentforce and Slack, as reported August 26, 2026  
  <https://investor.salesforce.com/news/news-details/2026/Salesforce-Delivers-Record-Second-Quarter-Fiscal-2027-Results/default.aspx>
- **3.2 billion AWUs** — Agentic Work Units delivered in Salesforce fiscal Q2 2027  
  <https://investor.salesforce.com/news/news-details/2026/Salesforce-Delivers-Record-Second-Quarter-Fiscal-2027-Results/default.aspx>
- **97% quarter over quarter** — Growth in Salesforce’s reported Q2 FY27 Agentic Work Units  
  <https://investor.salesforce.com/news/news-details/2026/Salesforce-Delivers-Record-Second-Quarter-Fiscal-2027-Results/default.aspx>
- **More than $1.5 billion ARR** — Salesforce-reported Agentforce annual recurring revenue in Q2 FY27, up more than 240% year over year  
  <https://investor.salesforce.com/news/news-details/2026/Salesforce-Delivers-Record-Second-Quarter-Fiscal-2027-Results/default.aspx>

  - source: <https://investor.salesforce.com/news/news-details/2026/Salesforce-Delivers-Record-Second-Quarter-Fiscal-2027-Results/default.aspx>
  - source: <https://about.gitlab.com/press/releases/2026-08-20-gitlab-scales-agentic-ai-across-trusted-software-delivery-workflows/>
  - source: <https://aws.amazon.com/about-aws/whats-new/2026/08/aws-agent-registry-generally-available/>
  - source: <https://openai.com/index/introducing-the-agents-api>

## 3. Agents often fail because the system feeds them the wrong business reality.

The most credible failure pattern is context failure rather than a spectacular model hallucination. VentureBeat’s July 2026 Pulse survey of 101 enterprises found that 68% had traced at least one confident but wrong agent answer to missing or inconsistent business context during the previous six months; 37% reported that this had happened more than once. The sample was self-selected and directional, but the operational lesson is important: stale data, inconsistent metric definitions, missing documents, and incomplete retrieval can create answers that look confident and plausible. Organizations with context-layer projects reported more recurring failures, which the study says is likely because they can detect and attribute them.

- **101 enterprises** — Respondents in VentureBeat Pulse’s July 2026 survey; organizations had more than 100 employees  
  <https://venturebeat.com/resources/agent-context-layers-enterprises-governing-their-ai-data-are-catching-twice-as-many-bad-answers-as-the-ones-who-arent>
- **68%** — Respondents reporting at least one context-traced confident-but-wrong answer in the prior six months  
  <https://venturebeat.com/resources/agent-context-layers-enterprises-governing-their-ai-data-are-catching-twice-as-many-bad-answers-as-the-ones-who-arent>
- **37%** — Respondents reporting recurring context failures  
  <https://venturebeat.com/resources/agent-context-layers-enterprises-governing-their-ai-data-are-catching-twice-as-many-bad-answers-as-the-ones-who-arent>
- **50% versus 21%** — Recurring-failure rate among respondents building or having built a semantic layer versus respondents without one; the source cautions this reflects detection and selection effects  
  <https://venturebeat.com/resources/agent-context-layers-enterprises-governing-their-ai-data-are-catching-twice-as-many-bad-answers-as-the-ones-who-arent>

  - source: <https://venturebeat.com/resources/agent-context-layers-enterprises-governing-their-ai-data-are-catching-twice-as-many-bad-answers-as-the-ones-who-arent>

## 4. Benchmark pass rates are a poor proxy for production reliability when tasks require many dependent actions.

Long-horizon workflows expose a reliability ceiling that short benchmark scores hide. A September 2, 2026 arXiv study tested nine models—six open models ranging from 1.2 billion to 671 billion parameters and three deployed proprietary systems—across 10,664 trajectories. On the agentic tool-use task, every tested model fell from near-perfect success to near zero within 16 steps. A separate arXiv paper introduced a deployment-qualification method that combines reliability, human-review burden, and cost; in a 16-system, 750-case clinical-audit study, systems with nearly identical autonomous accuracy required materially different amounts of human review to reach the same reliability target. These are new and directly relevant findings, but both are preprints rather than audited enterprise field studies.

- **10,664 trajectories** — Trajectories analyzed in the long-horizon degradation study submitted August 31, 2026  
  <https://arxiv.org/abs/2609.01660>
- **9 models** — Models tested: six open models from 1.2B to 671B parameters and three deployed proprietary systems  
  <https://arxiv.org/abs/2609.01660>
- **16 steps** — Within this horizon, every model tested on the study’s agentic task fell from near-perfect success to near zero  
  <https://arxiv.org/abs/2609.01660>
- **16 agent systems and 750 cases** — Clinical-audit case-study scope in the READY deployment-qualification preprint  
  <https://arxiv.org/abs/2609.02095v1>
- **72.8% versus 72.5%** — Autonomous accuracy for two systems that differed by only 0.3 percentage points  
  <https://arxiv.org/abs/2609.02095v1>
- **39.2% versus 29.6% human review** — Human-review rates required by those two systems to qualify at the same 76% reliability target under the evaluated policy  
  <https://arxiv.org/abs/2609.02095v1>

  - source: <https://arxiv.org/abs/2609.01660>
  - source: <https://arxiv.org/abs/2609.02095v1>

## 5. Productivity gains are outrunning measurable enterprise financial impact.

The economic payoff is real for some deployments but not yet broad or uniform. McKinsey found a large gap between individual productivity and organization-level financial impact: 80% of respondents said AI improved their own productivity, while only 37% attributed at least some positive EBIT impact to AI use; the latter was essentially unchanged from the previous survey. About one in five respondents said AI-related operating costs—including token costs—constrained use. This supports a more cautious thesis: the bottleneck is increasingly operating model, observability, data quality, and unit economics, not whether a demo can complete a task.

- **80%** — Respondents reporting that AI improved their individual productivity  
  <https://www.mckinsey.com/capabilities/quantumblack/our-insights/the-state-of-ai?page=58&onlycontent=1>
- **37%** — Respondents attributing at least some positive EBIT impact to AI use  
  <https://www.mckinsey.com/capabilities/quantumblack/our-insights/the-state-of-ai?page=58&onlycontent=1>
- **About 20%** — Respondents saying AI-related operating costs constrained or limited AI use  
  <https://www.mckinsey.com/capabilities/quantumblack/our-insights/the-state-of-ai?page=58&onlycontent=1>
- **14%** — Respondents at AI-using organizations saying AI contributed to an overall workforce decline in the prior year  
  <https://www.mckinsey.com/capabilities/quantumblack/our-insights/the-state-of-ai?page=58&onlycontent=1>

  - source: <https://www.mckinsey.com/capabilities/quantumblack/our-insights/the-state-of-ai?page=58&onlycontent=1>

## 6. The recent shift is from agent demos to deployment control planes.

What is genuinely new in the last few months is not the existence of agent pilots; it is the infrastructure around controlled deployment. In August and September 2026, AWS made an Agent Registry generally available for governed discovery of agents, tools, skills, MCP servers, and custom resources; GitLab announced agentic workloads inside its single-tenant Dedicated environment for regulated customers; and OpenAI introduced the Agents API in public beta on September 10. These releases show vendors productizing identity, tenancy, tool access, deployment, and orchestration. The recirculated story is that enterprise pilots are failing at a universal 86–89% or 88% rate; the sources located for this briefing do not substantiate that number.

- **5 AWS Regions** — Initial regions listed by AWS for the generally available Agent Registry  
  <https://aws.amazon.com/about-aws/whats-new/2026/08/aws-agent-registry-generally-available/>
- **1 single-tenant environment and region** — GitLab Dedicated deployment model announced for GitLab Duo Agent Platform customers  
  <https://about.gitlab.com/press/releases/2026-08-20-gitlab-scales-agentic-ai-across-trusted-software-delivery-workflows/>

  - source: <https://aws.amazon.com/about-aws/whats-new/2026/08/aws-agent-registry-generally-available/>
  - source: <https://about.gitlab.com/press/releases/2026-08-20-gitlab-scales-agentic-ai-across-trusted-software-delivery-workflows/>
  - source: <https://openai.com/index/introducing-the-agents-api>

## Where sources disagree

- **How much enterprise agent deployment is genuinely at scale** — Deloitte’s April–June 2026 survey of 501 U.S. leaders found 42% had tested or deployed agents, but only 15% had scaled orchestrated, multi-agent adoption. McKinsey’s May–June 2026 global survey found 40% of respondents at organizations with more than $1 billion in revenue were scaling agents in at least one function, versus 22% at smaller organizations. These are not necessarily contradictory: McKinsey’s measure includes scaling in one or more functions and does not require multi-agent orchestration, while Deloitte’s 15% is a narrower scale definition.
- **What counts as production evidence** — Salesforce reports 7.0 billion Agentic Work Units delivered to date and 3.2 billion in fiscal Q2 2027, defining an AWU as a discrete task executed by an AI agent in production. This is strong vendor telemetry for Salesforce’s own platform, but it is not a market-wide deployment rate and does not establish that every task was fully autonomous or economically successful.
- **Whether observed agent failures are mainly model failures or systems failures** — The strongest recent evidence points toward system-level failure: missing or inconsistent business context, long-horizon error accumulation, insufficient human oversight, and weak governance. However, the available studies use different populations and tasks, so they do not establish a single universal ranking of failure causes.

## Widely repeated, apparently wrong

- Believed: 88% of AI-agent pilots fail to reach production.  
  Actually: The widely repeated claim that “88% of AI-agent pilots never reach production” is not supported here by an identifiable primary IDC, Forrester, or Anaconda publication. It appears to be recirculated by secondary blogs and should not be presented as an established industry-wide failure rate.
- Believed: 40% of agentic-AI projects have already failed or will fail in production.  
  Actually: Gartner’s often-cited “more than 40%” figure is a forecast for agentic-AI projects that will be canceled by the end of 2027, not an observed 40% production-failure or cancellation rate.
- Believed: Organizations without a semantic layer have fewer agent failures.  
  Actually: A semantic or context layer can increase the number of failures an organization detects. In VentureBeat’s small, self-selected survey, organizations building such layers reported more recurring failures, but the article explicitly warns that this likely reflects better instrumentation and reverse causation—not that semantic layers make agents less reliable.
