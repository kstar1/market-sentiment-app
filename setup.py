import os

# Define the folders to create
folders = [
    "data",
    "src",
    "src/data",
    "src/ui",
    "src/utils",
    "src/config",
    "assets"
]

# Define files and their starter content
files = {
    "streamlit_app.py": "",
    "requirements.txt": "streamlit\nyfinance\npandas\n",
    "README.md": "# Market Sentiment App\n\nAnalyze PUT/CALL option chains to understand market expectations.\n",
    ".gitignore": "__pycache__/\n*.pyc\n.env\n*.csv\n",
    "src/data/option_loader.py": "",
    "src/ui/filters_sidebar.py": "",
    "src/utils/helpers.py": "",
    "src/config/settings.py": "",
    "assets/styles.css": ""
}

# Create directories
for folder in folders:
    os.makedirs(folder, exist_ok=True)

# Create files
for path, content in files.items():
    with open(path, "w") as f:
        f.write(content)

print("✅ Project structure created.")
