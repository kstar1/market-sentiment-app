import re

def sanitize_insights(insights: list[str]) -> list[str]:
    cleaned = []
    for insight in insights:
        text = insight.strip()

        # Standardize dollar references
        text = re.sub(r'\$(\d+)', r'$\1', text)  # ensure dollar signs stick

        # Normalize percentages: "502.0%" → "502%"
        text = re.sub(r'(\d+)\.0%', r'\1%', text)

        # Remove filler phrases
        text = re.sub(r"\b(might indicate|possibly|suggests that|could be seen as)\b", "suggests", text, flags=re.IGNORECASE)

        # Capitalize first letter
        text = text[0].upper() + text[1:]

        # Avoid double spaces
        text = re.sub(r'\s{2,}', ' ', text)

        cleaned.append(text)

    return cleaned
