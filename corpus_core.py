"""auto_skill_selector — corpus_core.py (Fase 2, Master Prompt §3.2).

Korpus inti pelatihan: TEPAT 6 skill representatif per pilar x 9 pilar = 54
kelas. Setiap entri adalah SKILL.md lengkap (frontmatter + When to Use +
Quick Reference + Procedure) dengan istilah dwibahasa agar zona S/A/B/C
terisi seimbang. Skill inti ditulis ke <skills_root>/<pilar>/<slug>/SKILL.md
dan menjadi basis pelatihan; hasil harvesting multi-katalog masuk sebagai
KELAS TAMBAHAN (tidak menggeser kuota inti).
"""
from __future__ import annotations

from pathlib import Path

# (slug, name, description, when_to_use, procedure)
CORE_SKILLS: dict[str, list[tuple[str, str, str, str, str]]] = {
    "data-analytics": [
        ("sql-bi-dashboard", "SQL BI Dashboard",
         "Build SQL queries and business intelligence dashboards with KPI charts, "
         "kueri SQL, dasbor kecerdasan bisnis, grafik metrik, buat grafik tren, "
         "visualisasi data penjualan, chart grafik batang garis.",
         "Use when the user asks to query a database, build a BI dashboard, or "
         "visualize KPI metrics from SQL tables.",
         "Write the SQL query, validate row counts, then render dashboard charts "
         "(bar, line, KPI cards). Verify totals against source tables."),
        ("tabular-pivot-cleaning", "Tabular Pivot Cleaning",
         "Clean messy tabular data, build pivot tables and aggregations, "
         "pembersihan data tabel, tabel pivot, agregasi data kotor, bersihkan "
         "data CSV, ekstrak tabel jadi CSV rapi, rapikan tabel.",
         "Use when a CSV or spreadsheet table needs cleaning, deduplication, "
         "pivot summaries or tabular reshaping.",
         "Profile columns, fix types and outliers, build the pivot, export a "
         "clean table. Check sums before and after."),
        ("statistical-forecasting", "Statistical Forecasting",
         "Fit statistical forecast models, time series regression and trend "
         "projection, peramalan statistik, deret waktu, proyeksi tren.",
         "Use when the user wants forecasts, trend projections, regression fits "
         "or time-series prediction on numeric data.",
         "Split train/test, fit the model, report confidence intervals and "
         "backtest error. Plot forecast vs actuals."),
        ("cohort-funnel-analysis", "Cohort Funnel Analysis",
         "Run cohort retention and funnel conversion analysis, analisis kohort "
         "retensi, corong konversi pengguna.",
         "Use for retention cohorts, churn, funnel drop-off and conversion "
         "analysis on user event data.",
         "Define cohort windows, compute retention matrix and funnel steps, "
         "highlight the biggest drop-off."),
        ("etl-pipeline", "ETL Pipeline",
         "Design ETL data pipelines: extract transform load, pipa data ETL, "
         "ekstraksi transformasi pemuatan, integrasi data.",
         "Use when building or fixing an ETL/ELT pipeline, data ingestion jobs "
         "or warehouse loading.",
         "Map sources to targets, write transform steps, add idempotent loads "
         "and row-count reconciliation."),
        ("spreadsheet-modeling", "Spreadsheet Modeling",
         "Build spreadsheet models with formulas and structured sheets, "
         "pemodelan lembar sebar, rumus, model spreadsheet terstruktur.",
         "Use when the user asks for a spreadsheet model, formula-driven sheet "
         "or structured workbook layout (generic spreadsheet, not Excel-specific).",
         "Lay out input/calc/output sheets, wire formulas, add checks and "
         "document assumptions."),
    ],
    "3d-video-animation": [
        ("blender-3d-modeling", "Blender 3D Modeling",
         "Drive Blender for 3D modeling, mesh sculpting, materials and rendering, "
         "pemodelan 3D Blender, mesh, tekstur, render.",
         "Use for Blender scenes, 3D models, sculpting, shading and render setup.",
         "Block out the mesh, refine topology, assign materials, set camera and "
         "lighting, render a preview."),
        ("video-editing-ffmpeg", "Video Editing FFmpeg",
         "Edit and process video with FFmpeg: cut, concat, transcode, filters, "
         "penyuntingan video FFmpeg, potong, gabung, konversi video.",
         "Use when cutting, joining, transcoding or filtering video files with "
         "ffmpeg or an NLE timeline.",
         "Probe streams, build the filter graph, encode with sane presets, "
         "verify duration and A/V sync."),
        ("motion-graphics", "Motion Graphics",
         "Create motion graphics and animated titles, grafis gerak, animasi "
         "judul, lower thirds, transisi.",
         "Use for animated logos, title sequences, lower thirds and kinetic "
         "typography.",
         "Design keyframes, ease curves, export with alpha or ProRes when "
         "compositing downstream."),
        ("subtitle-captioning", "Subtitle Captioning",
         "Generate subtitles and captions, takarir, teks terjemahan video, "
         "SRT, VTT, sinkronisasi waktu.",
         "Use when a video needs subtitles, captions, SRT/VTT files or "
         "translation timing.",
         "Transcribe, segment into readable lines, sync timestamps, export "
         "SRT/VTT and burn-in if requested."),
        ("storyboard-animatic", "Storyboard Animatic",
         "Draft storyboards and animatics from a brief, papan cerita, animatik, "
         "alur adegan, shot list.",
         "Use when planning shots, storyboard panels or an animatic before "
         "production.",
         "Break the script into shots, sketch panels with camera notes, time "
         "the animatic against the voiceover."),
        ("color-grading", "Color Grading",
         "Grade video color: LUTs, scopes, look development, gradasi warna, "
         "koreksi warna, LUT, scopes.",
         "Use for color correction, creative looks, LUT application and shot "
         "matching.",
         "Balance exposure and white balance, apply the look, match shots on "
         "scopes, export the graded master."),
    ],
    "audio-music-podcast": [
        ("podcast-production", "Podcast Production",
         "Produce podcast episodes end to end, produksi siniar, episode podcast, "
         "rekaman, editing, publikasi.",
         "Use when recording, editing or publishing a podcast episode.",
         "Record clean tracks, edit filler, mix levels, add intro/outro, "
         "export loudness-normalized MP3 and show notes."),
        ("audio-transcription-whisper", "Audio Transcription Whisper",
         "Transcribe audio with Whisper, transkripsi audio, ubah suara jadi "
         "teks, notula rekaman.",
         "Use when converting speech recordings or meeting audio into text.",
         "Run Whisper with the right language, segment speakers, proofread "
         "names and numbers, deliver the transcript."),
        ("noise-reduction-mastering", "Noise Reduction Mastering",
         "Clean audio noise and master loudness, pengurangan derau, mastering "
         "audio, loudness, denoise.",
         "Use for hiss/hum removal, dialogue cleanup and loudness mastering.",
         "Profile the noise, apply reduction gently, EQ/compress, limit to "
         "target LUFS, check on small speakers."),
        ("music-composition-midi", "Music Composition MIDI",
         "Compose music and MIDI arrangements, komposisi musik, aransemen MIDI, "
         "nada, chord, melodi.",
         "Use when writing melodies, chord progressions or MIDI arrangements.",
         "Sketch chords and melody, arrange parts, export MIDI and a rough "
         "mix for review."),
        ("voiceover-tts", "Voiceover TTS",
         "Generate voiceover and text-to-speech narration, sulih suara, teks ke "
         "suara, narasi TTS.",
         "Use when a script needs narration, voiceover or TTS audio.",
         "Pick voice and pacing, generate takes, fix pronunciations, export "
         "clean narration tracks."),
        ("stem-separation", "Stem Separation",
         "Separate audio stems: vocals, drums, bass, pemisahan stem, vokal, "
         "drum, bass, instrumental.",
         "Use when isolating vocals or instruments from a mixed track.",
         "Run the separation model, audition each stem, clean artifacts, "
         "export labeled stems."),
    ],
    "design-ui-ux": [
        ("infographic-design", "Infographic Design",
         "Compose infographics and visual data summaries, infografis, infografik, "
         "visualisasi data, poster informasi, visualisasikan data jadi "
         "infografis, ringkasan visual laporan.",
         "Use when the user asks for an infographic, visual summary or "
         "information poster.",
         "Structure the narrative, pick a layout grid, set typography and "
         "palette, render the infographic and check readability."),
        ("mermaid-architecture-diagram", "Mermaid Architecture Diagram",
         "Draw Mermaid flowcharts and architecture diagrams, diagram alur "
         "Mermaid, bagan arsitektur, sistem, ubah catatan jadi diagram alur, "
         "flowchart proses, sequence diagram.",
         "Use for flowcharts, sequence diagrams, architecture and system "
         "diagrams in Mermaid or SVG.",
         "List nodes and edges, write the Mermaid source, render and verify "
         "every connection matches the described system."),
        ("ui-wireframe-mockup", "UI Wireframe Mockup",
         "Design UI wireframes and mockups, kerangka kawat, purwarupa antarmuka, "
         "mockup layar, tata letak UI.",
         "Use when sketching screens, wireframes or high-fidelity UI mockups.",
         "Map user flows, lay out screens on a grid, annotate interactions, "
         "deliver wireframe then mockup."),
        ("brand-identity-typography", "Brand Identity Typography",
         "Build brand identity and typography systems, identitas merek, "
         "tipografi, logo, palet, pemandu gaya.",
         "Use for logos, brand palettes, type scales and style guides.",
         "Define brand attributes, design logo and palette, set the type "
         "scale, document usage rules."),
        ("web-landing-design", "Web Landing Design",
         "Design web landing pages, halaman arahan, desain web, landing page, "
         "hero, CTA, presentasi produk dalam halaman web, presentasi HTML, "
         "halaman web statis untuk produk.",
         "Use when designing a landing page or marketing website layout.",
         "Write the value proposition, structure hero/features/CTA sections, "
         "design responsive layout and hand off specs."),
        ("accessibility-audit", "Accessibility Audit",
         "Audit accessibility (a11y): WCAG, contrast, keyboard, screen reader, "
         "audit aksesibilitas, kontras, keyboard.",
         "Use when checking a product against WCAG or fixing accessibility "
         "issues. (Satu-satunya skill a11y di pilar ini.)",
         "Run automated checks, test keyboard and contrast, list violations "
         "with severity and fixes."),
    ],
    "finance-business": [
        ("financial-model-dcf", "Financial Model DCF",
         "Build discounted cash flow DCF valuation models, pemodelan keuangan, "
         "arus kas terdiskonto, valuasi, WACC.",
         "Use for DCF valuations, WACC, free cash flow projections and "
         "company valuation models.",
         "Project FCF, compute WACC, discount and terminal value, sanity-check "
         "implied multiples, sensitize key drivers."),
        ("mece-strategy-memo", "MECE Strategy Memo",
         "Structure problems with MECE issue trees and write strategy memos, "
         "kerangka MECE, pohon masalah, memo strategi ala konsultan, analisis "
         "kelebihan dan kekurangan, analisis vendor, analisis SWOT, pro kontra.",
         "Use when structuring a business problem MECE-style or drafting a "
         "consulting strategy memo.",
         "Define the question, build a MECE issue tree, prioritize branches, "
         "write the memo with so-what headlines."),
        ("pitch-deck-investor", "Pitch Deck Investor",
         "Craft investor pitch decks and narratives, dek pitch investor, "
         "narasi pendanaan, salindia pitch.",
         "Use when building a fundraising pitch deck or investor narrative.",
         "Shape the story arc, draft problem/solution/market/traction slides, "
         "tighten the ask and appendix."),
        ("invoice-ledger-reconciliation", "Invoice Ledger Reconciliation",
         "Reconcile invoices and ledgers, rekonsiliasi faktur dan buku besar, "
         "cocokkan tagihan, jurnal, rekonsiliasi neraca lajur, laporan laba dan "
         "rugi, laporan keuangan, hitung anuitas, pembukuan akuntansi.",
         "Use when matching invoices to ledger entries or reconciling accounts.",
         "Import both sides, match on keys and amounts, flag discrepancies, "
         "produce the reconciliation report."),
        ("pricing-unit-economics", "Pricing Unit Economics",
         "Analyze pricing and unit economics, penetapan harga, unit ekonomi, "
         "margin, CAC, LTV.",
         "Use for pricing strategy, contribution margin, CAC/LTV and unit "
         "economics analysis.",
         "Compute per-unit costs and margins, model CAC/LTV, test price "
         "scenarios, recommend a price point."),
        ("market-sizing", "Market Sizing",
         "Estimate market size TAM SAM SOM, ukuran pasar, estimasi pasar, "
         "top-down bottom-up.",
         "Use when estimating TAM/SAM/SOM or sizing a market opportunity.",
         "Choose top-down and bottom-up approaches, state assumptions, "
         "triangulate and present a range."),
    ],
    "writing-editorial": [
        ("seo-copywriting", "SEO Copywriting",
         "Write SEO copy and articles, penulisan SEO, naskah iklan, artikel "
         "blog, kata kunci.",
         "Use when writing SEO-optimized articles, landing copy or blog posts.",
         "Research keywords, outline search intent, write the draft, optimize "
         "headings and meta, check readability."),
        ("technical-documentation", "Technical Documentation",
         "Write technical documentation, dokumentasi teknis, panduan API, "
         "referensi, readme.",
         "Use for API docs, guides, READMEs and reference documentation.",
         "Inventory the surface, write task-oriented sections, add runnable "
         "examples, verify every command."),
        ("executive-brief-6pager", "Executive Brief 6-Pager",
         "Write Amazon-style 6-pagers and executive briefs, ringkasan "
         "eksekutif, memo 6 halaman, narasi keputusan.",
         "Use when drafting an executive brief, 6-pager or decision narrative.",
         "State the decision, write the narrative with data, append FAQs, "
         "edit for silence-room reading."),
        ("social-media-campaign", "Social Media Campaign",
         "Plan social media campaigns and content calendars, kampanye media "
         "sosial, kalender konten, hook.",
         "Use for campaign planning, content calendars and social copy.",
         "Define goals and audience, build the calendar, write hooks and "
         "captions per platform, set metrics."),
        ("press-release-pr", "Press Release PR",
         "Write press releases and PR announcements, siaran pers, pengumuman "
         "media, rilis berita.",
         "Use when announcing news to press or writing a press release.",
         "Lead with the newsworthy fact, add quotes and boilerplate, keep it "
         "to one page, provide media contact."),
        ("bilingual-translation", "Bilingual Translation Localization",
         "Translate and localize between Indonesian and English, penerjemahan "
         "dwibahasa, lokalisasi, ID EN.",
         "Use for ID<->EN translation, localization and bilingual rewriting.",
         "Translate meaning not words, keep terminology consistent, adapt "
         "locale formats, proofread both directions."),
    ],
    "productivity-office": [
        ("pdf-extraction-manipulation", "PDF Extraction Manipulation",
         "Extract, merge, split and OCR PDF documents, ekstraksi PDF, gabung "
         "PDF, pisah PDF, OCR, pindai, ekstrak tabel dari PDF, ambil data dari "
         "berkas PDF, konversi dokumen ke PDF, laporan PDF.",
         "Use when reading, merging, splitting, converting or OCR-ing PDFs.",
         "Inspect pages, extract text/tables, run OCR on scans, merge or split "
         "as asked, verify page counts."),
        ("word-docx-reporting", "Word DOCX Reporting",
         "Generate Word DOCX reports and letters, dokumen Word, laporan DOCX, "
         "templat surat, surat resmi, dokumen teks terformat.",
         "Use when producing formatted Word documents or reports.",
         "Apply the template styles, fill sections, generate tables and TOC, "
         "export DOCX and check pagination."),
        ("powerpoint-slide-deck", "PowerPoint Slide Deck",
         "Create PowerPoint PPTX slide decks, presentasi PowerPoint, salindia "
         "PPTX, dek presentasi, susun slide presentasi, materi rapat direksi.",
         "Use when building PowerPoint presentations or slide decks.",
         "Outline the deck, design master slides, fill content with visuals, "
         "export PPTX and rehearse timing."),
        ("excel-xlsx-automation", "Excel XLSX Automation",
         "Automate Excel XLSX workbooks, otomasi Excel, workbook XLSX, rumus, "
         "pivot, macro.",
         "Use when creating or automating Excel workbooks, formulas and pivots.",
         "Structure sheets, write formulas and pivots, add validation, export "
         "XLSX and recalc-check totals."),
        ("sop-process-checklist", "SOP Process Checklist",
         "Write SOPs and process checklists, prosedur tetap SOP, daftar periksa "
         "checklist, alur kerja operasional, panduan proses kerja.",
         "Use when documenting standard operating procedures or checklists.",
         "Map the process steps, assign owners, write the checklist with "
         "acceptance criteria, pilot it."),
        ("meeting-notes-action-items", "Meeting Notes Action Items",
         "Turn meeting notes into action items, notula rapat, risalah, daftar "
         "tugas, tenggat, ubah catatan rapat jadi daftar tugas, minutes of "
         "meeting.",
         "Use when converting meeting notes or transcripts into minutes and "
         "action items with deadlines.",
         "Extract decisions, list action items with owners and due dates, "
         "flag open questions, deliver the minutes."),
    ],
    "research-science": [
        ("literature-review-citation", "Literature Review Citation",
         "Run literature reviews with citations, tinjauan pustaka, sitasi, "
         "daftar pustaka, telaah jurnal, cari makalah, cari jurnal ilmiah, "
         "kumpulkan referensi penelitian, review literatur.",
         "Use for literature reviews, citation gathering and bibliography work.",
         "Search scholarly sources, screen by criteria, synthesize themes, "
         "format citations consistently."),
        ("academic-latex-paper", "Academic LaTeX Paper",
         "Write and format academic papers in LaTeX, penulisan makalah akademik "
         "LaTeX, bibtex, format konferensi, compile dokumen LaTeX.",
         "Use when drafting or formatting academic papers with LaTeX/BibTeX.",
         "Set the template, structure sections, manage BibTeX, compile and "
         "fix overfull boxes and references."),
        ("osint-fact-checking", "OSINT Fact Checking",
         "Run OSINT investigations and fact checks, penyelidikan sumber "
         "terbuka, cek fakta, jejak digital, WHOIS.",
         "Use for open-source intelligence, verifying claims and digital "
         "footprint checks.",
         "Collect public sources, cross-verify claims, document evidence "
         "chains, rate confidence."),
        ("bioinformatics-scientific-data", "Bioinformatics Scientific Data",
         "Analyze bioinformatics and scientific datasets, bioinformatika, "
         "data ilmiah, genomik, protein.",
         "Use for genomics/protein data analysis and scientific computing "
         "workflows.",
         "Validate inputs, run the analysis pipeline, check statistical "
         "assumptions, visualize results."),
        ("patent-policy-analysis", "Patent Policy Analysis",
         "Analyze patents and policy documents, analisis paten, analisis "
         "kebijakan, klaim, regulasi.",
         "Use when reviewing patent claims or analyzing policy/regulation text.",
         "Parse claims or clauses, map prior art or impacts, summarize risks "
         "and options with citations."),
        ("survey-design", "Survey Design",
         "Design surveys and questionnaires, desain survei, kuesioner, "
         "instrumen penelitian, sampling.",
         "Use when building survey instruments or questionnaire studies.",
         "Define constructs, write unbiased items, set scales and sampling, "
         "pilot and refine."),
    ],
    "software-devops": [
        ("backend-api-code-review", "Backend API Code Review",
         "Review backend API code and design, tinjauan kode backend, API REST, "
         "arsitektur layanan.",
         "Use for backend code reviews, API design checks and service "
         "architecture review.",
         "Read the diff, check contracts and error paths, flag security and "
         "performance issues, suggest fixes."),
        ("frontend-react-webapp", "Frontend React Web App",
         "Build frontend React web apps, aplikasi web frontend React, komponen "
         "UI interaktif, state management, routing SPA.",
         "Use when building or fixing React/HTML frontend applications.",
         "Scaffold components, wire state and routing, style responsively, "
         "test in the browser."),
        ("cicd-docker", "CI/CD Docker",
         "Set up CI/CD pipelines and Docker containers, CI CD, kontainer "
         "Docker, pipeline build, deploy.",
         "Use for Dockerfiles, compose stacks and CI/CD pipeline setup.",
         "Write the Dockerfile, build and scan the image, define pipeline "
         "stages, verify a clean deploy."),
        ("database-schema-optimization", "Database Schema Optimization",
         "Optimize database schemas and queries, optimasi skema basis data, "
         "indeks, query lambat, normalisasi.",
         "Use for schema design, index tuning and slow query optimization.",
         "Profile the workload, review indexes and plans, refactor schema, "
         "benchmark before/after."),
        ("security-audit", "Security Audit",
         "Run security audits and pentests, audit keamanan, uji penetrasi, "
         "kerentanan, OWASP.",
         "Use when auditing application or infrastructure security.",
         "Map the attack surface, run checks and scans, triage findings by "
         "severity, report remediations."),
        ("automated-testing-debugging", "Automated Testing Debugging",
         "Write automated tests and debug failures, pengujian otomatis, "
         "awakutu, uji unit, TDD.",
         "Use when adding tests, debugging failures or setting up TDD.",
         "Reproduce the bug, write the failing test, fix root cause, run the "
         "full suite green."),
    ],
}

_SKILL_TEMPLATE = """---
name: {slug}
description: "{description}"
version: 1.0.0
metadata:
  hermes:
    tags: [{pillar}, core-54]
    status: verified
---

# {name}

## When to Use

{when}

## Quick Reference

- Domain: {pillar}
- Trigger terms: {triggers}

## Procedure

{procedure}

## Verification

Confirm the deliverable matches the request before reporting done.
"""


def plant_core_corpus(skills_root: Path, overwrite: bool = False) -> int:
    """Tulis 54 skill inti (6/pilar). Return jumlah file ditulis."""
    written = 0
    for pillar, skills in CORE_SKILLS.items():
        assert len(skills) == 6, f"pilar {pillar} harus 6 skill"
        for slug, name, desc, when, proc in skills:
            d = skills_root / pillar / slug
            f = d / "SKILL.md"
            if f.exists() and not overwrite:
                continue
            d.mkdir(parents=True, exist_ok=True)
            triggers = ", ".join(desc.split(",")[:4])
            f.write_text(_SKILL_TEMPLATE.format(
                slug=slug, name=name, description=desc.replace('"', "'"),
                pillar=pillar, when=when, procedure=proc, triggers=triggers,
            ), encoding="utf-8")
            written += 1
    return written


if __name__ == "__main__":
    import os
    root = Path(os.environ.get("HERMES_HOME", Path.home() / ".hermes")) / "skills"
    n = plant_core_corpus(root, overwrite="--force" in __import__("sys").argv)
    total = sum(len(v) for v in CORE_SKILLS.values())
    print(f"Korpus inti: {total} skill (6 x {len(CORE_SKILLS)} pilar); ditulis {n} file ke {root}")