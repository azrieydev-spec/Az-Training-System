import os
import logging
from openai import OpenAI

logger = logging.getLogger(__name__)

# Groq API configuration
# Using llama-3.1-70b-versatile model via Groq API
GROQ_MODEL = "llama-3.1-70b-versatile"
GROQ_BASE_URL = "https://api.groq.com/openai/v1"

GROQ_API_KEY = os.environ.get("GROQ_API_KEY")

# Initialize Groq client (using OpenAI SDK with Groq endpoint)
client = None
if GROQ_API_KEY:
    client = OpenAI(
        api_key=GROQ_API_KEY,
        base_url=GROQ_BASE_URL
    )


def get_document_context(documents):
    """Build context from uploaded documents."""
    context = ""
    for doc in documents:
        if doc.content:
            context += f"\n--- Document: {doc.original_filename} ---\n"
            context += doc.content[:8000]  # Limit each document to 8000 chars
            context += "\n"
    return context


def generate_response(user_message, documents, chat_history=None):
    """Generate an AI response based on user message and document context."""
    if not client:
        return "I'm sorry, but the AI service is not configured. Please contact an administrator to set up the Groq API key."
    
    try:
        # Build document context
        doc_context = get_document_context(documents)
        
        # Build system message
        system_message = """You are a helpful employee training assistant for a company. 
Your role is to answer questions about company policies, procedures, and training materials.
Be professional, helpful, and accurate in your responses.
If you don't know the answer or if the information isn't in the provided documents, 
say so honestly and suggest the employee contact HR or their manager for more information.

"""
        
        if doc_context:
            system_message += f"""Here are the company training documents you can reference:

{doc_context}

Use the information from these documents to answer employee questions accurately.
Always cite which document your information comes from when possible."""
        else:
            system_message += """Note: No training documents have been uploaded yet. 
Please let the employee know that training documents need to be uploaded by an administrator 
before you can provide specific company information."""

        # Build messages
        messages = [{"role": "system", "content": system_message}]
        
        # Add recent chat history for context (last 5 exchanges)
        if chat_history:
            for msg in chat_history[-10:]:  # Last 10 messages (5 exchanges)
                messages.append({"role": "user", "content": msg.message})
                if msg.response:
                    messages.append({"role": "assistant", "content": msg.response})
        
        # Add current user message
        messages.append({"role": "user", "content": user_message})
        
        # Generate response using Groq API with llama-3.1-70b-versatile
        response = client.chat.completions.create(
            model=GROQ_MODEL,
            messages=messages,
            max_tokens=1000,
            temperature=0.7
        )
        
        return response.choices[0].message.content
        
    except Exception as e:
        logger.error(f"Error generating AI response: {e}")
        return f"I'm sorry, I encountered an error while processing your question. Please try again later. Error: {str(e)}"


def normalize_question(question):
    """Normalize a question for analytics grouping."""
    # Simple normalization: lowercase, remove extra spaces, limit length
    normalized = ' '.join(question.lower().split())
    return normalized[:500]
