# AI-Legal-Assistance

Transform your legal-document workflow: draft, customize, and review NDAs, contracts, and wills in **minutes**—no legal team required.

<p align="center">
  <img src="docs/screenshot.png" width="600" alt="AI-Legal-Assistance screenshot">
</p>

---

## ✨  Features
|  |  |
|---|---|
| ✍️ **Smart Document Generation** | One-click creation of properly formatted NDAs, contracts, and wills |
| 🔧 **Custom Tailoring** | Adapt clauses to any jurisdiction, governing law, or party details |
| 🔍 **AI Document Review** | Upload an existing agreement and receive actionable red-flag suggestions |
| 📑 **Professional PDFs** | Download press-ready, paginated PDFs—no post-processing needed |

---

## 🏗  Technology Stack
| Layer | Tech |
|-------|------|
| **UI** | React + Tailwind (responsive SPA) |
| **API** | Flask + FastAPI routers |
| **LLM** | OpenAI GPT-4o via LangChain prompt orchestration |
| **Storage** | PostgreSQL for user metadata; S3 for document versions |
| **PDF Engine** | WeasyPrint & ReportLab for pixel-perfect output |

---

## ⚙️  Quick Start

```bash
# 1) Backend
git clone https://github.com/yourusername/ai-legal-assistance.git
cd ai-legal-assistance/backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
export OPENAI_API_KEY=<your-key>
python app.py          # runs on http://localhost:5000
