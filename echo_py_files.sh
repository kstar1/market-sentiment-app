#!/bin/bash

# Name of the final output file
OUTPUT_FILE="all_python_code.txt"

# Make sure we start clean
> $OUTPUT_FILE

# Add streamlit_app.py
echo "=== ./streamlit_app.py ===" >> "$OUTPUT_FILE"
cat ./streamlit_app.py >> "$OUTPUT_FILE"
echo -e "\n\n" >> "$OUTPUT_FILE"

# Add src/data/*.py
for file in ./src/data/*.py; do
    echo "=== $file ===" >> "$OUTPUT_FILE"
    cat "$file" >> "$OUTPUT_FILE"
    echo -e "\n\n" >> "$OUTPUT_FILE"
done

# Add src/insights/*.py
for file in ./src/insights/*.py; do
    echo "=== $file ===" >> "$OUTPUT_FILE"
    cat "$file" >> "$OUTPUT_FILE"
    echo -e "\n\n" >> "$OUTPUT_FILE"
done

# Add src/ui/*.py
for file in ./src/ui/*.py; do
    echo "=== $file ===" >> "$OUTPUT_FILE"
    cat "$file" >> "$OUTPUT_FILE"
    echo -e "\n\n" >> "$OUTPUT_FILE"
done

# Add src/utils/*.py
for file in ./src/utils/*.py; do
    echo "=== $file ===" >> "$OUTPUT_FILE"
    cat "$file" >> "$OUTPUT_FILE"
    echo -e "\n\n" >> "$OUTPUT_FILE"
done

# Add src/config/*.py
for file in ./src/config/*.py; do
    echo "=== $file ===" >> "$OUTPUT_FILE"
    cat "$file" >> "$OUTPUT_FILE"
    echo -e "\n\n" >> "$OUTPUT_FILE"
done

for file in ./src/config/*.json; do
    echo "=== $file ===" >> "$OUTPUT_FILE"
    cat "$file" >> "$OUTPUT_FILE"
    echo -e "\n\n" >> "$OUTPUT_FILE"
done

# Move the file to Downloads
mv $OUTPUT_FILE /Users/kshitijdutt/Downloads/

echo "✅ Python file contents saved to ~/Downloads/$OUTPUT_FILE"