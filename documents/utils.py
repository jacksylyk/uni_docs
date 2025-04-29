from django.conf import settings
from docx import Document as DocxDocument
from openai import OpenAI

def extract_text_from_docx(file):
    doc = DocxDocument(file)
    text = "\n".join([p.text for p in doc.paragraphs])
    return text

from difflib import SequenceMatcher

def get_word_diff(a, b):
    matcher = SequenceMatcher(None, a.split(), b.split())
    result = []

    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        if tag == 'equal':
            result.extend(a.split()[i1:i2])
        elif tag == 'delete':
            result.extend([f'<span class="removed">{w}</span>' for w in a.split()[i1:i2]])
        elif tag == 'insert':
            result.extend([f'<span class="added">{w}</span>' for w in b.split()[j1:j2]])
        elif tag == 'replace':
            result.extend([f'<span class="removed">{w}</span>' for w in a.split()[i1:i2]])
            result.extend([f'<span class="added">{w}</span>' for w in b.split()[j1:j2]])

    return ' '.join(result)

def classify_document_with_openai(content, categories):
    category_list = "\n".join([category.name for category in categories])
    openai_client = OpenAI(api_key=settings.OPENAI_API_KEY)
    response = openai_client.responses.create(
        model="gpt-3.5-turbo",
        instructions=f"Классифицируй документ по следующему тексту и существующим категориям:\n{category_list}. Ответь только имя категории точь в точь такую же как в списке",
        input=f"Текст документа:\n{content}\nКакая категория?",
    )

    category = response.output_text
    return category

from docx2pdf import convert
import os

def convert_docx_to_pdf_windows(input_path: str, output_dir: str) -> str:
    convert(input_path, output_dir)
    filename = os.path.basename(input_path)
    pdf_filename = os.path.splitext(filename)[0] + ".pdf"
    return os.path.join(output_dir, pdf_filename)

def get_diff_description(prev_text: str, new_text: str) -> str:
    prompt = f"""Проанализируй два текста документа и кратко опиши, что было изменено:
                
                --- Предыдущая версия ---
                {prev_text}
                
                --- Новая версия ---
                {new_text}
                
                Опиши изменения на русском языке, кратко и по делу:"""
    openai_client = OpenAI(api_key=settings.OPENAI_API_KEY)
    response = openai_client.chat.completions.create(
        model="gpt-4",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.2
    )

    return response.choices[0].message.content.strip()