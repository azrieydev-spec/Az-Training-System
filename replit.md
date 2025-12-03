# Employee Training Chatbot

## Overview
An AI-powered employee training chatbot web application that uses OpenAI GPT-3.5-turbo to answer training questions based on uploaded company documents.

## Features
- **Chat Interface**: Clean chat interface for employees to ask training questions
- **AI-Powered Responses**: Context-aware responses using uploaded document content
- **Document Management**: Upload and manage PDF, TXT, and DOCX training documents
- **Admin Dashboard**: Analytics including total questions, FAQs, and user statistics
- **User Authentication**: Replit Auth with employee and admin roles
- **Session Management**: Secure session handling with PostgreSQL storage

## Tech Stack
- **Backend**: Python Flask
- **Database**: PostgreSQL (via Replit)
- **Authentication**: Replit Auth (OAuth2)
- **AI**: OpenAI GPT-3.5-turbo
- **Frontend**: Bootstrap 5, Vanilla JavaScript
- **Document Processing**: pdfplumber (PDF), python-docx (DOCX)

## Project Structure
```
├── app.py              # Flask app initialization and database config
├── main.py             # Application entry point
├── models.py           # SQLAlchemy database models
├── routes.py           # Route handlers and API endpoints
├── replit_auth.py      # Replit Auth integration
├── ai_chat.py          # OpenAI integration for chat
├── document_processor.py # Document text extraction
├── templates/          # Jinja2 HTML templates
│   ├── base.html
│   ├── landing.html
│   ├── chat.html
│   ├── documents.html
│   ├── upload.html
│   ├── admin.html
│   ├── profile.html
│   └── error pages (403, 404, 500)
├── static/
│   └── css/style.css
└── uploads/            # Uploaded documents storage
```

## Database Models
- **User**: User accounts with role (employee/admin)
- **OAuth**: OAuth tokens for Replit Auth
- **Document**: Uploaded training documents with extracted text
- **ChatMessage**: User questions and AI responses
- **QuestionAnalytics**: Tracking for frequently asked questions

## User Roles
- **Employee**: Can use chat, view documents, upload documents
- **Admin**: All employee permissions plus admin dashboard, user management, document deletion

## API Endpoints
- `POST /api/chat` - Send chat message and get AI response

## Environment Variables
- `DATABASE_URL` - PostgreSQL connection string (auto-configured)
- `SESSION_SECRET` - Session encryption key (auto-configured)
- `OPENAI_API_KEY` - Required for AI chat functionality

## Running the Application
The application runs on port 5000 with Flask's development server.

## Recent Changes
- December 2024: Initial implementation with all core features
