from docx import Document as DocxDocument

def extract_text_from_docx(file):
    doc = DocxDocument(file)
    text = "\n".join([p.text for p in doc.paragraphs])
    return text