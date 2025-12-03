import os
import logging
from io import BytesIO

logger = logging.getLogger(__name__)

def extract_text_from_txt(file_path):
    """Extract text from a TXT file."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return f.read()
    except UnicodeDecodeError:
        with open(file_path, 'r', encoding='latin-1') as f:
            return f.read()


def extract_text_from_pdf(file_path):
    """Extract text from a PDF file using pdfplumber."""
    try:
        import pdfplumber
        text = ""
        with pdfplumber.open(file_path) as pdf:
            for page in pdf.pages:
                page_text = page.extract_text()
                if page_text:
                    text += page_text + "\n"
        return text.strip()
    except Exception as e:
        logger.error(f"Error extracting text from PDF: {e}")
        return None


def extract_text_from_docx(file_path):
    """Extract text from a DOCX file."""
    try:
        from docx import Document
        doc = Document(file_path)
        text = ""
        for paragraph in doc.paragraphs:
            text += paragraph.text + "\n"
        return text.strip()
    except Exception as e:
        logger.error(f"Error extracting text from DOCX: {e}")
        return None


def extract_text(file_path, file_type):
    """Extract text from a document based on its type."""
    file_type = file_type.lower()
    
    if file_type == 'txt':
        return extract_text_from_txt(file_path)
    elif file_type == 'pdf':
        return extract_text_from_pdf(file_path)
    elif file_type == 'docx':
        return extract_text_from_docx(file_path)
    else:
        logger.warning(f"Unsupported file type: {file_type}")
        return None


def get_file_extension(filename):
    """Get the file extension from a filename."""
    return filename.rsplit('.', 1)[-1].lower() if '.' in filename else ''


def is_allowed_file(filename, allowed_extensions=None):
    """Check if the file has an allowed extension."""
    if allowed_extensions is None:
        allowed_extensions = {'pdf', 'txt', 'docx'}
    return get_file_extension(filename) in allowed_extensions
