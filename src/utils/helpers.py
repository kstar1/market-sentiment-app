import re
import streamlit as st
import json

def sanitize_insights(insights: list[str]) -> list[str]:
    cleaned = []
    for insight in insights:
        text = insight.strip()

        # Add space between number and text (e.g., 260strike → 260 strike)
        text = re.sub(r"(?<=\d)([A-Za-z])", r" \1", text)

        # Standardize dollar signs
        text = re.sub(r'\$(\d+)', r'$\1', text)

        # Normalize percentages: 502.0% → 502%
        text = re.sub(r'(\d+)\.0%', r'\1%', text)

        # Fix punctuation spacing
        text = text.replace(".,", ". ").replace("..", ".").replace(",,", ",")

        # Remove vague language
        text = re.sub(r"\b(might indicate|possibly|suggests that|could be seen as)\b", "suggests", text, flags=re.IGNORECASE)

        # Capitalize first letter
        if text:
            text = text[0].upper() + text[1:]

        cleaned.append(text)
    return cleaned

def render_task_output(insight: dict, show_raw=False):
    for key, val in insight.items():
        if key in ["task", "raw_response", "prepared_data"]:
            continue  # <-- SKIP prepared_data now

        if isinstance(val, list):
            if not val:
                continue  # Skip if empty list
            if all(isinstance(x, dict) for x in val):
                for i, row in enumerate(val, 1):
                    formatted = ", ".join(f"**{k.replace('_', ' ').title()}**: {str(v).replace('$', r'\$')}" for k, v in row.items())
                    st.markdown(f"{i}. {formatted}")
            else:
                for i, item in enumerate(val, 1):
                    clean = str(item).replace("$", r"\$")
                    st.markdown(f"- {clean}")

        elif isinstance(val, dict):
            st.markdown("**Details:**")
            for subk, subv in val.items():
                st.markdown(f"- **{subk.replace('_', ' ').title()}**: {str(subv).replace('$', r'\$')}")

        else:
            st.markdown(f"**{key.replace('_', ' ').title()}:** {str(val).replace('$', r'\$')}")

    # Raw response shown only if checkbox selected
    if show_raw and "raw_response" in insight:
        st.markdown("**Raw GPT JSON:**")
        st.code(insight["raw_response"], language="json")

    if show_raw and "prepared_data" in insight:
        st.markdown("**Numerical Prepared Data:**")
        st.json(insight["prepared_data"])

def safe_json_dumps(obj, **kwargs):
    return json.dumps(obj, default=lambda o: o.item() if hasattr(o, 'item') else str(o), **kwargs)
