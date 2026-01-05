try {
    // Professional color palette - customize these variables
    const colors = {
        primary: '#669bbc',      // Indigo - main action buttons
        primaryHover: '#003049', // Darker indigo for hover
        secondary: '#b1a7a6',    // Gray - secondary actions
        secondaryHover: '#161a1d', // Darker gray for hover
        success: '#669bbc',      // Green - save/confirm actions
        successHover: '#003049', // Darker green for hover
        danger: '#C1121F',       // Red - delete/destructive actions
        dangerHover: '#780000',  // Darker red for hover
        background: '#ffffff',   // White backgrounds
        border: '#e5e7eb',       // Light gray borders
        text: '#374151',         // Dark gray text
        textLight: '#6b7280'     // Light gray text
    };

    // Remove any existing memory editor
    const existingEditor = document.getElementById('memory-editor-overlay');
    if (existingEditor) {
        existingEditor.remove();
    }

    // Create overlay
    const overlay = document.createElement('div');
    overlay.id = 'memory-editor-overlay';
    overlay.style.cssText = `
        position: fixed;
        top: 0;
        left: 0;
        width: 100%;
        height: 100%;
        background: rgba(0, 0, 0, 0.7);
        z-index: 10000;
        display: flex;
        justify-content: center;
        align-items: center;
    `;

    // Create editor container
    const editor = document.createElement('div');
    editor.style.cssText = `
        background: white;
        border-radius: 12px;
        padding: 24px;
        width: 90%;
        max-width: 800px;
        max-height: 80vh;
        overflow-y: auto;
        box-shadow: 0 20px 25px -5px rgba(0, 0, 0, 0.1), 0 10px 10px -5px rgba(0, 0, 0, 0.04);
        color: #333;
    `;

    // Parse the memories data - PLACEHOLDER will be replaced by Python
    let memories = JSON.parse("${ENTRIES_JSON}");

    // Create editor HTML - PLACEHOLDER will be replaced by Python
    editor.innerHTML = `
        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 24px; padding-bottom: 16px; border-bottom: 2px solid ${colors.border};">
            <h2 style="margin: 0; color: ${colors.text}; font-size: 24px; font-weight: bold;">Edit Memories for ${USER_ID}</h2>
            <button id="memory-close-btn" style="background: ${colors.danger}; color: white; border: none; padding: 8px 16px; border-radius: 6px; cursor: pointer; font-weight: 500; transition: background-color 0.2s;">✕ Close</button>
        </div>

        <div style="margin-bottom: 20px;">
            <button id="memory-add-btn" style="background: ${colors.success}; color: white; border: none; padding: 8px 16px; border-radius: 6px; cursor: pointer; margin-right: 10px; font-weight: 500; font-size: 14px; transition: background-color 0.2s;">+ Add Memory</button>
            <button id="memory-save-btn" style="background: ${colors.primary}; color: white; border: none; padding: 8px 16px; border-radius: 6px; cursor: pointer; margin-right: 10px; font-weight: 500; font-size: 14px; transition: background-color 0.2s;">Save Changes</button>
            <button id="memory-cancel-btn" style="background: ${colors.secondary}; color: white; border: none; padding: 8px 16px; border-radius: 6px; cursor: pointer; font-weight: 500; font-size: 14px; transition: background-color 0.2s;">Cancel</button>
        </div>

        <div id="memories-container"></div>
    `;

    // Function to render memories
    function renderMemories() {
        const container = document.getElementById('memories-container');
        container.innerHTML = '';

        if (memories.length === 0) {
            container.innerHTML = '<p style="text-align: center; color: ' + colors.textLight + '; font-style: italic; padding: 40px;">No memories yet. Click "Add Memory" to create your first one!</p>';
            return;
        }

        // Sort memories by timestamp (newest first)
        const sortedMemories = [...memories].sort((a, b) => {
            return new Date(b.timestamp) - new Date(a.timestamp);
        });

        sortedMemories.forEach((memory, displayIndex) => {
            const actualIndex = memories.findIndex(m => m === memory);
            const memoryDiv = document.createElement('div');
            memoryDiv.style.cssText = `
                border: 2px solid ${colors.border};
                padding: 20px;
                margin-bottom: 16px;
                border-radius: 8px;
                background-color: #f9fafb;
                position: relative;
            `;

            memoryDiv.innerHTML = `
                <div style="display: flex; justify-content: flex-end; margin-bottom: 12px;">
                    <button onclick="deleteMemory(${actualIndex})" style="background: ${colors.danger}; color: white; border: none; padding: 6px 12px; border-radius: 4px; cursor: pointer; font-size: 12px; transition: background-color 0.2s;" onmouseover="this.style.backgroundColor='${colors.dangerHover}'" onmouseout="this.style.backgroundColor='${colors.danger}'">Delete</button>
                </div>
                <div style="margin-bottom: 12px;">
                    <label style="display: block; font-weight: 600; margin-bottom: 6px; color: ${colors.text};">Timestamp:</label>
                    <input type="text" value="${memory.timestamp}" onchange="updateTimestamp(${actualIndex}, this.value)" style="width: 100%; padding: 8px 12px; border: 1px solid ${colors.border}; border-radius: 6px; font-size: 14px;">
                </div>
                <div>
                    <label style="display: block; font-weight: 600; margin-bottom: 6px; color: ${colors.text};">Content:</label>
                    <textarea onchange="updateContent(${actualIndex}, this.value)" oninput="autoResizeTextarea(this)" style="width: 100%; min-height: 40px; padding: 12px; border: 1px solid ${colors.border}; border-radius: 6px; resize: vertical; font-family: inherit; font-size: 14px; line-height: 1.5; overflow: hidden;">${memory.content}</textarea>
                </div>
            `;

            container.appendChild(memoryDiv);
        });

        // Auto-resize all textareas after rendering
        container.querySelectorAll('textarea').forEach(textarea => {
            autoResizeTextarea(textarea);
        });
    }

    // Global functions for memory operations
    window.updateTimestamp = function(index, value) {
        memories[index].timestamp = value;
    };

    window.updateContent = function(index, value) {
        memories[index].content = value;
    };

    window.deleteMemory = function(index) {
        if (confirm('Are you sure you want to delete this memory?')) {
            memories.splice(index, 1);
            renderMemories();
        }
    };

    // Auto-resize textarea function
    window.autoResizeTextarea = function(textarea) {
        textarea.style.height = 'auto';
        textarea.style.height = Math.max(40, textarea.scrollHeight) + 'px';
    };

    // Add new memory function with popup dialog
    function addNewMemory() {
        const addBtn = document.getElementById('memory-add-btn');
        const originalText = addBtn.innerHTML;
        addBtn.innerHTML = '⏳ Creating...';
        addBtn.disabled = true;

        createNewMemoryPopup().then((newMemory) => {
            addBtn.innerHTML = originalText;
            addBtn.disabled = false;

            if (newMemory) {
                memories.unshift(newMemory);
                renderMemories();
            }
        });
    }

    // Create new memory popup dialog
    function createNewMemoryPopup() {
        return new Promise((resolve) => {
            const newMemoryOverlay = document.createElement('div');
            newMemoryOverlay.style.cssText = `
                position: fixed;
                top: 0;
                left: 0;
                width: 100%;
                height: 100%;
                background: rgba(0, 0, 0, 0.8);
                z-index: 20000;
                display: flex;
                justify-content: center;
                align-items: center;
            `;

            const dialog = document.createElement('div');
            dialog.style.cssText = `
                background: white;
                border-radius: 12px;
                padding: 32px;
                width: 90%;
                max-width: 600px;
                box-shadow: 0 25px 50px -12px rgba(0, 0, 0, 0.25);
                color: #333;
                animation: slideIn 0.3s ease-out;
            `;

            if (!document.getElementById('memory-dialog-styles')) {
                const style = document.createElement('style');
                style.id = 'memory-dialog-styles';
                style.textContent = `
                    @keyframes slideIn {
                        from { transform: translateY(-50px); opacity: 0; }
                        to { transform: translateY(0); opacity: 1; }
                    }
                `;
                document.head.appendChild(style);
            }

            const now = new Date();
            const currentTimestamp = now.getFullYear() + '-' +
                String(now.getMonth() + 1).padStart(2, '0') + '-' +
                String(now.getDate()).padStart(2, '0') + ' ' +
                String(now.getHours()).padStart(2, '0') + ':' +
                String(now.getMinutes()).padStart(2, '0');

            dialog.innerHTML = `
                <div style="text-align: center; margin-bottom: 24px;">
                    <h3 style="margin: 0; color: ${colors.success}; font-size: 20px; font-weight: bold;">✨ Create New Memory</h3>
                    <p style="margin: 8px 0 0 0; color: ${colors.textLight}; font-size: 14px;">Add a new memory to your personal collection</p>
                </div>

                <div style="margin-bottom: 20px;">
                    <label style="display: block; font-weight: 600; margin-bottom: 8px; color: ${colors.text};">Timestamp:</label>
                    <input type="text" id="new-memory-timestamp" value="${currentTimestamp}" style="width: 100%; padding: 12px; border: 2px solid ${colors.border}; border-radius: 8px; font-size: 14px; transition: border-color 0.2s;">
                </div>

                <div style="margin-bottom: 32px;">
                    <label style="display: block; font-weight: 600; margin-bottom: 8px; color: ${colors.text};">Memory Content:</label>
                    <textarea id="new-memory-content" placeholder="What would you like me to remember?" oninput="autoResizeTextarea(this)" style="width: 100%; min-height: 50px; padding: 12px; border: 2px solid ${colors.border}; border-radius: 8px; resize: vertical; font-family: inherit; font-size: 14px; line-height: 1.5; transition: border-color 0.2s; overflow: hidden;"></textarea>
                </div>

                <div style="display: flex; gap: 12px; justify-content: flex-end;">
                    <button id="cancel-new-memory" style="background: ${colors.secondary}; color: white; border: none; padding: 10px 20px; border-radius: 8px; cursor: pointer; font-weight: 500; font-size: 14px; transition: background-color 0.2s;">Cancel</button>
                    <button id="save-new-memory" style="background: ${colors.success}; color: white; border: none; padding: 10px 20px; border-radius: 8px; cursor: pointer; font-weight: 500; font-size: 14px; transition: background-color 0.2s;">Add Memory</button>
                </div>
            `;

            const timestampInput = dialog.querySelector('#new-memory-timestamp');
            const contentTextarea = dialog.querySelector('#new-memory-content');
            const saveBtn = dialog.querySelector('#save-new-memory');
            const cancelBtn = dialog.querySelector('#cancel-new-memory');

            [timestampInput, contentTextarea].forEach(input => {
                input.addEventListener('focus', () => input.style.borderColor = colors.success);
                input.addEventListener('blur', () => input.style.borderColor = colors.border);
            });

            saveBtn.addEventListener('mouseenter', () => saveBtn.style.backgroundColor = colors.successHover);
            saveBtn.addEventListener('mouseleave', () => saveBtn.style.backgroundColor = colors.success);
            cancelBtn.addEventListener('mouseenter', () => cancelBtn.style.backgroundColor = colors.secondaryHover);
            cancelBtn.addEventListener('mouseleave', () => cancelBtn.style.backgroundColor = colors.secondary);

            function closeDialog(result) {
                newMemoryOverlay.remove();
                resolve(result);
            }

            cancelBtn.onclick = () => closeDialog(null);

            saveBtn.onclick = () => {
                const timestamp = timestampInput.value.trim();
                const content = contentTextarea.value.trim();

                if (!content) {
                    contentTextarea.style.borderColor = colors.danger;
                    contentTextarea.focus();
                    return;
                }

                closeDialog({
                    timestamp: timestamp || currentTimestamp,
                    content: content
                });
            };

            newMemoryOverlay.onclick = (e) => {
                if (e.target === newMemoryOverlay) {
                    closeDialog(null);
                }
            };

            document.addEventListener('keydown', function escapeHandler(e) {
                if (e.key === 'Escape') {
                    document.removeEventListener('keydown', escapeHandler);
                    closeDialog(null);
                }
            });

            newMemoryOverlay.appendChild(dialog);
            document.body.appendChild(newMemoryOverlay);

            setTimeout(() => {
                autoResizeTextarea(contentTextarea);
                contentTextarea.focus();
            }, 100);
        });
    }

    // Set up event listeners and return a promise
    function setupEventListeners() {
        return new Promise((resolve) => {
            const addBtn = document.getElementById('memory-add-btn');
            const saveBtn = document.getElementById('memory-save-btn');
            const cancelBtn = document.getElementById('memory-cancel-btn');
            const closeBtn = document.getElementById('memory-close-btn');

            addBtn.onclick = addNewMemory;

            closeBtn.onclick = function() {
                overlay.remove();
                resolve({ action: 'cancel' });
            };

            cancelBtn.onclick = function() {
                overlay.remove();
                resolve({ action: 'cancel' });
            };

            saveBtn.onclick = function() {
                overlay.remove();
                resolve({ action: 'save', memories: memories });
            };

            addBtn.addEventListener('mouseover', () => addBtn.style.backgroundColor = colors.successHover);
            addBtn.addEventListener('mouseout', () => addBtn.style.backgroundColor = colors.success);

            saveBtn.addEventListener('mouseover', () => saveBtn.style.backgroundColor = colors.primaryHover);
            saveBtn.addEventListener('mouseout', () => saveBtn.style.backgroundColor = colors.primary);

            cancelBtn.addEventListener('mouseover', () => cancelBtn.style.backgroundColor = colors.secondaryHover);
            cancelBtn.addEventListener('mouseout', () => cancelBtn.style.backgroundColor = colors.secondary);

            closeBtn.addEventListener('mouseover', () => closeBtn.style.backgroundColor = colors.dangerHover);
            closeBtn.addEventListener('mouseout', () => closeBtn.style.backgroundColor = colors.danger);

            overlay.onclick = function(e) {
                if (e.target === overlay) {
                    overlay.remove();
                    resolve({ action: 'cancel' });
                }
            };
        });
    }

    // Append to document and render
    overlay.appendChild(editor);
    document.body.appendChild(overlay);
    renderMemories();

    // Return the promise that resolves when user interacts
    return await setupEventListeners();

} catch (error) {
    return { action: 'error', message: 'Error creating editor: ' + error.message };
}
