function copyToClipboard(text: string) {
  navigator.clipboard
    .writeText(text)
    .then(() => {
      alert("Calendar URL copied to clipboard!");
    })
    .catch((err) => {
      alert("Failed to copy link: " + err);
    });
}

function escapeHtml(text: string): string {
  return text
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#39;");
}

// Colours land in a style attribute, so anything but a plain hex is dropped
function safeColor(value: string | undefined): string | null {
  return value && /^#[0-9a-f]{6}$/i.test(value) ? value : null;
}

function downloadIcs(fileUrl: string) {
  const link = document.createElement("a");
  link.href = fileUrl;
  link.download = "";
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
}

async function loadCalendars() {
  const contentDiv = document.getElementById("content");
  const errorDiv = document.getElementById("error");
  const loadingDiv = document.getElementById("loading");

  try {
    const response = await fetch("calendars.json");
    if (!response.ok) {
      throw new Error(`Failed to load calendars: ${response.status}`);
    }

    const data = await response.json();

    if (!data.calendars || data.calendars.length === 0) {
      if (loadingDiv) loadingDiv.textContent = "No calendars available yet.";
      return;
    }

    if (loadingDiv) loadingDiv.style.display = "none";
    if (contentDiv) {
      type Competition = {
        name: string;
        url: string;
      };

      type Team = {
        name: string;
        slug?: string;
        color?: string;
        text_on_color?: string;
        crest?: string;
        competitions: Competition[];
      };

      type League = {
        league: string;
        teams: Team[];
      };

      type CalendarsData = {
        calendars: League[];
      };

      contentDiv.innerHTML = (data as CalendarsData).calendars
        .map(
          (league: League) => `
							<div class="league-section">
								<h2>${escapeHtml(league.league)}</h2>
								${league.teams
                  .map((team: Team) => {
                    const accent = safeColor(team.color);
                    const accentText = safeColor(team.text_on_color);
                    // Teams without a colour inherit the default black from :root
                    const accentStyle = accent
                      ? ` style="--accent:${accent}${accentText ? `;--accent-text:${accentText}` : ""}"`
                      : "";
                    // Crests are hotlinked, so drop the image if a 404 rather than broken link
                    const crest = team.crest
                      ? `<img class="crest" src="${escapeHtml(team.crest)}" alt="" loading="lazy" width="24" height="24" onerror="this.remove()">`
                      : "";
                    return `
									<div class="team-section"${accentStyle}>
										<div class="team-name">${crest}<span>${escapeHtml(team.name)}</span></div>
										<ul class="competitions-list">
											${team.competitions
                        .map((comp: Competition) => {
                          const calendarUrl =
                            location.origin +
                            location.pathname.replace(/\/$/, "") +
                            "/" +
                            comp.url.replace(/^\/+/, "");
                          return `
													<li>
														<button onclick="copyToClipboard('${calendarUrl}')">${escapeHtml(comp.name)}</button>
														<button onclick="downloadIcs('${comp.url}')" title="Download .ics file" class="download-btn">
															<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" fill="none" viewBox="0 0 32 32">
																<path stroke="currentColor" stroke-linecap="round" stroke-width="2" d="M16 22V5"/>
																<path stroke="currentColor" stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 16l7 7 7-7M9 27h14"/>
															</svg>
														</button>
													</li>
												`;
                        })
                        .join("")}
										</ul>
									</div>
								`;
                  })
                  .join("")}
							</div>
						`,
        )
        .join("");
    }
  } catch (err) {
    if (loadingDiv) loadingDiv.style.display = "none";
    if (errorDiv) {
      errorDiv.className = "error";
      const errorMessage =
        err && typeof err === "object" && "message" in err
          ? (err as { message: string }).message
          : String(err);
      errorDiv.innerHTML = `<strong>Error loading calendars:</strong> ${errorMessage}`;
    }
    console.error("Error loading calendars:", err);
  }
}

// Load calendars when page loads
document.addEventListener("DOMContentLoaded", loadCalendars);
