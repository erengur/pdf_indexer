import streamlit as st
import PyPDF2
import pdfplumber
import re
import pandas as pd
from io import StringIO

# Başlık
st.title("PDF Metin ve Tablo Çıkarıcı")

# PDF dosyası yükleme
uploaded_file = st.file_uploader("Lütfen bir PDF dosyası yükleyin", type="pdf")

# Metin ve tabloları kaydetme fonksiyonu
def save_text_and_tables(relevant_sentences, tables, summary):
    output = StringIO()
    output.write("=== Çıkarılan İlgili Metinler ===\n")
    for sentence in relevant_sentences:
        output.write(sentence + '\n')
    if tables:
        output.write("\n=== Çıkarılan Tablolar ===\n")
        for idx, table in enumerate(tables):
            output.write(f"\nTablo {idx+1}:\n")
            output.write(table.to_string(index=False) + '\n')
    output.write("\n=== Özet ===\n")
    output.write(summary if summary else "Özet yok.")
    return output.getvalue()

# Eğer bir dosya yüklendiyse işlemlere başla
if uploaded_file is not None:
    # PDF'den metin ve tabloları çıkarın
    def pdf_to_text_and_tables(pdf_file):
        try:
            # Metin çıkarma işlemi
            reader = PyPDF2.PdfReader(pdf_file)
            text = ''
            for page in reader.pages:
                page_text = page.extract_text()
                if page_text:
                    text += page_text + '\n'
            st.success("PDF metin çıkarma işlemi tamamlandı.")

            # Tablo çıkarma işlemi
            st.info("PDF'den tablolar çıkarılıyor...")
            tables = []
            with pdfplumber.open(pdf_file) as pdf:
                for page_num, page in enumerate(pdf.pages, start=1):
                    page_tables = page.extract_tables()
                    if page_tables:
                        for table in page_tables:
                            if table and len(table) > 1:
                                df = pd.DataFrame(table[1:], columns=table[0])
                                df.columns = clean_column_names(df.columns)
                                df.insert(0, 'Sayfa Numarası', page_num)
                                tables.append(df)
            st.success(f"PDF'den {len(tables)} tablo çıkarıldı.")
            return text, tables
        except Exception as e:
            st.error(f"PDF çıkarma sırasında hata oluştu: {e}")
            return None, None

    # Sütun isimlerini temizleyen fonksiyon
    def clean_column_names(columns):
        new_columns = []
        column_count = {}
        for col in columns:
            if col is None or col == '':
                col = 'Unnamed'
            col = str(col).strip()
            # Tekrarlanan sütun isimlerini sayıyla benzersiz hale getir
            if col in column_count:
                column_count[col] += 1
                col = f"{col}_{column_count[col]}"
            else:
                column_count[col] = 1
            new_columns.append(col)
        return new_columns

    # Custom Turkish sentence tokenizer
    def turkish_sentence_tokenizer(text):
        abbreviations = [
            'Dr.', 'Prof.', 'Doç.', 'Av.', 'Sn.', 'vs.', 'vb.', 'bkz.', 's.', 'No.'
        ]
        placeholder = '__ABBR_PERIOD__'
        for abbr in abbreviations:
            text = text.replace(abbr, abbr.replace('.', placeholder))
        sentences = re.split(r'(?<=[.!?])\s+', text)
        sentences = [sentence.replace(placeholder, '.') for sentence in sentences]
        return sentences

    # Extract relevant sections
    def extract_relevant_sections(text):
        swot_keywords = [
            'SWOT analysis', 'Strengths', 'Weaknesses', 'Opportunities', 'Threats',
            'SWOT analizi', 'Güçlü Yönler', 'Zayıf Yönler', 'Fırsatlar', 'Tehditler'
        ]
        finance_keywords = [
            'income', 'expense', 'profit', 'revenue', 'cost', 'loss',
            'gelir', 'gider', 'kâr', 'maliyet', 'zarar', 'hasılat', 'bütçe', 'mali', 'finans'
        ]
        keywords = swot_keywords + finance_keywords
        escaped_keywords = [re.escape(k) for k in keywords]
        pattern = re.compile(r'\b(' + '|'.join(escaped_keywords) + r')\b', re.IGNORECASE)
        sentences = turkish_sentence_tokenizer(text)
        relevant_sentences = [sentence.strip() for sentence in sentences if pattern.search(sentence)]
        return relevant_sentences

    # Summarize text
    def summarize_text_with_textrank(text, sentences_count=5):
        try:
            from sumy.parsers.plaintext import PlaintextParser
            from sumy.summarizers.text_rank import TextRankSummarizer

            class CustomTurkishTokenizer:
                def to_sentences(self, text):
                    return turkish_sentence_tokenizer(text)

                def to_words(self, sentence):
                    words = re.findall(r'\b\w+\b', sentence, flags=re.UNICODE)
                    return words

            parser = PlaintextParser.from_string(text, CustomTurkishTokenizer())
            summarizer = TextRankSummarizer()
            summary_sentences = summarizer(parser.document, sentences_count)
            summary = ' '.join(str(sentence).strip() for sentence in summary_sentences)
            st.success("Özetleme işlemi tamamlandı.")
            return summary
        except Exception as e:
            st.error(f"Özetleme sırasında hata oluştu: {e}")
            return None

    # Metin ve tabloları çıkar
    pdf_text, pdf_tables = pdf_to_text_and_tables(uploaded_file)

    if pdf_text:
        # İlgili bölümleri çıkar
        relevant_sentences = extract_relevant_sections(pdf_text)

        # Tabloları ve metni kaydet
        relevant_text = ' '.join(relevant_sentences)
        summary = summarize_text_with_textrank(relevant_text, sentences_count=5)
        output_text = save_text_and_tables(relevant_sentences, pdf_tables, summary)

        # İndirme butonunu en üste ekleyelim
        st.download_button(
            label="Çıktıyı İndir (output.txt)",
            data=output_text,
            file_name="output.txt",
            mime="text/plain"
        )

        # İlgili cümleleri göster
        st.write(f"{len(relevant_sentences)} ilgili cümle çıkarıldı.")
        if relevant_sentences:
            st.subheader("Çıkarılan İlgili Metinler")
            for sentence in relevant_sentences:
                st.write("- " + sentence)

        # Tabloları göster
        if pdf_tables:
            st.subheader("Çıkarılan Tablolar")
            for idx, table in enumerate(pdf_tables):
                if not table.empty:
                    st.write(f"**Tablo {idx+1}**")
                    st.dataframe(table.reset_index(drop=True))
    else:
        st.error("PDF'den metin çıkarılamadı.")
