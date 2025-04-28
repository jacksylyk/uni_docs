from docx import Document as DocxDocument

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

# import openai
#
# openai.api_key = 'your-openai-api-key'
#
# def summarize_document(text):
#     response = openai.Completion.create(
#         model="text-davinci-003",
#         prompt="Summarize the following document: " + text,
#         max_tokens=200
#     )
#     return response.choices[0].text.strip()