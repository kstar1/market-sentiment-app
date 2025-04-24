#!/bin/bash

# Name of the final output file
OUTPUT_FILE="all_python_code.txt"

# Make sure we start clean
> $OUTPUT_FILE

# Recursively find all .py files, excluding venv/
find . -type f -name "*.py" -not -path "./venv/*" | while read filename; do
  echo "### File: $filename" >> $OUTPUT_FILE
  cat "$filename" >> $OUTPUT_FILE
  echo -e "\n\n" >> $OUTPUT_FILE
done

# Move the file to Downloads
mv $OUTPUT_FILE /Users/kshitijdutt/Downloads/

echo "✅ Python file contents saved to ~/Downloads/$OUTPUT_FILE"