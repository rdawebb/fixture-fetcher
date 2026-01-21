"use strict";
function copyToClipboard(text) {
    navigator.clipboard.writeText(text).then(() => {
        alert('Calendar URL copied to clipboard!');
    }).catch(err => {
        alert('Failed to copy link: ' + err);
    });
}
function downloadIcs(fileUrl) {
    const link = document.createElement('a');
    link.href = fileUrl;
    link.download = '';
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
}
async function loadCalendars() {
    const contentDiv = document.getElementById('content');
    const errorDiv = document.getElementById('error');
    const loadingDiv = document.getElementById('loading');
    try {
        const response = await fetch('calendars.json');
        if (!response.ok) {
            throw new Error(`Failed to load calendars: ${response.status}`);
        }
        const data = await response.json();
        if (!data.calendars || data.calendars.length === 0) {
            if (loadingDiv)
                loadingDiv.textContent = 'No calendars available yet.';
            return;
        }
        if (loadingDiv)
            loadingDiv.style.display = 'none';
        if (contentDiv) {
            contentDiv.innerHTML = data.calendars.map((league) => `
							<div class="league-section">
								<h2>${league.league}</h2>
								${league.teams.map((team) => `
									<div class="team-section">
										<div class="team-name">${team.name}</div>
										<ul class="competitions-list">
											${team.competitions.map((comp) => {
                const calendarUrl = location.origin + '/' + comp.url.replace(/^\/+/, '');
                return `
													<li>
														<button onclick="copyToClipboard('${calendarUrl}')">${comp.name}</button>
														<button onclick="downloadIcs('${comp.url}')" title="Download .ics file" class="download-btn">
															<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" fill="none" viewBox="0 0 32 32">
																<path stroke="currentColor" stroke-linecap="round" stroke-width="2" d="M16 22V5"/>
																<path stroke="currentColor" stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 16l7 7 7-7M9 27h14"/>
															</svg>
														</button>
													</li>
												`;
            }).join('')}
										</ul>
									</div>
								`).join('')}
							</div>
						`).join('');
        }
    }
    catch (err) {
        if (loadingDiv)
            loadingDiv.style.display = 'none';
        if (errorDiv) {
            errorDiv.className = 'error';
            const errorMessage = (err && typeof err === 'object' && 'message' in err) ? err.message : String(err);
            errorDiv.innerHTML = `<strong>Error loading calendars:</strong> ${errorMessage}`;
        }
        console.error('Error loading calendars:', err);
    }
}
// Load calendars when page loads
document.addEventListener('DOMContentLoaded', loadCalendars);
//# sourceMappingURL=main.js.map