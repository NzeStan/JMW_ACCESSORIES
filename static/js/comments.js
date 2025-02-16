// static/js/comments.js
class CommentSystem {
    constructor(config) {
        this.containerId = config.containerId;
        this.apiUrl = config.apiUrl || '/api/comments/';
        this.contentType = config.contentType;
        this.objectId = config.objectId;
        this.csrfToken = document.querySelector('[name=csrfmiddlewaretoken]').value;
        
        this.container = document.getElementById(this.containerId);
        this.init();
        this.setupGlobalEventListeners();
    }
    
    showError(message) {
        const alert = document.createElement('div');
        alert.className = 'alert alert-error mb-4';
        alert.innerHTML = `
            <svg xmlns="http://www.w3.org/2000/svg" class="stroke-current shrink-0 h-6 w-6" fill="none" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10 14l2-2m0 0l2-2m-2 2l-2-2m2 2l2 2m7-2a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
            <span>${message}</span>
        `;
        
        setTimeout(() => alert.remove(), 5000);
        this.container.insertBefore(alert, this.container.firstChild);
    }
    
    showSuccess(message) {
        const alert = document.createElement('div');
        alert.className = 'alert alert-success mb-4';
        alert.innerHTML = `
            <svg xmlns="http://www.w3.org/2000/svg" class="stroke-current shrink-0 h-6 w-6" fill="none" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
            <span>${message}</span>
        `;
        
        setTimeout(() => alert.remove(), 3000);
        this.container.insertBefore(alert, this.container.firstChild);
    }
    
    showLoading(element, show = true) {
        if (show) {
            element.disabled = true;
            element.innerHTML = '<span class="loading loading-spinner"></span> Loading...';
        } else {
            element.disabled = false;
            element.innerHTML = element.dataset.originalText;
        }
    }

    setupGlobalEventListeners() {
        // Use event delegation for all comment-related actions
        this.container.addEventListener('click', (e) => {
            const target = e.target;

            // Reply button clicks
            if (target.closest('.reply-button')) {
                const commentId = target.closest('.reply-button').dataset.commentId;
                this.toggleReplyForm(commentId);
            }

            // Cancel reply clicks
            if (target.closest('.cancel-reply')) {
                const commentId = target.closest('.cancel-reply').dataset.commentId;
                this.hideReplyForm(commentId);
            }

            // Submit reply clicks
            if (target.closest('.submit-reply')) {
                const submitBtn = target.closest('.submit-reply');
                const commentId = submitBtn.dataset.commentId;
                const replyForm = document.getElementById(`reply-form-${commentId}`);
                const content = replyForm.querySelector('textarea').value;
                this.submitComment(submitBtn, commentId, content);
            }
        });

        // Main comment submission
        document.getElementById('submit-comment').addEventListener('click', (e) => {
            this.submitComment(e.target);
        });

        // Ctrl+Enter for main comment
        document.getElementById('comment-input').addEventListener('keydown', (e) => {
            if ((e.ctrlKey || e.metaKey) && e.key === 'Enter') {
                const submitBtn = document.getElementById('submit-comment');
                this.submitComment(submitBtn);
            }
        });
    }

    toggleReplyForm(commentId) {
        // Hide all other reply forms first
        document.querySelectorAll('.reply-form').forEach(form => {
            if (form.id !== `reply-form-${commentId}`) {
                form.classList.add('hidden');
            }
        });

        const replyForm = document.getElementById(`reply-form-${commentId}`);
        if (replyForm) {
            replyForm.classList.toggle('hidden');
            if (!replyForm.classList.contains('hidden')) {
                replyForm.querySelector('textarea').focus();
            }
        }
    }

    hideReplyForm(commentId) {
        const replyForm = document.getElementById(`reply-form-${commentId}`);
        if (replyForm) {
            replyForm.classList.add('hidden');
            replyForm.querySelector('textarea').value = '';
        }
    }
    
    async init() {
        this.container.innerHTML = `
            <div class="mb-8">
                <textarea 
                    id="comment-input" 
                    class="textarea textarea-bordered w-full h-24" 
                    placeholder="Write your comment..."></textarea>
                <div class="mt-2">
                    <button 
                        id="submit-comment" 
                        class="btn btn-primary"
                        data-original-text="Post Comment">
                        Post Comment
                    </button>
                </div>
            </div>
            <div id="comments-list" class="space-y-4"></div>
        `;
        
        await this.loadComments();
    }
    
    async loadComments() {
        const commentsList = document.getElementById('comments-list');
        const loadingDiv = document.createElement('div');
        loadingDiv.className = 'flex justify-center items-center py-8';
        loadingDiv.innerHTML = '<span class="loading loading-spinner loading-lg"></span>';
        commentsList.appendChild(loadingDiv);

        try {
            const response = await fetch(
                `${this.apiUrl}?content_type=${this.contentType}&object_id=${this.objectId}`
            );
            
            if (!response.ok) {
                throw new Error('Failed to load comments');
            }
            
            const comments = await response.json();
            this.renderComments(comments);
        } catch (error) {
            console.error('Error loading comments:', error);
            this.showError('Failed to load comments. Please try again later.');
        } finally {
            loadingDiv.remove();
        }
    }
    
    renderComments(comments) {
        const commentsList = document.getElementById('comments-list');
        commentsList.innerHTML = '';
        
        if (comments.length === 0) {
            commentsList.innerHTML = `
                <div class="text-center py-8 text-base-content/70">
                    <p>No comments yet. Be the first to comment!</p>
                </div>
            `;
            return;
        }
        
        comments.forEach(comment => {
            commentsList.appendChild(this.createCommentElement(comment));
        });
    }
    
    createCommentElement(comment) {
        const div = document.createElement('div');
        div.className = 'rounded-lg p-3 sm:p-4 relative'; // Reduced padding on mobile
        div.id = `comment-${comment.id}`;
        
        const formattedDate = new Date(comment.created_at).toLocaleDateString('en-US', {
            year: 'numeric',
            month: 'long',
            day: 'numeric',
            hour: '2-digit',
            minute: '2-digit'
        });
        
        const isDeleted = comment.content === '[deleted]';
        
        // Add a visual indicator for nested comments
        const replyingTo = comment.parent ? 
            `<div class="text-sm text-base-content/70 mb-1">replying to ${comment.parent_username || 'previous comment'}</div>` : '';
        
        div.innerHTML = `
            ${replyingTo}
            <div class="bg-base-200 rounded-lg p-3 sm:p-4"> <!-- Comment container -->
                <div class="flex justify-between items-start flex-wrap gap-2">
                    <div class="flex items-center gap-2 flex-wrap">
                        <span class="font-bold">${comment.user.username}</span>
                        ${comment.is_admin ? 
                            '<span class="badge badge-primary">Admin</span>' : 
                            ''}
                    </div>
                    ${!isDeleted ? `
                        <button 
                            class="btn btn-ghost btn-sm reply-button" 
                            data-comment-id="${comment.id}"
                            data-original-text="Reply">
                            Reply
                        </button>
                    ` : ''}
                </div>
                <div class="text-sm text-base-content/70 mt-1">${formattedDate}</div>
                <div class="mt-2 ${isDeleted ? 'italic text-base-content/70' : ''}">${comment.content}</div>
            </div>
            
            <!-- Reply form -->
            <div class="reply-form hidden mt-3" id="reply-form-${comment.id}">
                <textarea 
                    class="textarea textarea-bordered w-full h-20" 
                    placeholder="Write your reply..."></textarea>
                <div class="flex justify-end gap-2 mt-2">
                    <button 
                        class="btn btn-ghost btn-sm cancel-reply"
                        data-comment-id="${comment.id}">
                        Cancel
                    </button>
                    <button 
                        class="btn btn-primary btn-sm submit-reply" 
                        data-comment-id="${comment.id}"
                        data-original-text="Submit Reply">
                        Submit Reply
                    </button>
                </div>
            </div>
            
            <!-- Replies container -->
            ${comment.replies && comment.replies.length > 0 ? `
                <div class="mt-3 space-y-3 pl-3 sm:pl-6 border-l-2 border-base-300">
                    ${comment.replies.map(reply => this.createCommentElement(reply).outerHTML).join('')}
                </div>
            ` : ''}
        `;
        
        
        return div;
    }

    async submitComment(buttonElement, parentId = null, content = null) {
        const commentContent = content || document.getElementById('comment-input').value;
        if (!commentContent.trim()) return;
        
        this.showLoading(buttonElement, true);
        
        try {
            const response = await fetch(this.apiUrl, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': this.csrfToken,
                },
                body: JSON.stringify({
                    content: commentContent,
                    content_type: this.contentType,
                    object_id: this.objectId,
                    parent: parentId,
                }),
            });
            
            if (!response.ok) {
                const data = await response.json();
                throw new Error(data.detail || 'Failed to post comment');
            }
            
            if (parentId) {
                this.hideReplyForm(parentId);
            } else {
                document.getElementById('comment-input').value = '';
            }
            
            this.showSuccess('Comment posted successfully!');
            await this.loadComments();
        } catch (error) {
            console.error('Error submitting comment:', error);
            this.showError(error.message || 'Failed to post comment. Please try again.');
        } finally {
            this.showLoading(buttonElement, false);
        }
    }
}

export default CommentSystem;