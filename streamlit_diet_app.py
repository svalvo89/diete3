
import streamlit as st
from docx import Document
from docx.shared import Pt
import io
from datetime import date

st.set_page_config(page_title="Generatore Piano Alimentare", page_icon="🥗", layout="centered")

# -------------------- SIDEBAR INPUTS -------------------- #
st.sidebar.header("Dati Paziente")
patient_name = st.sidebar.text_input("Nome paziente", "Rossi Paolo")
place = st.sidebar.text_input("Luogo", "Frascati")

# Upload anamnesi PDF
st.sidebar.header("Anamnesi")
pdf_file = st.sidebar.file_uploader("Carica scheda anamnesi (PDF)", type=["pdf"])

if pdf_file is not None:
    st.sidebar.success("Anamnesi caricata correttamente ✔️")

# Date
custom_date = st.sidebar.date_input("Data del piano", date.today())
header_date = f"{place}, {custom_date.strftime('%d %B %Y')}"

# Preferenze dieta
st.sidebar.header("Preferenze dieta")
carb_scale = st.sidebar.slider("Riduzione carboidrati serali (%)", 0, 100, 40)
alcohol_limit = st.sidebar.number_input("Bicchieri di vino week‑end", 0, 4, 2)

# Checkbox sezioni
show_supplements = st.sidebar.checkbox("Mostra integrazione", value=True)
show_free_meal = st.sidebar.checkbox("Mostra pasto libero", value=True)

st.title("🥗 Generatore di Diete Personalizzate")

# -------------------- FUNZIONE DI GENERAZIONE -------------------- #
def generate_plan():
    doc = Document()

    # Header
    p = doc.add_paragraph()
    run = p.add_run(header_date)
    run.bold = True
    run.font.size = Pt(12)

    doc.add_heading(f"Piano alimentare per {patient_name}", level=1)
    doc.add_paragraph()

    # Nota PDF allegato
    if pdf_file is not None:
        doc.add_paragraph("Anamnesi caricata in allegato e tenuta in considerazione per la stesura del piano.")
        doc.add_paragraph()

    # Integrazione
    if show_supplements:
        doc.add_heading("INTEGRAZIONE", level=2)
        supplements = [
            "Omega‑3 (1 g) a pranzo",
            "Riso rosso fermentato a cena",
            "Vitamina C 500 mg colazione",
            "Magnesio bisglicinato 300 mg sera",
            "Vitamina D3 2000 UI mattino"
        ]
        for s in supplements:
            doc.add_paragraph(s, style="List Bullet")
        doc.add_paragraph()

    # Note generali
    doc.add_heading("NOTE GENERALI", level=2)
    notes = [
        "Obiettivo: riduzione colesterolo <200 mg/dL e peso -0,5 kg/set.",
        "Idratazione: 2,5 l acqua/die; caffè max 3 espresso.",
        "Olio EVO 1 cucchiaio a pasto.",
        "Evitare alimenti non tollerati (fungi, melanzane, cavoli, finocchi, olive).",
        f"Alcol: massimo {alcohol_limit} bicchieri di vino nel week‑end.",
        "Allenamento: cardio 3× + forza 2× a settimana."
    ]
    for n in notes:
        doc.add_paragraph(n, style="List Bullet")

    doc.add_paragraph()

    # Helper
    def add_block(title, options):
        doc.add_heading(title, level=2)
        for i, opt in enumerate(options, 1):
            doc.add_paragraph(f"{i}) {opt}", style="List Number")
        doc.add_paragraph()

    # Pasti
    breakfast = [
        "Pane integrale tostato + marmellata 100% + latte p.s. + caffè",
        "Yogurt greco 0 % + kiwi + noci",
        "Porridge avena + mandorle + mirtilli",
        "Fette biscottate integrali + ricotta + miele + fragole"
    ]
    add_block("Colazione (ore 7:00‑7:30)", breakfast)

    snack_m = ["Mela", "Mandorle"]
    add_block("Spuntino mattutino (ore 10:30)", snack_m)

    lunch = [
        "Insalata mista + farro + pollo grigliato",
        "Verdura cruda + riso basmati + tonno naturale",
        "Insalatona ceci + pane integrale + verdure",
        "Pasta integrale al pomodoro + parmigiano + zucchine grigliate"
    ]
    add_block("Pranzo (ore 13:30)", lunch)

    snack_a = ["Yogurt magro + nocciole", "Cioccolato fondente + mandorle"]
    add_block("Spuntino pomeridiano (ore 16:30‑17:00)", snack_a)

    # Carbo serali
    base_carbs = 40
    adjusted_carbs = int(base_carbs * (100 - carb_scale) / 100)

    dinner = [
        f"Verdure al vapore + 2 uova + {adjusted_carbs} g pane integrale",
        "Burger manzo magro + insalata + patata dolce 200 g",
        f"Ricotta vaccina + spinaci + {max(adjusted_carbs - 10, 0)} g pane segale",
        "Burger ceci + carote al forno + olio EVO"
    ]
    add_block("Cena (ore 20:00)", dinner)

    doc.add_heading("DOPO CENA", level=2)
    doc.add_paragraph("Tisana rilassante; 1 quadratino cioccolato fondente se desiderato.")
    doc.add_paragraph()

    if show_free_meal:
        doc.add_heading("PASTO LIBERO", level=2)
        doc.add_paragraph("Una volta a settimana: pizza margherita + verdure oppure primo piatto a scelta.")

    doc.add_paragraph()
    footer = doc.add_paragraph("Martina Rastelli\nBIOLOGA NUTRIZIONISTA")
    footer.alignment = 2

    buffer = io.BytesIO()
    doc.save(buffer)
    return buffer

# -------------------- MAIN -------------------- #
if st.button("Genera piano"):
    file_buffer = generate_plan()
    st.success("Piano generato con successo!")
    st.download_button(
        "📥 Scarica DOCX",
        file_buffer.getvalue(),
        file_name=f"Dieta_{patient_name.replace(' ', '_')}.docx",
        mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    )

    st.info("Anteprima:")
    st.write("_Apri il file scaricato per l'impaginazione completa._")
else:
    st.write("Compila i campi nella sidebar, carica l'anamnesi se disponibile e clicca **Genera piano**.")
