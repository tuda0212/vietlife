import zipfile
import xml.etree.ElementTree as ET

def read_docx(file_path):
    # docx files are zip files containing xml
    try:
        with zipfile.ZipFile(file_path) as z:
            xml_content = z.read('word/document.xml')
            root = ET.fromstring(xml_content)
            
            # Namespace map
            ns = {'w': 'http://schemas.openxmlformats.org/wordprocessingml/2006/main'}
            
            text_runs = []
            for paragraph in root.findall('.//w:p', ns):
                p_text = []
                for run in paragraph.findall('.//w:t', ns):
                    p_text.append(run.text)
                if p_text:
                    text_runs.append("".join(p_text))
            return "\n".join(text_runs)
    except Exception as e:
        return f"Error reading docx: {e}"

if __name__ == "__main__":
    text = read_docx("tong_ket_du_an_migration.docx")
    print(text[:10000]) # Print first 10k chars
