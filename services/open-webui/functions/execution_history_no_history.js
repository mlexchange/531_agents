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
        max-width: 600px;
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

        <div style="text-align: center; padding: 40px 20px; color: #6b7280; font-size: 16px; line-height: 1.6;">
            <div style="font-size: 48px; margin-bottom: 16px;">⚠️</div>
            <h3 style="margin: 0 0 16px 0; color: #374151; font-size: 18px; font-weight: 600;">No Execution History Available</h3>
            <p style="margin: 0; color: #6b7280;">No ALS Assistant execution history found in recent messages. The execution history tracks:</p>
            <ul style="text-align: left; margin: 20px 0; color: #6b7280; line-height: 1.8;">
                <li><strong>Step execution details</strong></li>
                <li><strong>Success/failure status</strong></li>
                <li><strong>Timing information</strong></li>
                <li><strong>Parameters and results</strong></li>
                <li><strong>Error messages</strong></li>
            </ul>
            <p style="margin: 0; color: #6b7280; font-style: italic;">Execute an ALS Assistant query to generate execution history.</p>
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
    alert('Error displaying execution history');
}
