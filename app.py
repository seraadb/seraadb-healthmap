import json
import textwrap
from pathlib import Path

import streamlit as st

ROOT = Path(__file__).parent

st.set_page_config(page_title="HealthMap", page_icon="🩺", layout="wide")


# ---------- data ----------
@st.cache_data
def load_index():
    return json.loads((ROOT / "data" / "index.json").read_text(encoding="utf-8"))


@st.cache_data
def load_content(n: int):
    p = ROOT / "content" / f"{n}.json"
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else None


def load_done() -> set:
    # Progress lives in each visitor's own session (a shared file would mix
    # everyone's ticks on a public site). Add a database later for saved accounts.
    return set()


def save_done(done: set):
    pass


CATS = load_index()
if "done" not in st.session_state:
    st.session_state.done = load_done()


# ---------- navigation (URL query params, so pages are linkable) ----------
def go(**params):
    st.query_params.clear()
    st.query_params.update(params)


def toggle_done(n: int):
    d = st.session_state.done
    d.symmetric_difference_update({n})
    save_done(d)


# ---------- views ----------
def home():
    st.title("🩺 HealthMap")
    total = sum(len(c["topics"]) for c in CATS)
    st.caption(f"{total} topics across {len(CATS)} fields. Choose a field to begin.")
    for row in range(0, len(CATS), 4):
        cols = st.columns(4)
        for col, c in zip(cols, CATS[row:row + 4]):
            nums = {t["n"] for t in c["topics"]}
            done = len(nums & st.session_state.done)
            with col.container(border=True):
                st.caption(f"Field {c['letter']}")
                st.subheader(c["name"])
                st.progress(done / len(nums), text=f"{done} of {len(nums)} studied")
                st.button("Open field", key=f"c{c['letter']}", on_click=go,
                          kwargs={"cat": c["letter"]}, use_container_width=True)


def category(letter: str):
    c = next((x for x in CATS if x["letter"] == letter), None)
    if not c:
        return go()
    st.button("‹ All fields", on_click=go)
    st.title(c["name"])
    q = st.text_input("Search this field", placeholder="e.g. FHIR").strip().lower()
    topics = [t for t in c["topics"] if q in t["name"].lower()]
    if not topics:
        st.info("No topic matches your search.")
    for row in range(0, len(topics), 3):
        cols = st.columns(3)
        for col, t in zip(cols, topics[row:row + 3]):
            mark = " ✓" if t["n"] in st.session_state.done else ""
            col.button(f"{t['n']}. {t['name']}{mark}", key=f"t{t['n']}",
                       on_click=go, kwargs={"cat": letter, "topic": t["n"]},
                       use_container_width=True)


def node_at(root, path):
    node = root
    for i in path:
        node = node["children"][i]
    return node


def build_dot(root, sel):
    lines = ['digraph{rankdir=LR; bgcolor="transparent";'
             'node[shape=box,style="rounded,filled",fontname="Helvetica",margin="0.15,0.08"];'
             'edge[color="#8aa"];']

    def add(node, p):
        nid = "n" + "".join(f"_{i}" for i in p)
        label = textwrap.fill(node["title"], 22).replace('"', "'").replace("\n", "\\n")
        fill, font = ("#0f766e", "white") if p == sel else ("#e6f1f3", "#0e2a33")
        lines.append(f'{nid}[label="{label}",fillcolor="{fill}",fontcolor="{font}"];')
        if sel[:len(p)] == p:  # branch is open if it is on the path to the selected node
            for i, child in enumerate(node.get("children", [])):
                lines.append(f"{nid} -> {nid}_{i};")
                add(child, p + [i])

    add(root, [])
    return "\n".join(lines) + "}"


def topic(letter: str, n: int):
    meta = next(((c, t) for c in CATS for t in c["topics"] if t["n"] == n), None)
    if not meta:
        return go()
    c, t = meta
    st.button(f"‹ {c['name']}", on_click=go, kwargs={"cat": letter})
    st.title(t["name"])
    st.caption(f"Field {c['letter']} › Topic {n}")

    root = load_content(n)
    if root is None:
        st.info("Write-ups for this topic are being prepared. Add `content/"
                f"{n}.json` to publish it.")
        return

    key = f"path_{n}"
    st.session_state.setdefault(key, [])
    sel = st.session_state[key]
    node = node_at(root, sel)

    def setp(p):
        st.session_state[key] = p

    left, right = st.columns([3, 2])
    with left:
        st.graphviz_chart(build_dot(root, sel), use_container_width=True)
    with right:
        with st.container(border=True):
            titles = [root["title"]]
            cur = root
            for i in sel:
                cur = cur["children"][i]
                titles.append(cur["title"])
            st.caption(" › ".join(titles[:-1]) or "Topic overview")
            st.subheader(node["title"])
            st.write(node["text"])
            if not sel:
                label = "Studied ✓" if n in st.session_state.done else "Mark as studied"
                st.button(label, on_click=toggle_done, args=(n,))
        kids = node.get("children", [])
        if kids:
            st.markdown("**Open a branch**")
            for i, k in enumerate(kids):
                st.button(k["title"], key=f"{key}_{sel}_{i}", on_click=setp,
                          args=(sel + [i],), use_container_width=True)
        if sel:
            c1, c2 = st.columns(2)
            c1.button("↑ Up one level", on_click=setp, args=(sel[:-1],),
                      use_container_width=True)
            c2.button("Back to start", on_click=setp, args=([],),
                      use_container_width=True)


# ---------- router ----------
qp = st.query_params
if "topic" in qp and "cat" in qp and str(qp["topic"]).isdigit():
    topic(qp["cat"], int(qp["topic"]))
elif "cat" in qp:
    category(qp["cat"])
else:
    home()
