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
    PdfReader = None  # assicurati di includere PyPDF2 in requirements

# ---------- APP CONFIG ----------
st.set_page_config(page_title="Generatore Piano Alimentare", page_icon="🥗", layout="centered")

# ---------- PATOLOGIE SUPPORTATE ----------
SUPPORTED_PATHOLOGIES = {
    "diabetes": "Diabete / controllo glicemico",
    "hyperchol": "Ipercolesterolemia / colesterolo alto",
    "hypertension": "Ipertensione / riduzione sodio",
    "endometriosis": "Endometriosi / dieta anti‑infiammatoria",
    "celiac": "Celiachia / gluten‑free",
    "lactose": "Intolleranza al lattosio",
    "ibs": "IBS / colon irritabile (low‑FODMAP)",
    "ckd": "Malattia renale cronica (stadi 1‑3)",
    "fattyliver": "Steatosi epatica",
    "anemia": "Anemia sideropenica",
    "pcos": "Sindrome PCOS",
    "nickel": "Allergia al nichel",
    "fructose": "Intolleranza al fruttosio",
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
manual_path_text = st.sidebar.text_input("Patologie (virgola separate)")
show_free_meal = st.sidebar.checkbox("Mostra pasto libero", True)
manual_paths = [p.strip().lower() for p in manual_path_text.split(',') if p.strip()]

with st.sidebar.expander("ℹ️ Patologie gestite"):
    for c, d in SUPPORTED_PATHOLOGIES.items():
        st.markdown(f"**{c}** — {d}")

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

    for word in SUPPORTED_PATHOLOGIES:
        if word in text:
            data["conditions"].add(word)

    if "vegan" in text or "vegano" in text:
        data["diet"] = "vegan"

    data["activity"] = 1.2
    if "moderata" in text:
        data["activity"] = 1.55
    elif "intensa" in text:
        data["activity"] = 1.725
    return data

pdf_data = parse_pdf(pdf_file) if pdf_file else defaultdict(lambda: None)
for p in manual_paths:
    if p in SUPPORTED_PATHOLOGIES:
        pdf_data["conditions"].add(p)

if pdf_data["conditions"]:
    st.subheader("Patologie riconosciute")
    for c in sorted(pdf_data["conditions"]):
        st.write(f"• **{c}** — {SUPPORTED_PATHOLOGIES.get(c)}")
else:
    st.info("Nessuna patologia selezionata.")

# ---------- KCAL ----------
def calc_kcal(sex, w, h, age, act):
    if not all([sex, w, h, age]):
        return 2000
    bmr = 10*w + 6.25*h - 5*age + (5 if sex=='M' else -161)
    tdee = bmr*act
    if w and h and w/(h/100)**2 > 25:
        tdee -= 400
    return int(tdee)

kcal_target = manual_kcal or calc_kcal(pdf_data.get("sex"), pdf_data.get("weight"), pdf_data.get("height"), pdf_data.get("age"), pdf_data.get("activity",1.2))
st.sidebar.markdown(f"### 🔥 Kcal target: **{kcal_target}**")

def portion(base): return int(base * kcal_target / 2000)

SUPP_MAP = {
    "diabetes": ["Cannella 500 mg", "Cromo 200 µg"],
    "hyperchol": ["Omega‑3 1 g", "Riso rosso 10 mg"],
    "lactose": ["Vitamina D3 2000 UI", "Calcio citrato 500 mg"],
}

def generate_plan():
    doc = Document()
    run = doc.add_paragraph().add_run(header_date)
    run.bold = True; run.font.size = Pt(12)
    doc.add_heading(f"Piano alimentare per {patient_name}", level=1)
    doc.add_paragraph(f"Calorie target: {kcal_target} kcal"); doc.add_paragraph()

    if pdf_data["conditions"]:
        doc.add_paragraph("Condizioni: " + ", ".join(sorted(pdf_data["conditions"])).title()); doc.add_paragraph()

    doc.add_heading("INTEGRAZIONE", level=2)
    supp = []
    for c in pdf_data["conditions"]:
        supp += SUPP_MAP.get(c, [])
    if not supp:
        supp = ["Multivitaminico quotidiano"]
    for s in supp:
        doc.add_paragraph(s, style="List Bullet")

    doc.add_heading("ESEMPIO GIORNATA", level=2)
    doc.add_paragraph("Colazione: Fiocchi avena 40 g + latte p.s. + banana")
    doc.add_paragraph("Pranzo: Insalata + pollo + pane integrale 50 g")
    doc.add_paragraph("Cena: Salmone + verdure + riso 60 g")

    if show_free_meal:
        doc.add_paragraph(); doc.add_heading("PASTO LIBERO", level=2)
        doc.add_paragraph("Una volta a settimana: pizza a scelta")

    footer = doc.add_paragraph("Martina Rastelli\nBIOLOGA NUTRIZIONISTA")
    footer.alignment = 2

    buf = io.BytesIO(); doc.save(buf); return buf

if st.button("Genera piano alimentare"):
    buf = generate_plan()
    st.success("Piano generato!")
    st.download_button("📥 Scarica DOCX", buf.getvalue(), file_name=f"Dieta_{patient_name.replace(' ','_')}.docx",
                       mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document")
