# ACRS — Automated Code Review System

GNN-powered structural code analysis. Detects bugs, code smells, and design inefficiencies using AST + CFG + DFG program graphs with Graph Attention Networks.

## Structure

```
acrs/
├── backend/              ← Flask API + GNN engine
│   ├── app.py            ← Main server
│   ├── requirements.txt
│   ├── parsers/          ← Python, Java, C/C++ AST parsers
│   ├── graph/            ← Program graph builder + feature encoder
│   ├── models/           ← GAT model + benchmark suite
│   └── utils/            ← Repo handler, report gen, graph exporter
├── frontend/             ← React + Vite UI
│   ├── package.json
│   ├── vite.config.js
│   ├── index.html
│   └── src/
│       ├── main.jsx
│       └── App.jsx       ← Full React app
└── notebook/             ← Jupyter EDA report
    ├── ACRS_EDA_Report.ipynb
    └── benchmark_results.json
```

## Setup

### 1. Backend

```bash
cd backend
pip install -r requirements.txt
python app.py
```

Flask runs on http://localhost:5000

### 2. Frontend

```bash
cd frontend
npm install
npm run dev
```

Vite runs on http://localhost:5173 (proxies API to Flask)

### 3. Jupyter Notebook (optional)

```bash
cd notebook
pip install jupyter matplotlib seaborn pandas numpy
jupyter notebook ACRS_EDA_Report.ipynb
```

## Usage

1. Start backend (terminal 1): `cd backend && python app.py`
2. Start frontend (terminal 2): `cd frontend && npm install && npm run dev`
3. Open http://localhost:5173
4. Paste a GitHub repo URL and click Scan
5. Or click Benchmark to run the 20-sample evaluation suite
