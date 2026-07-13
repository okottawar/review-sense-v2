# Fuzzy Logic Satisfaction Analyzer

A single-page app that runs a hand-built Mamdani-style fuzzy inference engine
over product review data (rating + sentiment) to produce interpretable
satisfaction scores. No database, no build step, no frontend framework.

## Expected CSV columns

Matches the [Synthetic E-commerce Product Reviews Dataset](https://www.kaggle.com/datasets/aryan208/synthetic-e-commerce-product-reviews-dataset):

- `rating` (1-5, required)
- `sentiment` (Positive / Neutral / Negative, required)
- any other columns (`product_id`, `product_title`, `category`, `review_text`, ...) are preserved and passed through untouched.

## How the fuzzy engine works

- **Inputs**: `rating` (fuzzified into Low/Medium/High) and `sentiment` (mapped
  Negative=0, Neutral=0.5, Positive=1, then fuzzified into Low/Medium/High membership).
- **Rules**: 9 rules covering all rating x sentiment combinations (`core/rules.py`).
- **Inference**: Mamdani min-based rule strength, max-aggregation across rules
  firing the same output term.
- **Defuzzification**: centroid (center-of-gravity) method over a discretized
  0-100 output domain.
- **Category**: Low (<40), Medium (40-65), High (>65) satisfaction score.

Pure Python, no `scikit-fuzzy` dependency — keeps the Vercel serverless
function lightweight and fast to cold-start.

## Local development

```bash
pip install -r requirements.txt
uvicorn api.analyze:app --reload --port 8000
```

In a second terminal, serve the frontend:

```bash
cd public && python3 -m http.server 8080
```

Open `http://127.0.0.1:8080`. Note: for local dev the frontend calls
`/api/analyze` as a relative path, so you'll want a proxy or to run
`vercel dev` instead for a fully wired local setup (recommended):

```bash
npm i -g vercel
vercel dev
```

## Deploy to Vercel

```bash
vercel
```

That's it — `vercel.json` routes `/api/*` to the Python serverless function
and everything else to the static `public/` folder.

## Folder structure

```
api/analyze.py          FastAPI app (single serverless function)
core/
  membership.py          Triangular/trapezoidal fuzzy membership functions
  rules.py                Rule base (rating x sentiment -> satisfaction)
  engine.py                Fuzzification, inference, defuzzification
  analyzer.py               Runs the engine over a full dataframe, builds summary
utils/csv_processor.py    CSV parsing/validation
public/
  index.html
  styles.css
  app.js
requirements.txt
vercel.json
```
