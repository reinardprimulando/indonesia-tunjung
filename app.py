import os
import csv
import re
import random
import time
import streamlit as st
import streamlit.components.v1 as components
from google import genai
from google.genai import types # <--- ADD THIS LINE HERE

# --- 1. Konfigurasi Halaman ---
st.set_page_config(page_title="Penerjemah Dayak Tonyooi", page_icon="🌍")
st.title("🌍 Penerjemah Bahasa Dayak Tonyooi")
st.write("Terjemahkan teks antara Bahasa Indonesia dan Bahasa Dayak Tonyooi secara instan menggunakan AI.")

# --- 2. Inisialisasi Klien API ---
try:
    client = genai.Client()
except Exception as e:
    st.error("Kunci API tidak ditemukan. Harap konfigurasikan secrets Streamlit Anda.")
    st.stop()

# --- 3. Fungsi Inti ---
@st.cache_data 
def load_csv_corpus(file_path):
    """Membaca dataset CSV dan mengubahnya menjadi list of dictionary."""
    dataset = []
    try:
        with open(file_path, mode='r', encoding='utf-8') as f:
            reader = csv.reader(f)
            for row in reader:
                if len(row) >= 2:
                    dataset.append({
                        "Indonesian": row[0].strip(),
                        "Dayak_Tonyooi": row[1].strip()
                    })
    except FileNotFoundError:
        st.error(f"Galat: Tidak dapat menemukan file dataset {file_path}")
    return dataset

def find_relevant_examples(input_text, source_lang, dataset):
    """Mencari padanan kata yang paling relevan untuk konteks terjemahan."""
    input_words = set(re.findall(r'\w+', input_text.lower()))
    source_key = source_lang.replace(" ", "_")
    best_matches = []
    
    # Pencarian Kata-per-Kata
    for word in input_words:
        matching_rows = []
        for row in dataset:
            row_words = set(re.findall(r'\w+', row.get(source_key, "").lower()))
            if word in row_words:
                matching_rows.append(row)
        
        matching_rows.sort(key=lambda x: len(x.get(source_key, "")))
        
        for match in matching_rows[:2]:
            if match not in best_matches:
                best_matches.append(match)
                
    # Penambahan kalimat konteks
    scored_examples = []
    for row in dataset:
        if row in best_matches: 
            continue
        source_text = row.get(source_key, "")
        row_words = set(re.findall(r'\w+', source_text.lower()))
        match_score = len(input_words.intersection(row_words))
        
        if match_score > 0:
            density_score = match_score / len(row_words)
            scored_examples.append((density_score, row))
            
    scored_examples.sort(key=lambda x: x[0], reverse=True)
    
    for score, row in scored_examples[:5]:
        best_matches.append(row)
        
    return best_matches

def translate_text(input_text, source_lang, target_lang, dataset):
    """Menerjemahkan teks dengan Auto-Retry untuk Limit API."""
    relevant_examples = find_relevant_examples(input_text, source_lang, dataset)
    
    total_target = 20
    num_random_needed = max(0, total_target - len(relevant_examples))
    
    remaining_dataset = [row for row in dataset if row not in relevant_examples]
    random_examples = random.sample(remaining_dataset, min(num_random_needed, len(remaining_dataset)))
    
    final_examples_list = random_examples + relevant_examples
    
    examples_text = ""
    for pair in final_examples_list:
        if source_lang == "Indonesian":
            examples_text += f"* Indonesian: {pair['Indonesian']}\n  Dayak Tonyooi: {pair['Dayak_Tonyooi']}\n\n"
        else:
            examples_text += f"* Dayak Tonyooi: {pair['Dayak_Tonyooi']}\n  Indonesian: {pair['Indonesian']}\n\n"
            
    # AI Prompt (Tetap dalam bahasa Inggris agar AI memahami instruksi dengan maksimal)
    prompt = f"""You are an expert linguist and translator specializing in the Dayak Tonyooi language. 
Your task is to translate the given {source_lang} text into {target_lang}. 

Study the following examples carefully to understand the vocabulary, grammar, and sentence structure:

{examples_text}

Now, translate this exact phrase. Output ONLY the {target_lang} translation, nothing else. Do not include quotes or parentheses unless they are in the original text.

{source_lang}: "{input_text}"
{target_lang}:"""

    # --- RETRY LOGIC ---
    max_retries = 3
    base_wait_time = 4  

    for attempt in range(max_retries):
        try:
            response = client.models.generate_content(
                model='gemma-3-27b-it',
                contents=prompt,
                config=types.GenerateContentConfig(temperature=0.1)
            )
            return response.text.strip()
            
        except Exception as e:
            error_msg = str(e)
            
            if "429" in error_msg or "RESOURCE_EXHAUSTED" in error_msg:
                if attempt < max_retries - 1:
                    wait_time = base_wait_time * (2 ** attempt) 
                    st.toast(f"Batas Akses API. Menjeda selama {wait_time} detik...", icon="⏳")
                    time.sleep(wait_time)
                    continue 
                else:
                    return f"Maaf, server AI sedang sibuk. Silakan coba lagi dalam beberapa menit."
            else:
                return f"Terjadi kesalahan saat menghubungi API: {e}"

# --- 4. Memuat Data ---
csv_file_path = "dayak_dataset.csv"
real_dataset = load_csv_corpus(csv_file_path)

st.divider()

# --- 5. Antarmuka Pengguna (User Interface) ---
direction = st.radio(
    "Pilih Arah Terjemahan:",
    ("Indonesia ke Dayak Tonyooi", "Dayak Tonyooi ke Indonesia")
)

# Menyesuaikan label UI dengan format yang dibutuhkan sistem AI internal
if direction == "Indonesia ke Dayak Tonyooi":
    source_lang, target_lang = "Indonesian", "Dayak Tonyooi"
    ui_source_lang, ui_target_lang = "Indonesia", "Dayak Tonyooi"
else:
    source_lang, target_lang = "Dayak Tonyooi", "Indonesian"
    ui_source_lang, ui_target_lang = "Dayak Tonyooi", "Indonesia"

user_input = st.text_input(f"Masukkan teks Bahasa {ui_source_lang} untuk diterjemahkan:")

if st.button("Terjemahkan"):
    if user_input.strip():
        if not real_dataset:
            st.error("Dataset kosong atau gagal dimuat. Terjemahan tidak dapat dilanjutkan.")
        else:
            with st.spinner("Mencari padanan kata, menyiapkan konteks kalimat, dan menerjemahkan..."):
                translation_result = translate_text(user_input, source_lang, target_lang, real_dataset)
                st.success(f"**{ui_target_lang}:** {translation_result}")
                # --- PENCATATAN REQUEST DIMULAI DI SINI ---
                try:
                    with open("translation_requests.txt", "a", encoding="utf-8") as log_file:
                        # Menyimpan kalimat input dan kalimat output secara rapi
                        log_file.write(f"[{ui_source_lang} -> {ui_target_lang}] Input: {user_input} | Output: {translation_result}\n")
                except Exception as e:
                    st.warning(f"Terjemahan berhasil, tetapi gagal menyimpan log: {e}")
                # --- PENCATATAN REQUEST SELESAI ---
    else:
        st.warning("Harap masukkan teks yang ingin diterjemahkan terlebih dahulu.")

# --- 6. Disclaimer Tengah ---
st.info("⚠️ **Pemberitahuan Penting:**\nJika sistem gagal menerjemahkan karena batas penggunaan API harian telah habis, mohon tunggu dan coba kembali besok.\n Terjemahan dari Tonyooi ke Indonesia lebih sering tidak akurat.")

st.divider()

# --- 7. Bantuan & Kontribusi ---
st.markdown("### 🤝 Bantu Kami Berkembang")
st.write("Menemukan terjemahan yang kurang tepat? Atau ingin menambahkan kosakata baru ke dalam sistem ini? Silakan isi formulir di bawah.")

# GANTI URL DI BAWAH INI dengan tautan 'src' panjang yang Anda dapatkan dari Langkah 1
embed_url = "https://docs.google.com/forms/d/e/1FAIpQLSc-MkB8kqZbV5vcFwn0002IBmNBdawPsIGjwysAKr4G2PZ7_g/viewform?embedded=true"

# Menampilkan Google Form langsung di dalam halaman
components.iframe(embed_url, height=800, scrolling=True)

st.divider()

# --- 8. Informasi Hosting & Logo ---
st.markdown("<h4 style='text-align: center; color: gray;'>Hosted by:</h4>", unsafe_allow_html=True)
st.markdown("<p style='text-align: center; font-weight: bold;'>Laboratorium Fisika Lanjut Fisika UNPAR</p>", unsafe_allow_html=True)

# Menyelaraskan logo ke tengah menggunakan kolom
col1, col2, col3, col4 = st.columns([1, 1.2, 1.2, 1])
with col2:
    st.image("FA-Logo-Berwarna-Unpar.png", width=180)
with col3:
    st.image("logoBluIG.png", width=180)

st.divider()

# --- 9. Daftar Kontributor ---
st.markdown("<p style='text-align: center; font-size: 14px;'>Terima kasih kepada semua pihak yang telah membantu menyempurnakan kamus ini.</p>", unsafe_allow_html=True)

# Membuat tautan di tengah
col_link1, col_link2, col_link3 = st.columns([1, 2, 1])
with col_link2:
    st.link_button("👥 Lihat Daftar Kontributor", "https://docs.google.com/spreadsheets/d/12LlioWh3o9uLzAmW80fS-wVvbEXmVoTUuhdIk-Thl7g/edit?usp=sharing", use_container_width=True)
