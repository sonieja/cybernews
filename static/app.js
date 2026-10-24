// app.js - makes search and filters "live" without reloading the page.
// How it works:
//   1. Watch the search box and the drop-downs.
//   2. When something changes, ask Flask for JSON: fetch('/api/articles?q=...')
//   3. Build new article cards from that JSON and put them on the page.
// Safety: I use textContent (never innerHTML) for data, so a title like
// "<script>" is shown as text and never runs.

const form = document.getElementById("filter-form");
const list = document.getElementById("article-list");
const countText = document.getElementById("result-count");

function makeBadge(text, cls) {
    const span = document.createElement("span");
    span.className = "badge " + cls;
    span.textContent = text;
    return span;
}

function makeCard(a) {
    const card = document.createElement("article");
    card.className = "card";

    const meta = document.createElement("div");
    meta.className = "meta";
    meta.appendChild(makeBadge(a.category, "cat"));
    if (a.is_sample) { meta.append(" "); meta.appendChild(makeBadge("Sample", "sample")); }

    const h3 = document.createElement("h3");
    const link = document.createElement("a");
    link.href = a.url;
    link.textContent = a.title;
    h3.appendChild(link);

    const summary = document.createElement("p");
    summary.textContent = a.summary;

    const date = document.createElement("p");
    date.className = "date";
    date.textContent = a.source + " · " + a.published_date;

    card.append(meta, h3, summary, date);
    return card;
}

async function loadArticles() {
    // Turn the form fields into ?q=...&category=... (URLSearchParams encodes them safely)
    const params = new URLSearchParams(new FormData(form));
    try {
        const response = await fetch("/api/articles?" + params.toString());
        if (!response.ok) throw new Error("HTTP " + response.status);
        const articles = await response.json();

        list.replaceChildren();   // remove the old cards
        if (articles.length === 0) {
            const p = document.createElement("p");
            p.className = "muted";
            p.textContent = "No articles match your search.";
            list.appendChild(p);
        }
        articles.forEach(a => list.appendChild(makeCard(a)));
        countText.textContent = articles.length + " article(s) found (loaded live with JavaScript)";
    } catch (err) {
        countText.textContent = "Could not load articles (" + err.message + "). Press Filter to try again.";
    }
}

if (form && list) {
    let timer;
    // Wait 300 ms after the last key press, so we don't call the server on every letter
    form.querySelector("#q").addEventListener("input", () => {
        clearTimeout(timer);
        timer = setTimeout(loadArticles, 300);
    });
    form.querySelectorAll("select, input[type=date]").forEach(el =>
        el.addEventListener("change", loadArticles));
    // Pressing Enter / the Filter button also uses fetch instead of reloading
    form.addEventListener("submit", e => { e.preventDefault(); loadArticles(); });
}
