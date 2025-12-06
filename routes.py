
import os
import uuid
from flask import render_template, request, redirect, url_for, jsonify, session, flash
from flask_login import current_user, login_user, logout_user
from werkzeug.utils import secure_filename

from app import app, db
from auth import require_login, require_admin
from models import User, Document, ChatMessage, QuestionAnalytics
from document_processor import extract_text, get_file_extension, is_allowed_file
from ai_chat import generate_response, normalize_question


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


@app.route('/register', methods=['GET', 'POST'])
def register():
    """User registration page."""
    if current_user.is_authenticated:
        return redirect(url_for('chat'))
    
    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')
        confirm_password = request.form.get('confirm_password', '')
        
        # Validation
        if not email or not password:
            flash('Email and password are required.', 'error')
            return redirect(url_for('register'))
        
        if len(password) < 8:
            flash('Password must be at least 8 characters long.', 'error')
            return redirect(url_for('register'))
        
        if password != confirm_password:
            flash('Passwords do not match.', 'error')
            return redirect(url_for('register'))
        
        # Check if user already exists
        if User.query.filter_by(email=email).first():
            flash('Email already registered. Please log in.', 'error')
            return redirect(url_for('login'))
        
        # Create new user
        user = User(email=email)
        user.set_password(password)
        
        # Set admin role for specific email
        if email == 'azrieydev@gmail.com':
            user.role = 'admin'
        
        db.session.add(user)
        db.session.commit()
        
        flash('Registration successful! Please log in.', 'success')
        return redirect(url_for('login'))
    
    return render_template('register.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    """User login page."""
    if current_user.is_authenticated:
        return redirect(url_for('chat'))
    
    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')
        
        if not email or not password:
            flash('Email and password are required.', 'error')
            return redirect(url_for('login'))
        
        user = User.query.filter_by(email=email).first()
        
        if user and user.check_password(password):
            login_user(user)
            
            # Redirect to next page or chat
            next_page = request.args.get('next')
            if next_page:
                return redirect(next_page)
            return redirect(url_for('chat'))
        else:
            flash('Invalid email or password.', 'error')
            return redirect(url_for('login'))
    
    return render_template('login.html')


@app.route('/logout')
@require_login
def logout():
    """User logout."""
    logout_user()
    flash('You have been logged out.', 'success')
    return redirect(url_for('index'))


@app.route('/chat')
@require_login
def chat():
    """Chat interface for employees."""
    messages = ChatMessage.query.filter_by(user_id=current_user.id).order_by(ChatMessage.created_at.desc()).limit(50).all()
    messages = list(reversed(messages))
    return render_template('chat.html', messages=messages, user=current_user)


@app.route('/api/chat', methods=['POST'])
@require_login
def api_chat():
    """API endpoint for chat messages."""
    data = request.get_json()
    user_message = data.get('message', '').strip()
    
    if not user_message:
        return jsonify({'error': 'Message is required'}), 400
    
    documents = Document.query.all()
    chat_history = ChatMessage.query.filter_by(user_id=current_user.id).order_by(ChatMessage.created_at.desc()).limit(10).all()
    chat_history = list(reversed(chat_history))
    
    ai_response = generate_response(user_message, documents, chat_history)
    
    chat_msg = ChatMessage(
        user_id=current_user.id,
        message=user_message,
        response=ai_response
    )
    db.session.add(chat_msg)
    
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
        
        original_filename = secure_filename(file.filename)
        file_ext = get_file_extension(original_filename)
        unique_filename = f"{uuid.uuid4().hex}.{file_ext}"
        
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], unique_filename)
        file.save(file_path)
        
        file_size = os.path.getsize(file_path)
        content = extract_text(file_path, file_ext)
        
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
    total_questions = ChatMessage.query.count()
    active_users = db.session.query(ChatMessage.user_id).distinct().count()
    total_documents = Document.query.count()
    top_questions = QuestionAnalytics.query.order_by(QuestionAnalytics.count.desc()).limit(10).all()
    recent_questions = ChatMessage.query.order_by(ChatMessage.created_at.desc()).limit(20).all()
    documents = Document.query.order_by(Document.created_at.desc()).all()
    users = User.query.order_by(User.created_at.desc()).all()
    
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


@app.route('/admin/users/<int:user_id>/toggle-admin', methods=['POST'])
@require_admin
def toggle_admin(user_id):
    """Toggle admin status for a user."""
    user = User.query.get_or_404(user_id)
    
    if user.id == current_user.id:
        flash('You cannot change your own admin status.', 'error')
        return redirect(url_for('admin_dashboard'))
    
    if user.email == 'azrieydev@gmail.com':
        flash('Cannot change admin status of the primary admin account.', 'error')
        return redirect(url_for('admin_dashboard'))
    
    user.role = 'employee' if user.is_admin() else 'admin'
    db.session.commit()
    
    flash(f'User {user.email} is now {"an admin" if user.is_admin() else "an employee"}.', 'success')
    return redirect(url_for('admin_dashboard'))


@app.route('/users')
@require_admin
def users_management():
    """User management page for admins."""
    users = User.query.order_by(User.created_at.desc()).all()
    
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
