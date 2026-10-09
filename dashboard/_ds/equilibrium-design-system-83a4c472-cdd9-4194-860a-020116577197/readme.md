# Equilibrium Design System

**Equilibrium | Business, Data & Communities** — consultora de investigación social y empresarial con presencia en América Latina y el Caribe (LAC). Clients span corporate decision-makers (Smart Fit, Entel, IKEA, Tigo…) and impact managers at multilaterals/NGOs (BID, UNICEF, PMA, OIM, ONU Mujeres, Banco Mundial…). Outputs: presentations, reports, one-pagers, landing pages, data visualisations, social carousels.

The system must read as **rigorous, clear, trustworthy, specialised and contemporary**. Hierarchy, readability, generous space and structured layouts beat decoration.

## Sources
- `uploads/Equilibrium_Manual de Marca_1.pdf` — *Manual de Marca, Identidad 2025* (13 pp.): colour palette (as duotone photo swatches), graphic resources (charts, KPI cards), applications (website mock-up, Instagram posts). Colour values in `tokens/colors.css` were read from the PDF's vector fills.
- `uploads/Lineamientos de marca.docx` — Brand Persona, verbal identity, tone guide, audiences.
- 9 screenshots of official decks (`uploads/Captura de pantalla 2026-09-29 *.png`): covers, index, section divider, context/stat slide, objectives, scope, chart + quote, closing.
- Official logo SVGs (principal, con tagline, isotipo — azul & blanco) and the full **Geologica** family (TTF).
- No codebase, Figma or live website was provided.

## Index
- `styles.css` — entry point (imports only) → `tokens/fonts.css, colors.css, typography.css, spacing.css, effects.css, base.css`
- `fonts/` — Geologica 100–900 + italics
- `assets/logos/` — 6 official SVG lockups · `assets/photos/` — manual duotone swatches + website hero photo
- `guidelines/` — foundation specimen cards (Colors, Type, Spacing, Brand)
- `components/` — React primitives (below), one `*.card.html` per folder
- `ui_kits/website/` — click-through institutional website
- `slides/` — 8 deck slide types at 1920×1080 (static HTML)
- `SKILL.md` — Agent-Skill entry
- `research/` — extracted manual images used during analysis (not shipped)

## Components
- **core:** Button, IconButton, Icon, Tag
- **forms:** Input (+ textarea), Select, Checkbox, Radio, Switch
- **content:** Card, Quote, NumberedList, SectionHeader
- **data:** StatFigure, BarChart, ColumnChart
- **navigation:** NavBar, Tabs
- **feedback:** Dialog
- **media:** DuotonePhoto
- **brand:** Logo, Isotipo

**Intentional additions** (no component inventory existed — the set was authored from the brand manual + decks): Icon (Lucide wrapper), DuotonePhoto (brand photo treatment as code), SectionHeader / NumberedList / Quote / StatFigure / BarChart (lifted from deck patterns). Toast and Tooltip were not built — no brand reference for them.

## Slides
TitleSlide, IndexSlide, SectionSlide, ContextSlide, ScopeSlide, ChartQuoteSlide, BigStatementSlide, ClosingSlide.

---

## CONTENT FUNDAMENTALS
**Language:** Spanish (LAC neutral) by default; English only for the tagline *Business, Data & Communities*.

**Voice:** "Somos el Sabio que explora el terreno para crear soluciones y las comunica con la claridad de una Persona Común." Archetypes: Sabio 60% (core), Explorador 15%, Creador 15%, Persona Común 10%. Profile INTJ — analyse first, then speak.

**Principio rector:** *Comprendemos antes de recomendar. Generamos evidencia para convertirla en decisiones.*

**Attributes (is… without being…):** Rigurosa / no rígida · Ágil / no improvisada · Experta / no arrogante · Empática / no complaciente · Innovadora / no de moda.

**Rules:**
- Lead with the main idea, then context.
- Explain rather than impress; define technical terms when they block understanding.
- Direct sentences, active verbs.
- Separate what we know from what we interpret; never claim causality the data doesn't support.
- Never isolated numbers — always base (n), year, comparison. e.g. "73.5% residen en áreas urbanas (3.7 M)".
- No superlatives or unverifiable leadership claims ("los mejores", "líderes del mercado").
- When mentioning AI/new methods, say what it does and why it adds value.

**Person:** "nosotros" for Equilibrium (Somos, Realizamos, Contamos con…); address the reader as **tú** in digital/social ("Cuéntanos", "Conversemos"), neutral impersonal in reports.

**Casing:** Sentence case for slide titles and headlines (*Objetivos*, *Principales hallazgos*). ALL CAPS reserved for section dividers and cover kickers (*EL PROYECTO*, *SESIÓN CREATIVA 3*, *CONTEXTO*) and hashtag kickers (*#NARRATIVAS*). Questions use opening ¿.

**Numbers:** Spanish decimal comma in reports/charts (71,8%), space before % optional (manual uses "23 %"); decks also show "30.1%" — pick one per document and stay consistent.

**Tone by context:** report launch → analítico y didáctico; job post → inspirador; reply to user → servicial y resolutivo; milestone → orgulloso y agradecido; fieldwork → informativo y humano; commercial → consultivo y directo.

**Emoji:** not used. **Exclamation marks:** avoid.

Example copy: "Somos especialistas en consultoría estratégica para optimizar decisiones y potenciar resultados." · "Información precisa = Buenas decisiones" · "Una celebración local, una conexión regional."

---

## VISUAL FOUNDATIONS
**Colour.** Navy `#030F50` is the brand: logo, headings, key figures, dark grounds. Paper `#F7FAF2` (warm off-white, never pure white for page grounds) is the default background. Secondary palette from the manual: coral `#F7966B` (most used accent), teal `#7CCCBF`, yellow `#F4B21B`, periwinkle `#788EC7`, blue `#1A55A6`, cyan `#14B1E7` (charts only). Peach `#F6C8AE` appears as a coral tint on covers. Body text grey `#595959`. Grey track `#EEEEEE` for bars and table rows. One accent per slide/section; navy + paper carry most of the area. No error-red exists in the brand — form errors use a coral underline + bold navy message.

**Type.** Geologica only. Bold 700 for titles/figures (tight 1.05–1.2), Medium 500 for large statements and subtitles (e.g. coral subtitle on covers, teal panel on the website), Regular 400 for body (1.5), Italic for testimonials and base notes ("n = 000 encuestas"). Slides at 1920: title 56–64px, body 30px, figures 60px+.

**Backgrounds.** (1) flat paper; (2) flat colour fields (coral sidebars, teal panels, navy blocks); (3) **duotone photography** — grayscale photo mapped navy↔periwinkle, navy↔teal, or coral mono, usually with a **halftone dot screen and paper grain**; (4) palette-only gradients with grain (extension, per brief) for statement slides and CTAs. No pattern wallpapers, no illustrations.

**Isotipo motif ("arc").** The large coral shapes on covers, dividers and closings are the **official isotipo itself** — not a ring or circle. Its asymmetric geometry (rounded form, straight section, pointed tip, varying stroke width) must never be redrawn. Use `<Isotipo>` (or inline the official paths with `fill="currentColor"` + `.eq-isotipo`): change only scale, colour (coral, peach, teal, navy, paper), position and how much the frame crops it. No rotation, stretching or outlines. One per layout.

**Corners.** Square by default — buttons, inputs, cards, bars, images. Rounding is an **accent** on a single corner or edge: the cover's paper footer (top-left ~64px), header-tab band (bottom-left), index number spine (left side), date pill tag. Never round every corner of every card.

**Lines.** 2px solid navy for header underlines, stat dividers and quote rules; 2px **dotted** navy for list/row separators. Quote rule carries a V speech-notch.

**Header tab.** Navy square with white isotipo + full-width colour band (coral / periwinkle) with bottom-left radius; or the lighter "rule" header (isotipo + title + navy underline).

**Cards.** Flat colour blocks or white with a 1px inset hairline; no shadow at rest; shadow-1 only on hover for clickable cards. Image on top, square.

**Shadows / blur / transparency.** Essentially none. Transparency only for duotone multiply/lighten layers and the navy modal scrim. No glassmorphism.

**Imagery vibe.** Real people of LAC, fieldwork, cities and communities; candid not staged; cool navy/periwinkle or warm coral monotones; visible grain. Avoid generic stock handshakes and abstract tech imagery.

**Data viz.** Horizontal bars with square ends on a grey track, label + value inside/right of bar, sorted descending; single series colour (coral or navy); base n in italic below; source always. Series order: navy, coral, teal, blue, yellow, periwinkle.

**Layout.** Generous margins (120px on 1920 slides), left-aligned text, max ~6 bullets per slide, page number bottom-right. Web: 1200px container, split bands (50/50 colour + text), sticky navy nav.

**Motion.** Minimal: 120–220ms colour transitions, ease-out; ghost-button arrow nudges 3px; card image scales 1.02 on hover. No bounces.

**Hover / press.** Buttons swap fill (navy→blue, coral→navy, outline→filled). Links underline, hover to navy. Press: 1px downward nudge. Focus: cyan ring.

---

## ICONOGRAPHY
The manual references iconography but **no icon files were supplied**. Decks show simple solid/line pictograms (target, monitor) in coral or navy, and social icons (LinkedIn, Instagram, X, globe) in white. **Substitution:** [Lucide](https://lucide.dev) via CDN (`lucide-static@0.460.0`), 2px stroke, rendered through `<Icon name="…">` as a CSS mask so it takes any brand colour. Use navy on paper, paper on navy, coral as a single accent. No emoji, no unicode glyph icons. Replace with an official set when available.

## Logo
Use only the 6 supplied SVGs (`assets/logos/`): principal, con tagline, isotipo — each in azul (navy) and blanco. Tagline version for covers/closings; isotipo for header tabs and avatars. Decks occasionally tint the isotipo coral in light "rule" headers — keep that the only recolour.
