import streamlit as st
import pdfplumber
import pandas as pd
import io
import re
import os

# Belirlenen Prompt
PROMPT = """
Using the most recent annual activity report of the client, your task is to conduct a comprehensive analysis that will provide key insights into the client's operations and strategies. This analysis should cover the following areas:

SWOT Analysis: Identify and elaborate on the company's strengths, weaknesses, opportunities, and threats. These insights will not be directly stated within the document, so you will need to infer this information from the details provided in the report.
Employee Analysis: Extract any information related to the number of employees in the company. This could include the total number of employees, the number of employees in different departments, changes in employee numbers over the year, etc.
Financial Analysis: Gather all the numbers related to the company's revenues, profits, costs, and losses. Using this financial information, perform a Profit & Loss (P&L) analysis. This analysis should provide an understanding of the company's financial health and profitability.
Technology & AI Innovations: Highlight any significant technological and artificial intelligence innovations or initiatives the company has undertaken in the past year. Discuss the impact of these innovations on the company's operations and its position in the market.

Your analysis should be detailed, thorough, and actionable. The goal is to provide insights that will enhance our employees' understanding of the client's business, including their strategies, structure, operations, and financial standing. Your report should be comprehensive enough to provide a holistic view of the client's business and should be presented in a manner that encourages strategic thinking and decision-making.
"""

def extract_text_and_tables(pdf_file):
    """
    PDF dosyasından sayfa bazında metin ve tabloları çıkarır.
    Her sayfa için metin satırları ve tablolar listelenir.
    """
    pages_content = []
    try:
        with pdfplumber.open(pdf_file) as pdf:
            for page_num, page in enumerate(pdf.pages, start=1):
                # Sayfadaki metni çıkar
                page_text = page.extract_text()
                lines = page_text.split('\n') if page_text else []

                # Sayfadaki tabloları çıkar
                page_tables = page.extract_tables()

                pages_content.append({
                    'page_num': page_num,
                    'lines': lines,
                    'tables': page_tables
                })
        return pages_content
    except Exception as e:
        st.error(f"PDF işlenirken bir hata oluştu: {e}")
        return None

def make_unique_headers(headers):
    """
    Sütun başlıklarını benzersiz hale getirir.
    Tekrarlanan başlıkların sonuna numara ekler.
    Eksik başlıklar için 'Column_X' şeklinde isim verir.
    """
    unique_headers = []
    header_count = {}
    for idx, header in enumerate(headers):
        if not header or header.strip() == '':
            unique_header = f"Column_{idx+1}"
        else:
            header = header.strip()
            if header in header_count:
                header_count[header] += 1
                unique_header = f"{header}_{header_count[header]}"
            else:
                header_count[header] = 1
                unique_header = header
        unique_headers.append(unique_header)
    return unique_headers

def process_pages(pages_content):
    """
    Sayfa bazında çıkarılan metin ve tabloları işler.
    Tabloların başlıklarını belirler ve DataFrame oluşturur.
    """
    all_table_info = []
    processed_data = {}

    for page in pages_content:
        page_num = page['page_num']
        lines = page['lines']
        tables = page['tables']

        # Sayfadaki başlıkları tespit et (tümü büyük harflerle yazılmış satırlar)
        headings = [line.strip() for line in lines if line.isupper() and len(line.split()) < 10]

        for table in tables:
            if len(table) < 2:
                continue  # En az başlık ve bir veri satırı olmalı

            # Tablonun başlığını belirle
            # Basit bir yaklaşım: sayfadaki son bulunan başlık
            if headings:
                table_title = headings[-1]
            else:
                table_title = f"Sayfa {page_num} Tablo"

            # Sütun başlıklarını benzersiz hale getir
            headers = make_unique_headers(table[0])
            data_rows = table[1:]
            df = pd.DataFrame(data_rows, columns=headers)

            all_table_info.append({
                'title': table_title,
                'df': df,
                'page_num': page_num
            })

            # İşlenen verileri topla
            for column in df.columns:
                column_data = df[column].dropna().astype(str).tolist()
                if column in processed_data:
                    processed_data[column] += ", " + ", ".join(column_data)
                else:
                    processed_data[column] = ", ".join(column_data)

    return all_table_info, processed_data

def process_text(text):
    """
    Metni işleyerek sadece belirlenen prompt ile ilgili olan kısımları çeker.
    Yalnızca SWOT, Employee, Financial ve Technology & AI bölümleriyle ilgili bilgileri alır.
    """
    processed_data = {}
    lines = text.split('\n')
    current_section = None

    # Belirlenen bölümlerin başlık kalıpları
    sections = {
        'SWOT Analysis': r'swot analysis',
        'Employee Analysis': r'employee analysis|employees?',
        'Financial Analysis': r'financial analysis|profit & loss|p&l analysis',
        'Technology & AI Innovations': r'technology & ai innovations|technology and ai|ai innovations'
    }

    # Bölüm tespiti için regex derleme
    section_patterns = {key: re.compile(pattern, re.IGNORECASE) for key, pattern in sections.items()}

    for line in lines:
        line = line.strip()
        if not line:
            continue

        # Bölüm başlıklarını tespit et
        for section, pattern in section_patterns.items():
            if pattern.search(line):
                current_section = section
                break
        else:
            # Eğer mevcut bir bölüm varsa, o bölüme ait veriyi toplar
            if current_section:
                # Sayı veya yüzde içeren satırları kontrol et
                numbers = re.findall(r'\d+%?', line)
                if numbers and all(is_number(num) for num in numbers):
                    for number in numbers:
                        if current_section in processed_data:
                            processed_data[current_section] += ", " + number
                        else:
                            processed_data[current_section] = number
                else:
                    # Etiketler ve diğer metin bilgilerini de işleyebilirsiniz
                    pass  # Bu örnekte sadece sayılar alınıyor

    return processed_data

def is_number(s):
    """
    Bir string'in sayı veya yüzde içerip içermediğini kontrol eder.
    """
    return re.match(r'^-?\d+(\.\d+)?%?$', s) is not None

def create_txt_document(prompt, text, tables, processed_data):
    """
    Çıkarılan metin, tablolar ve işlenen verilerle bir TXT belgesi oluşturur.
    """
    txt_content = []

    # Belgenin başlığı ve prompt
    txt_content.append("Analiz İçin Hazır Prompt")
    txt_content.append("========================\n")
    txt_content.append(prompt)
    txt_content.append("\n\n")

    # Çıkarılan Metin (Sadece ilgili kısımlar)
    if text:
        txt_content.append("Çıkarılan Metin")
        txt_content.append("----------------")
        txt_content.append(text + "\n\n")

    # Çıkarılan Tablolar (Sadece ilgili tablolar)
    if tables:
        txt_content.append("Çıkarılan Tablolar")
        txt_content.append("-------------------")
        for table_info in tables:
            title = table_info['title']
            df = table_info['df']
            txt_content.append(f"{title}")
            txt_content.append(df.to_string(index=False))
            txt_content.append("")  # Boş satır
        txt_content.append("\n")

    # İşlenen Veriler (Sadece ilgili alanlar)
    if processed_data:
        txt_content.append("İşlenen Veriler")
        txt_content.append("----------------")
        for key, value in processed_data.items():
            txt_content.append(f"{key}: {value}")
        txt_content.append("")  # Boş satır

    # Tüm içerikleri birleştir
    full_txt = "\n".join(txt_content)

    # Bellek içi bir dosya oluştur
    txt_io = io.StringIO()
    txt_io.write(full_txt)
    txt_io.seek(0)

    return txt_io

def main():
    st.title("PDF'den Metin ve Veri Çıkarıcı")
    st.write("Bu uygulama, yüklediğiniz PDF dosyasının metin ve veri tablolarını çıkarır, belirlediğiniz prompt ile uyumlu hale getirir ve düzenlenmiş bir TXT belgesi olarak indirmenizi sağlar.")

    uploaded_file = st.file_uploader("Bir PDF dosyası yükleyin", type=["pdf"])

    if uploaded_file is not None:
        st.success("Dosya başarıyla yüklendi!")
        with st.spinner("Metin ve tablolar çıkarılıyor..."):
            pages_content = extract_text_and_tables(uploaded_file)
            if not pages_content:
                st.error("PDF'den veri çıkarılamadı.")
                st.stop()

            # Metni çıkar
            full_text = "\n".join(["\n".join(page['lines']) for page in pages_content if page['lines']])

            # Tabloları işle
            all_table_info, table_processed_data = process_pages(pages_content)

            # Metinden işlenen verileri al
            text_data = process_text(full_text)
            table_processed_data.update(text_data)

        # Dosya adını al ve .txt uzantısına çevir
        original_filename = uploaded_file.name
        base_name = os.path.splitext(original_filename)[0]
        txt_filename = f"{base_name}.txt"

        # İndirme Butonunu Metin Alanının Üstüne Taşı
        if all_table_info or table_processed_data or full_text:
            # TXT belgesini oluştur
            txt_file = create_txt_document(PROMPT, full_text, all_table_info, table_processed_data)

            # TXT belgesini indirmek için bir buton
            st.download_button(
                label="TXT Belgesini İndir",
                data=txt_file.getvalue(),
                file_name=txt_filename,  # Dinamik dosya adı kullanılıyor
                mime="text/plain"
            )

        # Ekranda Çıkarılan Metin
        if full_text:
            st.subheader("Çıkarılan Metin")
            st.text_area("Metin İçeriği", full_text, height=300)

        # Ekranda Çıkarılan Tablolar
        if all_table_info:
            st.subheader("Çıkarılan Tablolar")
            for table_info in all_table_info:
                st.markdown(f"**{table_info['title']}**")
                st.dataframe(table_info['df'])

        # İşlenen Veriler
        if table_processed_data:
            st.subheader("İşlenen Veriler")
            for key, value in table_processed_data.items():
                st.write(f"**{key}:** {value}")

if __name__ == "__main__":
    main()  
