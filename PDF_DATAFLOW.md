# PDF Generation Data Flow

This document explains how user input flows from the API into the final generated PDF.

## 1. Input Processing
- **Entry Point**: `POST /api/create-lead-magnet/`
- **Data**: Topic, Audience, Pain Points, Target Outcome, CTA.
- **Service**: `views.py` initiates a background job.

## 2. AI Content Generation (Groq)
The `GroqClient` uses a multi-layered approach to ensure context-specific content:
- **Layer 1 (Analysis)**: Deep analysis of the topic and audience.
- **Layer 2 (Framework)**: Generates context-specific section titles (e.g., "Sustainable Framework") and uppercase kickers (e.g., "STRATEGY") for all 11 pages.
- **Layer 3 (Content)**: Generates the actual body text, statistics, and checklists for each section based on the Layer 2 plan.

## 3. Variable Mapping
The `map_to_template_vars` function flattens the AI response and firm profile into a single context dictionary:
- **Dynamic Fallbacks**: If data is missing, the system uses topic-derived fallbacks (e.g., "Quantum Notice" instead of "Legal Notice").
- **Dynamic Labels**: Labels like "Company", "Email", and "Phone" are passed as variables, allowing for future localization or customization.
- **Layout Variables**: Logic maps AI-extracted components (e.g., `stat1Value`) to the specific CSS classes in the template.

## 4. Rendering (DocRaptor)
- **Engine**: Jinja2 renders `Template.html` with the context dictionary.
- **Safety**: The `| safe` filter is applied to AI-generated HTML to ensure formatting (bold, lists) is preserved.
- **CSS**: The template uses `@page` rules and print-media CSS for high-fidelity A4 output.

## 5. Fallback Strategy
- **Prioritize User Data**: Always uses firm profile first.
- **Contextual Fallbacks**: If firm name is missing, it falls back to `{Topic} Experts`.
- **Structural Cleanup**: A `clean_rendered_html` post-process removes any remaining empty tags or unresolved placeholders before submission to the PDF engine.
