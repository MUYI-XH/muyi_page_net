import os
import re
import requests
from flask import Flask, request, jsonify, send_file
from zipfile import ZipFile
from io import BytesIO
from urllib.parse import urljoin

app = Flask(__name__)

# 设置下载目录
DOWNLOAD_DIR = 'download_pdfs'
if not os.path.exists(DOWNLOAD_DIR):
    os.makedirs(DOWNLOAD_DIR)

def find_pdfs(url):
    try:
        response = requests.get(url)
        response.raise_for_status()
        
        # 使用正则表达式查找所有PDF链接
        pdf_links = re.findall(r'href=["\'](https?://[\w./-]+\.pdf["\']', response.text)
        
        # 去重和整理链接
        pdf_links = list(set(pdf_links))
        pdf_links = [urljoin(url, link.replace('href="', '').replace('href=\'', '').replace('"', '').replace('\'', '')) for link in pdf_links]
        
        return pdf_links
    except Exception as e:
        return str(e)

@app.route('/api/analyze', methods=['POST'])
def analyze():
    url = request.json.get('url')
    if not url:
        return jsonify({"error": "请输入有效的网址"}), 400
    
    pdf_links = find_pdfs(url)
    
    if isinstance(pdf_links, str):
        return jsonify({"error": pdf_links}), 500
    
    # 下载并保存PDF文件
    pdf_files = []
    for i, link in enumerate(pdf_links):
        try:
            response = requests.get(link, stream=True)
            response.raise_for_status()
            
            file_path = os.path.join(DOWNLOAD_DIR, f"file_{i}.pdf")
            with open(file_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
            
            pdf_files.append({
                "name": f"file_{i}.pdf",
                "size": os.path.getsize(file_path),
                "url": link
            })
        except Exception as e:
            print(f"Error downloading {link}: {e}")
    
    return jsonify({
        "count": len(pdf_files),
        "files": pdf_files
    })

@app.route('/api/download/<filename>')
def download_file(filename):
    return send_file(os.path.join(DOWNLOAD_DIR, filename), as_attachment=True)

@app.route('/api/download_all')
def download_all():
    # 创建内存中的ZIP文件
    zip_buffer = BytesIO()
    with ZipFile(zip_buffer, 'w') as zipf:
        for filename in os.listdir(DOWNLOAD_DIR):
            file_path = os.path.join(DOWNLOAD_DIR, filename)
            if os.path.isfile(file_path):
                zipf.write(file_path, arcname=filename)
    
    zip_buffer.seek(0)
    return send_file(zip_buffer, download_name='pdf_files.zip', as_attachment=True)

if __name__ == '__main__':
    app.run(debug=True)