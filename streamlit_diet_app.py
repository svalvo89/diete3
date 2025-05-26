import streamlit as st
from docx import Document
from docx.shared import Pt
import io
from datetime import date
import re
from collections import defaultdict

try:
    from PyPDF2 import PdfReader
except ImportError:
    PdfReader = None  # assicurati che PyPDF2 sia in requirements.txt

# ---------- APP CONFIG ----------
st.set_page_config(page_title="Generatore Piano Alimentare", page_icon="🥗", layout="centered")

# ---------- PATHOLOGIES ----------
SUPPORTED_PATHOLOGIES = {
    "diabetes": "Diabete / controllo glicemico",
    "hyperchol": "Ipercolesterolemia / colesterolo alto",
    "hypertension": "Ipertensione / riduzione sodio",
    "endometriosis": "Endometriosi / dieta anti‑infiammatoria",
    "celiac": "Celiachia / gluten‑free",
    "lactose": "Intolleranza al lattosio",
    "ibs": "IBS / colon irritabile (low‑FODMAP)",
    "ckd": "Malattia renale cronica (stadi 1‑3)",
    "fattyliver": "Steatosi epatica / dieta ipolipidica",
    "anemia": "Anemia sideropenica / ferro + vit. C",
    "pcos": "Sindrome PCOS / low‑GI",
    "nickel": "Allergia al nichel / dieta low‑Ni",
    "fructose": "Intolleranza al fruttosio / FODMAP ridotto",
}

# ---------- SIDEBAR ----------
st.sidebar.header("📋 Dati paziente")
patient_name = st.sidebar.text_input("Nome paziente", "Nome Cognome")
place = st.sidebar.text_input("Luogo", "Frascati")
selected_date = st.sidebar.date_input("Data del piano", date.today())
header_date = f"{place}, {selected_date.strftime('%d %B %Y')}"

st.sidebar.header("📑 Anamnesi (opzionale)")
pdf_file = st.sidebar.file_uploader("Carica scheda (PDF)", type=["pdf"])

st.sidebar.header("⚙️ Impostazioni manuali")
manual_kcal = st.sidebar.number_input("Kcal target (0 = auto)", 0, 5000, 0)
manual_pathologies_text = st.sidebar.text_input("Patologie/condizioni (virgola separate)")
show_free_meal = st.sidebar.checkbox("Mostra pasto libero", True)
manual_pathologies = [p.strip().lower() for p in manual_pathologies_text.split(',') if p.strip()]

with st.sidebar.expander("ℹ️ Patologie gestite"):
    for code, desc in SUPPORTED_PATHOLOGIES.items():
        st.markdown(f"**{code}** — {desc}")

st.title("🥗 Generatore diete personalizzate")

# ---------- UTILS ----------
def extract_first(pattern, text, cast=float, default=None):
    m = re.search(pattern, text)
    if m:
        try:
            return cast(m.group(1).replace(',', '.'))
        except ValueError:
            return default
    return default

def parse_pdf(pdf):
    data = defaultdict(lambda: None)
    if not PdfReader:
        return data
    try:
        reader = PdfReader(pdf)
        text = "\n".join((p.extract_text() or "") for p in reader.pages).lower()
    except Exception as e:
        st.warning(f"Errore lettura PDF: {e}")
        return data

    data["weight"] = extract_first(r"(\d{2,3})\s*kg", text)
    data["height"] = extract_first(r"(\d{3})\s*cm", text)
    data["age"] = extract_first(r"et[àa]\s*(\d{1,2})", text, int)

    if "maschio" in text or re.search(r"\b(m)\b", text):
        data["sex"] = "M"
    elif "femmina" in text or re.search(r"\b(f)\b", text):
        data["sex"] = "F"

    syn = {
        "diabete":"diabetes","glicemia":"diabetes","diabetes":"diabetes",
        "ipercolesterolemia":"hyperchol","colesterolo":"hyperchol",
        "ipertensione":"hypertension","pressione alta":"hypertension",
        "endometriosi":"endometriosis",
        "celiachia":"celiac","gluten":"celiac","senza glutine":"celiac",
        "lattosio":"lactose","intolleranza lattosio":"lactose",
        "ibs":"ibs","colon irritabile":"ibs",
        "ckd":"ckd","renale cronica":"ckd","insufficienza renale":"ckd",
        "steatosi":"fattyliver","fegato grasso":"fattyliver",
        "anemia":"anemia","ferro basso":"anemia",
        "pcos":"pcos","ovaio policistico":"pcos",
        "nichel":"nickel","allergia nichel":"nickel",
        "fruttosio":"fructose","intolleranza fruttosio":"fructose"
    }
    data["conditions"] = {code for k, code in syn.items() if k in text}

    if "vegan" in text or "vegano" in text:
        data["diet"] = "vegan"
    elif "vegetarian" in text or "vegetariano" in text:
        data["diet"] = "vegetarian"

    # attività
    data["activity"] = 1.2
    if any(k in text for k in ["leggera","1-2"]): data["activity"] = 1.375
    elif any(k in text for k in ["moderata","3-5"]): data["activity"] = 1.55
    elif any(k in text for k in ["intensa","6-7"]): data["activity"] = 1.725
    return data

pdf_data = parse_pdf(pdf_file) if pdf_file else defaultdict(lambda: None)
for p in manual_pathologies:
    if p in SUPPORTED_PATHOLOGIES:
        pdf_data["conditions"].add(p)

if pdf_data["conditions"]:
    st.subheader("Patologie riconosciute")
    for c in sorted(pdf_data["conditions"]):
        st.markdown(f"• **{c}** — {SUPPORTED_PATHOLOGIES.get(c, 'custom')}")
else:
    st.info("Nessuna patologia riconosciuta/selezionata.")

# kcal
def calc_kcal(sex,w,h,age,act):
    if not all([sex,w,h,age]): return 2000
    bmr = 10*w + 6.25*h - 5*age + (5 if sex=='M' else -161)
    tdee = bmr*act
    if w and h and w/(h/100)**2 > 25: tdee -= 400
    return int(tdee)

kcal_target = manual_kcal or calc_kcal(pdf_data.get("sex"), pdf_data.get("weight"), pdf_data.get("height"), pdf_data.get("age"), pdf_data.get("activity",1.2))
st.sidebar.markdown(f"### 🔥 Kcal target: **{kcal_target}**")

def portion(base): return int(base * kcal_target / 2000)

SUPP_MAP = {
    "hyperchol":["Omega‑3 1 g","Riso rosso 10 mg"],
    "diabetes":["Cannella 500 mg","Cromo 200 µg"],
    "lactose":["Vit D3 2000 UI","Ca citrato 500 mg"],
}

def generate_plan():
    doc = Document()
    run = doc.add_paragraph().add_run(header_date)
    run.bold=True; run.font.size=Pt(12)
    doc.add_heading(f"Piano alimentare per {patient_name}", level=1)
    doc.add_paragraph(f"Calorie target: {kcal_target} kcal"); doc.add_paragraph()

    cond = pdf_data["conditions"]
    if cond:
        doc.add_paragraph("Condizioni: "+", ".join(sorted(cond)).title()); doc.add_paragraph()

    doc.add_heading("INTEGRAZIONE", level=2)
    supp=[]
    for c in cond: supp+=SUPP_MAP.get(c,[])
    if not supp: supp=["Multivitaminico quotidiano"]
    for s in supp: doc.add_paragraph(s, style="List Bullet")

    def add_sec(title, opts):
        doc.add_heading(title, level=2)
        for i,o in enumerate(opts,1): doc.add_paragraph(f"{i}) {o}", style="List Number")
        doc.add_paragraph()

    gf='celiac' in cond; no_lact='lactose' in cond
    bread_p=portion(50); cereal_p=portion(40)

    add_sec("Colazione", [
        f"{cereal_p} g fiocchi avena"+(" GF" if gf else "")+(" con bevanda soia" if no_lact else " con latte p.s."),
        f"Toast {bread_p} g pane"+(" SG" if gf else " integrale")+" avocado + uova",
        ("Yogurt soia" if no_lact else "Yogurt greco")+" + frutti di bosco",
        "Pancake avena + albume",
        "Smoothie verde proteico"
    ])

    add_sec("Spuntino mattutino", ["Frutta", "Mandorle 15 g", "Barretta low‑sugar"])

    add_sec("Pranzo", [
        "Insalata + legumi",
        "Pasta integrale 70 g + verdure",
        "Riso basmati + tonno + verdure"
    ])

    add_sec("Spuntino pomeriggio", ["Yogurt + noci", "Cioccolato 90% + nocciole", "Spremuta + pistacchi"])

    add_sec("Cena", [
        "Verdure + 2 uova",
        "Salmone al forno + asparagi",
        "Burger ceci + carote"
    ])

    add_sec("Spuntino serale", ["Tisana + cioccolato", "Kefir 100 ml", "Nice‑cream banana"])

    if show_free_meal:
        doc.add_heading("PASTO LIBERO", level=2)
        doc.add_paragraph("1 volta a settimana: pizza (SG se gf) o primo a scelta")

    footer = doc.add_paragraph("Martina Rastelli\nBIOLOGA NUTRIZIONISTA")
    footer.alignment=2
    buf=io.BytesIO()
    doc.save(buf)
    return buf

if st.button("Genera piano alimentare"):
    filebuf = generate_plan()
    st.success("Piano generato!")
    st.download_button("📥 Scarica DOCX", filebuf.getvalue(), file_name=f"Dieta_{patient_name.replace(' ','_')}.docx", mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document")
