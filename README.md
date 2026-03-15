# BiasCheck 🔍

![Python](https://img.shields.io/badge/Python-3.10+-3776AB?style=flat&logo=python&logoColor=white)
![Django](https://img.shields.io/badge/Django-4.x-092E20?style=flat&logo=django&logoColor=white)
![Groq](https://img.shields.io/badge/Groq-GPT--OSS%2020B-F55036?style=flat&logo=groq&logoColor=white)
![NewsAPI](https://img.shields.io/badge/NewsAPI-enabled-black?style=flat)
![License](https://img.shields.io/badge/License-MIT-green?style=flat)
![Status](https://img.shields.io/badge/Status-Hackathon%20Build-orange?style=flat)
![Built at](https://img.shields.io/badge/Built%20at-BirmingHack%202026-purple?style=flat)


<img src="https://github.com/CrawfoBP23/BiasCheck/blob/c237359373aa4e01909753ecaf2f95de612814cb/analyzer/static/biascheck-white.png" width="300">

> *In 2021, a WhatsApp message told 3 million people that vaccines contained a microchip — before any fact-check could reach them. It came too late. The belief was already alive. BiasCheck is about reversing that.*

BiasCheck is a real-time news bias and misinformation analyzer. Paste a claim, drop a URL, or search a topic — and get an instant breakdown of political bias, emotional language, and unverified claims. **The user decides the views themselves.**

---

## Features

- **Bias detection** — scores articles from -10 (far left) to +10 (far right) with political position, indicators, claims, and summary
- **Misinformation check** — flags unverified claims against trusted sources
- **Emotional language detection** — features engineering using scoring of evidence vs persuasion used
- **Bias quadrant chart** — visualises story framing and political spectrum in a bias quadrant
- **Source filtering** — excludes unverified user-generated, conspiracy-leaning, opinion-based, and no editorial oversight websites
- **Full article extraction** — scrapes and reads full article content via Trafilatura
- **Multi-article analysis** — analyzes all articles in parallel using async LLM requests
- **Verdict summary** — calculates an overall verdict and summarises all findings across articles

---

## How It Works

```
User inputs a topic or claim
        ↓
  Query sent to Google News RSS + NewsAPI
        ↓
  Exclude unverified, conspiracy-leaning,
  opinion-based, no editorial websites
        ↓
  Scrape full article content via Trafilatura
        ↓
  Each article analysed for political or emotional bias
  (left vs right) using Groq + OpenAI
        ↓
        ├── Political position, bias score,
        │   indicators, claims, summary
        │
        └── Features engineering:
            scoring of evidence vs persuasion used
        ↓
  Calculate verdict and summarise all findings
        ↓
  Visualise story framing and political spectrum
  in a bias quadrant chart
        ↓
  The user decides the views themselves
```

---

## Tech Stack

| Layer | Technology |
|---|---|
| Backend | Django |
| LLM | Groq (GPT-OSS 20B) + OpenAI |
| News source | Google News RSS + NewsAPI |
| Article extraction | Trafilatura |
| URL decoding | googlenewsdecoder |
| Async processing | asyncio + AsyncGroq |

---

## Getting Started

### Prerequisites
- Python 3.10+
- [Groq API key](https://console.groq.com) (free, no credit card)
- [NewsAPI key](https://newsapi.org/register) (free tier)

### Installation

```bash
git clone https://github.com/yourusername/biascheck.git
cd biascheck
pip install -r requirements.txt
cp .env.example .env
```

### Environment variables

```
NEWS_API_KEY=your_newsapi_key
GROQ_API_KEY=your_groq_api_key
```

### Run

```bash
python manage.py migrate
python manage.py runserver
```

Visit `http://127.0.0.1:8000`

---

## Bias Scale

| Score | Label |
|---|---|
| 0 | Not biased |
| 1–20% | Minimal bias |
| 21–60% | Moderate bias |
| 61–80% | Strong bias |
| 81–100% | Highly biased |

---

## Excluded Domains

BiasCheck automatically filters out unverified user-generated, conspiracy-leaning, opinion-based, and sites with no editorial oversight — including social media platforms, unmoderated blogs, and state propaganda outlets. Trusted sources like Reuters, AP News, BBC, and fact-checking organizations are prioritized.

---

## What's Next

- Browser extension to analyze articles without leaving the page
- Cross-source comparison of the same story across outlets
- Claim tracking across multiple articles over time
- User history with bias trends of most-read sources
- Multilingual support

---

## License

MIT
