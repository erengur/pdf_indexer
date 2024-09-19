import streamlit as st
import PyPDF2
from io import StringIO, BytesIO
import re
import pandas as pd

# Başlık
st.title("PDF Metin Çıkarıcı ve Cümle İndeksleyici (Excel Formatında)")

# PDF dosyası yükleme
uploaded_file = st.file_uploader("Lütfen bir PDF dosyası yükleyin", type="pdf")

# Metni kaydetme fonksiyonu
def save_text(text):
    output = StringIO()
    output.write("=== Çıkarılan Metin ===\n\n")
    output.write(text)
    return output.getvalue()

# Regex tabanlı cümle bölme fonksiyonu
def split_into_sentences(text):
    # Cümle sonu işaretlerine göre bölme
    sentence_endings = re.compile(r'(?<=[.!?])\s+')
    sentences = sentence_endings.split(text)
    return sentences

# Ana işlem akışı
if uploaded_file is not None:
    try:
        # PDF'den metin çıkarma işlemi
        reader = PyPDF2.PdfReader(uploaded_file)
        text = ''
        for page_num, page in enumerate(reader.pages, start=1):
            page_text = page.extract_text()
            if page_text:
                text += page_text + '\n'
        st.success("PDF metin çıkarma işlemi tamamlandı.")

        if text:
            # Çıkarılan metni cümle cümle indeksleme
            sentences = split_into_sentences(text)
            indexed_sentences = [{"Index": i+1, "Sentence": sentence} for i, sentence in enumerate(sentences)]
            
            # Veri çerçevesine dönüştürme
            df = pd.DataFrame(indexed_sentences)
            
            # İndekslenmiş cümleleri Excel olarak indirilebilir hale getirme
            excel_buffer = BytesIO()
            with pd.ExcelWriter(excel_buffer, engine='openpyxl') as writer:
                df.to_excel(writer, index=False, sheet_name='Sentences')
            excel_bytes = excel_buffer.getvalue()

            # Metni kaydet
            output_text = save_text(text)

            # İndirme butonlarını üstte gösterme (İki sütun halinde)
            st.subheader("Çıkarılan Metin ve İndekslenmiş Cümleler")

            col1, col2 = st.columns(2)
            with col1:
                st.download_button(
                    label="Çıktıyı İndir (output.txt)",
                    data=output_text,
                    file_name="output.txt",
                    mime="text/plain"
                )
            with col2:
                st.download_button(
                    label="İndekslenmiş Cümleleri İndir (sentences.xlsx)",
                    data=excel_bytes,
                    file_name="sentences.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )

            # Çıkarılan metni göster (Madde Madde İndekslenmiş)
            st.subheader("Çıkarılan Metin")
            indexed_text = '\n'.join([f"{i}. {sentence}" for i, sentence in enumerate(sentences, start=1)])
            st.markdown(indexed_text)

            # İndekslenmiş cümleleri gösterme
            st.subheader("İndekslenmiş Cümleler")
            st.dataframe(df, height=400)
            
        else:
            st.warning("PDF dosyasında çıkarılacak metin bulunamadı.")

    except Exception as e:
        st.error(f"PDF işleme sırasında hata oluştu: {e}")
else:
    st.info("Lütfen bir PDF dosyası yükleyin.")
