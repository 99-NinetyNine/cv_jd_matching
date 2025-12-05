# 🧠 Advanced CV Explainability - Premium AI Feature

## Overview

The **Advanced Explainability** system provides premium users with deep AI-powered insights into their CV quality and job matches. It leverages **LangGraph** for orchestrating multi-step reasoning workflows with **real-time streaming** of analysis nodes.

---

## ✨ Features

### 1. **CV Quality Assessment (ATS Resume Scoring)**
- **Structure & Formatting** (0-100)
- **Content Completeness** (0-100)
- **ATS Compatibility** (0-100)
- **Keyword Optimization** (0-100)
- **Professional Language** (0-100)
- **Overall Score** with actionable improvement suggestions

### 2. **Contrastive Explanations**
- Explains **why Job A ranks higher than Job B** for your profile
- Highlights key differentiators (skills, experience, role fit)
- Personalized to your background

### 3. **Counterfactual Suggestions (What-If Scenarios)**
- "If you add X skill, your match score improves from Y to Z"
- Quantified impact predictions
- Career boost recommendations

### 4. **Chain-of-Thought (CoT) Reasoning**
- Step-by-step AI decision process:
  - **Step 1:** Initial skill scan
  - **Step 2:** Experience level assessment
  - **Step 3:** Role fit analysis
  - **Step 4:** Final decision synthesis
- Transparent, auditable reasoning

---

## 🏗️ Architecture

### Backend (Python + LangGraph)

```
api/routers/advanced_candidate.py
├── CVExplainabilityGraph (LangGraph workflow)
│   ├── assess_cv_quality (Node 1)
│   ├── generate_contrastive_explanation (Node 2)
│   ├── generate_counterfactual_suggestions (Node 3)
│   └── chain_of_thought_reasoning (Node 4)
│
├── WebSocket: /advanced/ws/explain/{cv_id} (streaming)
└── REST: /advanced/explain/{cv_id} (non-streaming)
```

**Key Technologies:**
- **LangGraph**: Orchestrates multi-node AI workflow
- **LangChain LLM**: Powers reasoning (Ollama/OpenAI)
- **WebSocket**: Real-time event streaming
- **MemorySaver**: Checkpointing for advanced features

### Frontend (React + TypeScript)

```
web/src/components/candidate/
├── AIReasoningPanel.tsx         # Streaming node visualization
│   ├── Node progress indicators
│   ├── Token streaming simulation
│   └── Real-time WebSocket connection
│
└── AIInsightsDisplay.tsx        # Final results display
    ├── Quality score dashboard
    ├── Contrastive explanations
    ├── Counterfactual suggestions
    └── CoT reasoning viewer
```

**Visual Effects:**
- Animated node transitions (purple → green)
- Token-by-token text streaming (cursor blink)
- Progress bars for active nodes
- Color-coded scoring (green/yellow/red)

---

## 🚀 Usage

### For Premium Users

1. **Upload CV** with Premium toggle ON
2. **After matching completes**, AI analysis automatically starts
3. **Watch live streaming** of 4 reasoning nodes:
   - 🎯 CV Quality Assessment
   - 🔀 Match Comparison
   - 💡 Improvement Suggestions
   - 🧠 AI Reasoning Chain
4. **View detailed insights** below the analysis panel

### API Endpoints

#### WebSocket (Streaming - Recommended)
```bash
ws://localhost:8000/advanced/ws/explain/{cv_id}
```

**Events:**
- `init`: Connection established
- `node_start`: Node begins processing
- `node_complete`: Node finishes (includes partial results)
- `complete`: All analysis done (full results)
- `error`: Something went wrong

**Example Client:**
```javascript
const ws = new WebSocket('ws://localhost:8000/advanced/ws/explain/123');

ws.onmessage = (event) => {
    const data = JSON.parse(event.data);

    if (data.event === 'node_start') {
        console.log(`Starting: ${data.node}`);
    } else if (data.event === 'node_complete') {
        console.log(`Completed: ${data.node}`, data.data);
    } else if (data.event === 'complete') {
        console.log('All done!', data.data);
    }
};
```

#### REST (Non-Streaming)
```bash
GET /advanced/explain/{cv_id}
```

**Response:**
```json
{
  "cv_id": "123",
  "quality_score": {
    "overall_score": 82,
    "structure_formatting": 85,
    "content_completeness": 78,
    "ats_compatibility": 82,
    "keyword_optimization": 75,
    "professional_language": 88,
    "improvement_suggestions": [
      "Add quantifiable achievements with metrics",
      "Include more technical keywords",
      "Expand project descriptions"
    ]
  },
  "contrastive_explanation": "Job A ranks higher because...",
  "counterfactual_suggestions": [
    "If you add React.js, score improves from 72 to 85",
    "If you include GitHub projects, score improves by 10 points"
  ],
  "cot_reasoning": "Step 1 - Initial Skill Scan:\n..."
}
```

---

## 🎨 UI Components

### AIReasoningPanel (Streaming Visualization)

Shows real-time progress through 4 nodes:

```tsx
<AIReasoningPanel
  cvId="123"
  onComplete={(results) => console.log(results)}
/>
```

**Features:**
- Animated node transitions
- Token streaming simulation (typewriter effect)
- Progress bars for active nodes
- Checkmarks for completed nodes

### AIInsightsDisplay (Results Dashboard)

Displays final insights:

```tsx
<AIInsightsDisplay
  qualityScore={...}
  contrastiveExplanation={...}
  counterfactualSuggestions={[...]}
  cotReasoning={...}
/>
```

**Features:**
- Score gauges with color coding
- Detailed breakdowns per category
- Improvement suggestion cards
- Step-by-step reasoning viewer

---

## 🧪 Testing

### Prerequisites
```bash
# Ensure CV exists and has predictions
curl -X POST http://localhost:8000/candidate/upload \
  -F "file=@resume.pdf" \
  -F "action=match"
```

### Test WebSocket Streaming
```bash
# Use wscat or browser console
wscat -c ws://localhost:8000/advanced/ws/explain/YOUR_CV_ID
```

### Test REST Endpoint
```bash
curl http://localhost:8000/advanced/explain/YOUR_CV_ID
```

---

## 🔧 Configuration

### Toggle LLM Usage

In `core/configs.py`:
```python
USE_REAL_LLM = False  # Use mock responses for testing
USE_REAL_LLM = True   # Use actual LLM (Ollama/OpenAI)
```

### Customize Scoring Weights

In `advanced_candidate.py` → `analyze_factors()`:
```python
overall_score = (
    matching_factors["skills_match"] * 0.35 +      # Skills: 35%
    matching_factors["experience_match"] * 0.25 +  # Experience: 25%
    matching_factors["education_match"] * 0.15 +   # Education: 15%
    matching_factors["semantic_similarity"] * 0.25 # Semantic: 25%
)
```

---

## 🎯 Why This Is Cool

1. **Real-Time Streaming**: See AI thinking process live (not just final answer)
2. **Transparent Reasoning**: Chain-of-Thought shows "why" decisions were made
3. **Actionable Insights**: Counterfactual suggestions show exact improvement paths
4. **Premium UX**: Animated, token-streaming UI feels like ChatGPT Pro
5. **LangGraph Power**: Multi-node orchestration enables complex workflows
6. **Scalable**: Easy to add new analysis nodes (salary prediction, culture fit, etc.)

---

## 📊 Example Output

### CV Quality Score
```
Overall Score: 82/100 🟢

Structure & Format:     85 ████████░
Content Completeness:   78 ███████░░
ATS Compatibility:      82 ████████░
Keyword Optimization:   75 ███████░░
Professional Language:  88 ████████░

Top Improvements:
1. Add quantifiable achievements (e.g., "Increased performance by 40%")
2. Include 2-3 GitHub projects showcasing your skills
3. Add cloud certifications (AWS/Azure)
```

### Contrastive Explanation
```
"Senior Backend Engineer at TechCorp ranks higher than Full-Stack
Developer at StartupCo because your 5 years of Python/Django experience
strongly aligns with their backend-heavy tech stack, whereas the
full-stack role requires significant frontend skills (React/Vue)
which are underrepresented in your CV."
```

### Counterfactual Suggestions
```
💡 What-If Scenarios:

1. If you add Docker/Kubernetes certification, your match score for
   DevOps Engineer roles would improve from 72 to 85+

2. If you include 2-3 data analysis projects using pandas/numpy,
   your match score for Data Analyst positions would improve from
   68 to 80

3. If you quantify achievements with metrics, your overall ATS score
   would improve by 5-10 points across all roles
```

### Chain-of-Thought Reasoning
```
Step 1 - Initial Skill Scan:
Identified strong Python, Django, PostgreSQL expertise. Matches 8/10
required skills for Senior Backend Engineer role.

Step 2 - Experience Level Assessment:
5 years of backend experience aligns perfectly with "5-7 years"
requirement. Seniority level matches job expectations.

Step 3 - Role Fit Analysis:
Current trajectory from Mid-level to Senior is logical next step.
Responsibilities align with career growth goals.

Step 4 - Final Decision:
Strong match (85/100) with high confidence. Primary gaps are AWS
experience and containerization, both learnable skills that don't
impact core competency fit.
```

---

## 🚦 Next Steps

### Potential Enhancements

1. **Salary Prediction Node**: Estimate expected salary range based on CV
2. **Culture Fit Analysis**: Match personality/values with company culture
3. **Skill Transferability**: Show how current skills map to new domains
4. **Interactive What-If**: Let users simulate CV changes in real-time
5. **Multi-Hop RAG**: Fetch external data (Glassdoor, LinkedIn, tech trends)
6. **ReAct Tools**: Integrate GitHub API, certification validators, etc.

### Performance Optimizations

- Cache LLM responses per CV for faster re-runs
- Parallel node execution where possible (no dependencies)
- Streaming token-by-token from LLM (not just simulated)
- Add loading placeholders for smoother UX

---

## 🙏 Credits

Built with:
- **LangGraph** (orchestration)
- **LangChain** (LLM integration)
- **FastAPI** (WebSocket backend)
- **React** (streaming UI)
- **TailwindCSS** (beautiful animations)

---

**Enjoy your premium AI-powered career insights! 🚀**
