try {
    // Remove any existing history popup
    const existingPopup = document.getElementById('execution-history-popup');
    if (existingPopup) {
        existingPopup.remove();
    }

    // Create overlay
    const overlay = document.createElement('div');
    overlay.id = 'execution-history-popup';
    overlay.style.cssText = `
        position: fixed;
        top: 0;
        left: 0;
        width: 100%;
        height: 100%;
        background: rgba(0, 0, 0, 0.8);
        z-index: 10000;
        display: flex;
        justify-content: center;
        align-items: center;
    `;

    // Create popup content
    const popup = document.createElement('div');
    popup.style.cssText = `
        background: white;
        border-radius: 8px;
        padding: 24px;
        width: 90%;
        max-width: 1200px;
        max-height: 80vh;
        overflow-y: auto;
        box-shadow: 0 25px 50px -12px rgba(0, 0, 0, 0.25);
        color: #333;
        font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'Roboto', sans-serif;
    `;

    popup.innerHTML = `
        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px; padding-bottom: 16px; border-bottom: 2px solid #e5e7eb;">
            <h2 style="margin: 0; color: #374151; font-size: 20px; font-weight: 600;">📋 ALS Assistant Execution History</h2>
            <button id="history-close-btn" style="background: #dc2626; color: white; border: none; padding: 8px 16px; border-radius: 6px; cursor: pointer; font-weight: 500; font-size: 14px;">Close</button>
        </div>

        <div style="line-height: 1.6;">
            ${FORMATTED_HISTORY}
        </div>
    `;

    // Add event listeners
    overlay.appendChild(popup);
    document.body.appendChild(overlay);

    // Close button
    document.getElementById('history-close-btn').onclick = function() {
        overlay.remove();
    };

    // Close on overlay click
    overlay.onclick = function(e) {
        if (e.target === overlay) {
            overlay.remove();
        }
    };

} catch (error) {
    console.error('Error creating execution history popup:', error);
    alert('Error displaying execution history: ' + error.message);
}
