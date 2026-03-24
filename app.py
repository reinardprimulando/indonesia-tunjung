import os
import csv
import streamlit as st
from google import genai

# --- 1. Page Configuration ---
st.set_page_config(page_title="Dayak Tonyooi Translator", page_icon="🌍")
st.title("🌍 Dayak Tonyooi Translator")
st.write("Translate text between Indonesian and Dayak Tonyooi instantly.")

# --- 2. Initialize the Client ---
# Streamlit Cloud will securely pass the API key from its Secrets manager
try:
    client = genai.Client()
except Exception as e:
    st.error("API Key not found. Please configure your secrets.")
    st.stop()

# --- 3. Functions ---
def translate_text(input_text, source_lang, target_lang, translation_memory):
    """Translates text using a dynamic few-shot prompt."""
    examples_text = ""
    for pair in translation_memory:
        if source_lang == "Indonesian":
            examples_text += f"* Indonesian: {pair['Indonesian']}\n  Dayak Tonyooi: {pair['Dayak_Tonyooi']}\n\n"
        else:
            examples_text += f"* Dayak Tonyooi: {pair['Dayak_Tonyooi']}\n  Indonesian: {pair['Indonesian']}\n\n"
        
    prompt = f"""You are an expert linguist and translator specializing in the Dayak Tonyooi language. 
Your task is to translate the given {source_lang} text into {target_lang}. 

Study the following examples carefully to understand the vocabulary, grammar, and sentence structure:

{examples_text}

Now, translate this exact phrase. Output ONLY the {target_lang} translation, nothing else. Do not include quotes or parentheses unless they are in the original text.

{source_lang}: "{input_text}"
{target_lang}:"""

    try:
        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=prompt,
        )
        return response.text.strip()
    except Exception as e:
         return f"Error connecting to Gemini API: {e}"

# We use @st.cache_data so the CSV only loads once, speeding up the app
@st.cache_data 
def load_csv_corpus(file_path):
    """Reads the CSV dataset and converts it into a list of dictionaries."""
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
        st.error(f"Error: Could not find the dataset file {file_path}")
    return dataset

# --- 4. Load Data ---
csv_file_path = "dayak_dataset.csv"
real_dataset = load_csv_corpus(csv_file_path)
examples_to_use = real_dataset[:100] if real_dataset else []

st.divider()

# --- 5. User Interface ---
# Replace the old menu with a nice radio button
direction = st.radio(
    "Select Translation Direction:",
    ("Indonesian to Dayak Tonyooi", "Dayak Tonyooi to Indonesian")
)

if direction == "Indonesian to Dayak Tonyooi":
    source_lang, target_lang = "Indonesian", "Dayak Tonyooi"
else:
    source_lang, target_lang = "Dayak Tonyooi", "Indonesian"

# Replace the 'input()' with a text input box
user_input = st.text_input(f"Enter {source_lang} text to translate:")

# Create a translate button
if st.button("Translate"):
    if user_input.strip():
        # Show a loading spinner while waiting for the API
        with st.spinner("Translating..."):
            translation_result = translate_text(user_input, source_lang, target_lang, examples_to_use)
            st.success(f"**{target_lang}:** {translation_result}")
    else:
        st.warning("Please enter some text to translate first.")