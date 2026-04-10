
# AI Travel & Logistics Planner

A production-ready AI-powered system with LangGraph multi-agent routing, traffic-aware maps, and multi-input support.

---

## 🚀 Quick Setup

### 1. Install Dependencies

```bash
cd travel_planner
pip install -r requirements.txt
```

### 2. Configure Environment

```bash
cp .env.example .env
```

Edit `.env` with your actual API credentials:

```
API_ENDPOINT=
API_KEY=your_actual_api_key
MODEL=
EMBEDDING_MODEL=
ADMIN_SECRET_KEY=your_admin_secret
```

### 3. Run the Application

```bash
streamlit run app.py
```

Open: http://localhost:8501

---

## 📁 Project Structure

```
travel_planner/
├── app.py                 # Main Streamlit entry + auth routing
├── database.py            # SQLite DB + auth helpers
├── llm_client.py          
├── embedding_client.py    # Embedding API client
├── rag_memory.py          # ChromaDB RAG memory
├── routing.py             # VRP + Traffic routing logic
├── map_generator.py       # Folium map with traffic
├── agents.py              # All 10 LangGraph agents + workflow
├── csv_processor.py       # CSV parsing + normalization
├── plan_renderer.py       # Shared plan result UI
├── user_chat.py           # Chat-based planner page
├── user_form.py           # Form-based planner page
├── user_csv.py            # CSV upload planner page
├── user_plans.py          # Past plans view/manage
├── admin_dashboard.py     # Admin analytics dashboard
├── requirements.txt
├── .env.example
└── README.md
```

---

## 🎯 Features

### User App

- **Chat Input**: Natural language plan creation and modification
- **Form Input**: Structured multi-field form
- **CSV Upload**: Auto-detect columns, preview, generate
- **Plan Modification**: Update existing plan via any input method
- **Plan States**: generated → accepted/modified/rejected
- **Map**: Folium + OpenStreetMap + traffic color coding
- **Download**: Route as CSV

### Admin Dashboard

- Total users, plans, acceptance rate
- Plan status distribution (pie chart)
- Input source usage (bar chart)
- Plans per day trend (line chart)
- Plans per user (bar chart)
- Full activity log
- All users + itineraries table

### LangGraph Agents

1. **INPUT_AGENT** – Normalize form/chat/CSV
2. **INTENT_AGENT** – Detect new vs modify
3. **RAG_AGENT** – ChromaDB similarity retrieval
4. **PLANNING_AGENT** – LLM plan enhancement
5. **UPDATE_AGENT** – Smart plan modification
6. **ROUTING_AGENT** – VRP + time windows + capacity
7. **MAP_AGENT** – Folium HTML generation
8. **EXPLANATION_AGENT** – Natural language explanation
9. **MEMORY_AGENT** – SQLite + ChromaDB persistence
10. **LOGGING_AGENT** – Action tracking

### Traffic Simulation

| Time Window | Factor | Color     |
| ----------- | ------ | --------- |
| 09:00–11:00 | 1.5x   | 🔴 Red    |
| 17:00–19:00 | 1.6x   | 🔴 Red    |
| 11:00–17:00 | 1.2x   | 🟠 Orange |
| 06:00–09:00 | 1.1x   | 🟡 Yellow |
| Night       | 1.0x   | 🟢 Green  |

---

## 🔐 Authentication

- **User signup**: Username + Password
- **Admin signup**: Username + Password + Admin Secret Key
- **Admin Secret**: Set `ADMIN_SECRET_KEY` in `.env`

---

## 📤 CSV Format

| Column          | Aliases                    | Required         |
| --------------- | -------------------------- | ---------------- |
| name            | stop_name, location, place | Yes              |
| lat             | latitude, y                | Yes              |
| lng             | longitude, lon, x          | Yes              |
| priority        | prio, importance           | No (default: 2)  |
| service_time    | service_time_min, dwell    | No (default: 15) |
| weight          | package_weight, load, kg   | No (default: 0)  |
| delivery_window | window, time_window, slot  | No               |

---


- If LLM is unavailable, routing still works with raw form/CSV data
