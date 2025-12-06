import os
import uuid
from flask import render_template, request, redirect, url_for, jsonify, session, flash
from flask_login import current_user
from werkzeug.utils import secure_filename

from app import app, db
from replit_auth import require_login, require_admin, make_replit_blueprint
from models import User, Document, ChatMessage, QuestionAnalytics
from document_processor import extract_text, get_file_extension, is_allowed_file
from ai_chat import generate_response, normalize_question

# Register auth blueprint
app.register_blueprint(make_replit_blueprint(), url_prefix="/auth")

# Make session permanent
@app.before_request
def make_session_permanent():
    session.permanent = True

# Add cache control headers
@app.after_request
def add_header(response):
    response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '0'
    return response


@app.route('/')
def index():
    """Landing page / Home page based on auth status."""
    if current_user.is_authenticated:
        return redirect(url_for('chat'))
    return render_template('landing.html')


@app.route('/chat')
@require_login
def chat():
    """Chat interface for employees."""
    # Get user's chat history
    messages = ChatMessage.query.filter_by(user_id=current_user.id).order_by(ChatMessage.created_at.desc()).limit(50).all()
    messages = list(reversed(messages))  # Show oldest first
    return render_template('chat.html', messages=messages, user=current_user)


@app.route('/api/chat', methods=['POST'])
@require_login
def api_chat():
    """API endpoint for chat messages."""
    data = request.get_json()
    user_message = data.get('message', '').strip()
    
    if not user_message:
        return jsonify({'error': 'Message is required'}), 400
    
    # Get all documents for context
    documents = Document.query.all()
    
    # Get user's recent chat history
    chat_history = ChatMessage.query.filter_by(user_id=current_user.id).order_by(ChatMessage.created_at.desc()).limit(10).all()
    chat_history = list(reversed(chat_history))
    
    # Generate AI response
    ai_response = generate_response(user_message, documents, chat_history)
    
    # Save the message and response
    chat_msg = ChatMessage(
        user_id=current_user.id,
        message=user_message,
        response=ai_response
    )
    db.session.add(chat_msg)
    
    # Track question for analytics
    normalized = normalize_question(user_message)
    analytics = QuestionAnalytics.query.filter_by(normalized_question=normalized).first()
    if analytics:
        analytics.count += 1
    else:
        analytics = QuestionAnalytics(
            question_text=user_message,
            normalized_question=normalized
        )
        db.session.add(analytics)
    
    db.session.commit()
    
    return jsonify({
        'response': ai_response,
        'message_id': chat_msg.id
    })


@app.route('/documents')
@require_login
def documents():
    """Document management page."""
    docs = Document.query.order_by(Document.created_at.desc()).all()
    return render_template('documents.html', documents=docs, user=current_user)


@app.route('/upload', methods=['GET', 'POST'])
@require_admin
def upload():
    """Document upload page."""
    if request.method == 'POST':
        if 'file' not in request.files:
            flash('No file selected', 'error')
            return redirect(request.url)
        
        file = request.files['file']
        
        if file.filename == '':
            flash('No file selected', 'error')
            return redirect(request.url)
        
        if not is_allowed_file(file.filename):
            flash('File type not allowed. Please upload PDF, TXT, or DOCX files.', 'error')
            return redirect(request.url)
        
        # Secure the filename and create unique name
        original_filename = secure_filename(file.filename)
        file_ext = get_file_extension(original_filename)
        unique_filename = f"{uuid.uuid4().hex}.{file_ext}"
        
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], unique_filename)
        file.save(file_path)
        
        # Get file size
        file_size = os.path.getsize(file_path)
        
        # Extract text from document
        content = extract_text(file_path, file_ext)
        
        # Save to database
        doc = Document(
            filename=unique_filename,
            original_filename=original_filename,
            file_type=file_ext,
            content=content,
            file_size=file_size,
            uploaded_by=current_user.id
        )
        db.session.add(doc)
        db.session.commit()
        
        flash(f'Document "{original_filename}" uploaded successfully!', 'success')
        return redirect(url_for('documents'))
    
    return render_template('upload.html', user=current_user)


@app.route('/documents/<int:doc_id>/delete', methods=['POST'])
@require_admin
def delete_document(doc_id):
    """Delete a document (admin only)."""
    doc = Document.query.get_or_404(doc_id)
    
    # Delete file from filesystem
    file_path = os.path.join(app.config['UPLOAD_FOLDER'], doc.filename)
    if os.path.exists(file_path):
        os.remove(file_path)
    
    db.session.delete(doc)
    db.session.commit()
    
    flash(f'Document "{doc.original_filename}" deleted.', 'success')
    return redirect(url_for('admin_dashboard'))


@app.route('/admin')
@require_admin
def admin_dashboard():
    """Admin dashboard with analytics."""
    # Total questions asked
    total_questions = ChatMessage.query.count()
    
    # Total unique users who asked questions
    active_users = db.session.query(ChatMessage.user_id).distinct().count()
    
    # Total documents
    total_documents = Document.query.count()
    
    # Most frequently asked questions
    top_questions = QuestionAnalytics.query.order_by(QuestionAnalytics.count.desc()).limit(10).all()
    
    # Recent questions
    recent_questions = ChatMessage.query.order_by(ChatMessage.created_at.desc()).limit(20).all()
    
    # All documents
    documents = Document.query.order_by(Document.created_at.desc()).all()
    
    # All users
    users = User.query.order_by(User.created_at.desc()).all()
    
    # User statistics
    user_stats = db.session.query(
        User.id,
        User.first_name,
        User.last_name,
        User.email,
        db.func.count(ChatMessage.id).label('question_count')
    ).outerjoin(ChatMessage).group_by(User.id).order_by(db.func.count(ChatMessage.id).desc()).all()
    
    return render_template('admin.html',
                         user=current_user,
                         total_questions=total_questions,
                         active_users=active_users,
                         total_documents=total_documents,
                         top_questions=top_questions,
                         recent_questions=recent_questions,
                         documents=documents,
                         users=users,
                         user_stats=user_stats)


@app.route('/admin/users/<user_id>/toggle-admin', methods=['POST'])
@require_admin
def toggle_admin(user_id):
    """Toggle admin status for a user."""
    user = User.query.get_or_404(user_id)
    
    # Prevent removing admin from yourself
    if user.id == current_user.id:
        flash('You cannot change your own admin status.', 'error')
        return redirect(url_for('admin_dashboard'))
    
    # Prevent removing admin from azrieydev@gmail.com
    if user.email == 'azrieydev@gmail.com':
        flash('Cannot change admin status of the primary admin account.', 'error')
        return redirect(url_for('admin_dashboard'))
    
    user.role = 'employee' if user.is_admin() else 'admin'
    db.session.commit()
    
    flash(f'User {user.first_name or user.email} is now {"an admin" if user.is_admin() else "an employee"}.', 'success')
    return redirect(url_for('admin_dashboard'))


@app.route('/users')
@require_admin
def users_management():
    """User management page for admins."""
    users = User.query.order_by(User.created_at.desc()).all()
    
    # User statistics
    user_stats = db.session.query(
        User.id,
        User.first_name,
        User.last_name,
        User.email,
        User.role,
        User.created_at,
        db.func.count(ChatMessage.id).label('question_count')
    ).outerjoin(ChatMessage).group_by(User.id).order_by(User.created_at.desc()).all()
    
    return render_template('users.html', users=users, user_stats=user_stats, user=current_user)


@app.route('/profile')
@require_login
def profile():
    """User profile page."""
    message_count = ChatMessage.query.filter_by(user_id=current_user.id).count()
    return render_template('profile.html', user=current_user, message_count=message_count)


# Error handlers
@app.errorhandler(404)
def not_found_error(error):
    return render_template('404.html'), 404


@app.errorhandler(403)
def forbidden_error(error):
    return render_template('403.html'), 403


@app.errorhandler(500)
def internal_error(error):
    db.session.rollback()
    return render_template('500.html'), 500
