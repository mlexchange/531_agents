try {
    // Remove any existing context popup
    const existingPopup = document.getElementById('agent-context-popup');
    if (existingPopup) {
        existingPopup.remove();
    }

    // Create overlay
    const overlay = document.createElement('div');
    overlay.id = 'agent-context-popup';
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
            <h2 style="margin: 0; color: #dc2626; font-size: 20px; font-weight: 600;">❌ Error Processing Agent Context</h2>
            <button id="context-close-btn" style="background: #dc2626; color: white; border: none; padding: 8px 16px; border-radius: 6px; cursor: pointer; font-weight: 500; font-size: 14px;">Close</button>
        </div>

        <div style="padding: 20px; background: #fef2f2; border-radius: 6px; border: 1px solid #fecaca;">
            <p style="margin: 0 0 16px 0; color: #dc2626; font-weight: 500;">An error occurred while processing the agent context:</p>
            <pre style="margin: 0; font-family: monospace; background: #fff; padding: 12px; border-radius: 4px; border: 1px solid #e5e7eb; color: #374151; font-size: 13px; overflow-x: auto;">${ERROR_MESSAGE}</pre>
            <p style="margin: 16px 0 0 0; color: #6b7280; font-size: 14px;">Please check the logs for more details.</p>
        </div>
    `;

    // Add event listeners
    overlay.appendChild(popup);
    document.body.appendChild(overlay);

    // Close button
    document.getElementById('context-close-btn').onclick = function() {
        overlay.remove();
    };

    // Close on overlay click
    overlay.onclick = function(e) {
        if (e.target === overlay) {
            overlay.remove();
        }
    };

} catch (error) {
    console.error('Error creating error popup:', error);
    alert('Error displaying agent context error: ' + error.message);
}
