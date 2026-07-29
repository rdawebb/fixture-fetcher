type Competition = {
  code?: string;
  name: string;
  url: string;
};

type Team = {
  name: string;
  slug?: string;
  color?: string;
  text_on_color?: string;
  crest?: string;
  next_fixture?: string;
  competitions: Competition[];
};

type League = {
  league: string;
  slug?: string;
  teams: Team[];
};

type CalendarsData = {
  calendars: League[];
};

const SVG_NS = "http://www.w3.org/2000/svg";

const SUBSCRIBE_ICON = "static/assets/calendar-add.svg";
const DOWNLOAD_ICON = "static/assets/download.svg";

const COPIED_MESSAGE = "✓ Copied";
const COPY_FAILED_MESSAGE = "✗ Copy failed";
const COPIED_RESET_MS = 2000;

// Formatted in the viewer's own locale and timezone
const KICKOFF_FORMAT = new Intl.DateTimeFormat(undefined, {
  weekday: "short",
  day: "numeric",
  month: "short",
  hour: "2-digit",
  minute: "2-digit",
});

// Colours land in a CSS custom property, so anything but a plain hex is dropped
function safeColor(value: string | undefined): string | null {
  return value && /^#[0-9a-f]{6}$/i.test(value) ? value : null;
}

// Manifest URLs are relative to the page, which may or may not end in a slash
function absoluteUrl(path: string): string {
  return new URL(path, location.href).href;
}

function createIcon(path: string): SVGSVGElement {
  const svg = document.createElementNS(SVG_NS, "svg");
  svg.setAttribute("viewBox", "0 0 32 32");
  svg.setAttribute("width", "16");
  svg.setAttribute("height", "16");
  svg.setAttribute("fill", "none");
  svg.setAttribute("aria-hidden", "true");

  for (const d of path) {
    const path = document.createElementNS(SVG_NS, "path");
    path.setAttribute("d", d);
    path.setAttribute("stroke", "currentColor");
    path.setAttribute("stroke-width", "2");
    path.setAttribute("stroke-linecap", "round");
    path.setAttribute("stroke-linejoin", "round");
    svg.appendChild(path);
  }

  return svg;
}

function downloadIcs(fileUrl: string): void {
  const link = document.createElement("a");
  link.href = fileUrl;
  link.download = "";
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
}

function createCopyButton(label: string, url: string): HTMLButtonElement {
  const button = document.createElement("button");
  button.className = "chip copy";
  button.title = "Copy the calendar URL";

  const text = document.createElement("span");
  text.className = "chip-label";
  // Announce the confirmation, since the only visible feedback is this swap
  text.setAttribute("aria-live", "polite");
  text.textContent = label;
  button.appendChild(text);

  let resetTimer: number | undefined;

  button.addEventListener("click", async () => {
    let message = COPIED_MESSAGE;

    try {
      // Undefined outside a secure context, which throws here and is handled
      // like any other clipboard failure
      await navigator.clipboard.writeText(url);
    } catch (err) {
      console.error("Could not copy calendar URL:", err);
      message = COPY_FAILED_MESSAGE;
    }

    text.textContent = message;
    // Restart the countdown so a second click doesn't restore the label early
    window.clearTimeout(resetTimer);
    resetTimer = window.setTimeout(() => {
      text.textContent = label;
    }, COPIED_RESET_MS);
  });

  return button;
}

function createSubscribeLink(url: string): HTMLAnchorElement {
  const link = document.createElement("a");
  // webcal:// hands the feed straight to the OS calendar app, rather than
  // asking the visitor to copy a URL and find the "add by URL" dialog
  link.href = url.replace(/^https?:/, "webcal:");
  link.className = "chip subscribe";
  link.title = "Subscribe in your calendar app";
  link.appendChild(createIcon(SUBSCRIBE_ICON));

  const text = document.createElement("span");
  text.textContent = "Subscribe";
  link.appendChild(text);

  return link;
}

function createDownloadButton(fileUrl: string): HTMLButtonElement {
  const button = document.createElement("button");
  button.className = "chip download";
  button.title = "Download .ics file";
  button.setAttribute("aria-label", "Download .ics file");
  button.appendChild(createIcon(DOWNLOAD_ICON));
  button.addEventListener("click", () => downloadIcs(fileUrl));

  return button;
}

function createCompetition(competition: Competition): HTMLLIElement {
  const item = document.createElement("li");
  const url = absoluteUrl(competition.url);

  item.append(
    createCopyButton(competition.name, url),
    createSubscribeLink(url),
    createDownloadButton(competition.url),
  );

  return item;
}

function createCrest(src: string): HTMLImageElement {
  const crest = document.createElement("img");
  crest.className = "crest";
  crest.src = src;
  crest.alt = "";
  crest.loading = "lazy";
  crest.width = 24;
  crest.height = 24;
  // Crests are hotlinked, so drop the image on a 404 rather than leaving a
  // broken-image placeholder
  crest.addEventListener("error", () => crest.remove());

  return crest;
}

function createNextFixture(isoDate: string): HTMLParagraphElement | null {
  const kickoff = new Date(isoDate);
  if (Number.isNaN(kickoff.getTime())) {
    return null;
  }

  const line = document.createElement("p");
  line.className = "next-fixture";
  line.textContent = `Next: ${KICKOFF_FORMAT.format(kickoff)}`;

  return line;
}

function createTeam(team: Team): HTMLDivElement {
  const section = document.createElement("div");
  section.className = "team-section";

  // Teams without a colour inherit the defaults from :root
  const accent = safeColor(team.color);
  if (accent) {
    section.style.setProperty("--accent", accent);

    const accentText = safeColor(team.text_on_color);
    if (accentText) {
      section.style.setProperty("--accent-text", accentText);
    }
  }

  const heading = document.createElement("div");
  heading.className = "team-name";

  if (team.crest) {
    heading.appendChild(createCrest(team.crest));
  }

  const name = document.createElement("span");
  name.textContent = team.name;
  heading.appendChild(name);
  section.appendChild(heading);

  if (team.next_fixture) {
    const nextFixture = createNextFixture(team.next_fixture);
    if (nextFixture) {
      section.appendChild(nextFixture);
    }
  }

  const competitions = document.createElement("ul");
  competitions.className = "competitions-list";
  for (const competition of team.competitions) {
    competitions.appendChild(createCompetition(competition));
  }
  section.appendChild(competitions);

  return section;
}

function createLeague(league: League): HTMLDetailsElement {
  const panel = document.createElement("details");
  panel.className = "league-section";
  panel.open = true;

  const summary = document.createElement("summary");
  const heading = document.createElement("h2");
  heading.textContent = league.league;
  summary.appendChild(heading);
  panel.appendChild(summary);

  for (const team of league.teams) {
    panel.appendChild(createTeam(team));
  }

  return panel;
}

function showError(errorDiv: HTMLElement, message: string): void {
  errorDiv.className = "error";

  const heading = document.createElement("strong");
  heading.textContent = "Error loading calendars:";
  errorDiv.replaceChildren(heading, document.createTextNode(message));
}

async function loadCalendars(): Promise<void> {
  const contentDiv = document.getElementById("content");
  const errorDiv = document.getElementById("error");
  const loadingDiv = document.getElementById("loading");

  try {
    const response = await fetch("calendars.json");
    if (!response.ok) {
      throw new Error(`Failed to load calendars: ${response.status}`);
    }

    const data = (await response.json()) as CalendarsData;

    if (!data.calendars || data.calendars.length === 0) {
      if (loadingDiv) loadingDiv.textContent = "No calendars available yet.";
      return;
    }

    if (loadingDiv) loadingDiv.style.display = "none";
    if (contentDiv) {
      contentDiv.replaceChildren(...data.calendars.map(createLeague));
    }
  } catch (err) {
    if (loadingDiv) loadingDiv.style.display = "none";
    if (errorDiv) {
      const message =
        err && typeof err === "object" && "message" in err
          ? (err as { message: string }).message
          : String(err);
      showError(errorDiv, message);
    }
    console.error("Error loading calendars:", err);
  }
}

// Load calendars when page loads
document.addEventListener("DOMContentLoaded", loadCalendars);
