# app/utils.py
import os

def read_markdown_file(filename: str) -> str:
    """
    Reads content from a markdown file in the assets/markdown directory.
    This function robustly finds the file regardless of where the script is run.
    """
    try:
        # Get the directory where this utils.py file is located
        base_dir = os.path.dirname(os.path.abspath(__file__))
        # Construct the full path to the markdown file
        file_path = os.path.join(base_dir, '..', 'assets', 'markdown', filename)
        
        with open(file_path, 'r', encoding='utf-8') as f:
            return f.read()
    except FileNotFoundError:
        return f"### Error\nEl archivo de contenido `{filename}` no fue encontrado."
    except Exception as e:
        return f"### Error\nOcurrió un error al leer el archivo: {e}"