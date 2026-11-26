# HealthMap (Streamlit)

    pip install -r requirements.txt
    streamlit run app.py

- `data/index.json` – the 16 fields and 355 topics.
- `content/<topic number>.json` – write-ups for one topic, as nested
  `{"title": ..., "text": ..., "children": [...]}`. Included: 56 (ECG), 167 (FHIR), 237 (Pharmacokinetics).
