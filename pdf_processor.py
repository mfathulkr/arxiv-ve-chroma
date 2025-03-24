import os
import re
import PyPDF2
from datetime import datetime

class PDFProcessor:
    def __init__(self, pdf_path):
        """
        PDF dosyasını işlemek için bir sınıf.
        
        Args:
            pdf_path (str): PDF dosyasının yolu.
        """
        self.pdf_path = pdf_path
    
    def extract_text(self):
        """
        PDF dosyasından metin çıkarır.
        
        Returns:
            str: Çıkarılan metin, başarısızsa boş string.
        """
        try:
            text = ""
            with open(self.pdf_path, 'rb') as file:
                reader = PyPDF2.PdfReader(file)
                for page_num in range(len(reader.pages)):
                    page = reader.pages[page_num]
                    text += page.extract_text() + "\n"
            return text
        except Exception as e:
            print(f"PDF metin çıkarma hatası ({self.pdf_path}): {e}")
            return ""
    
    def extract_metadata(self):
        """
        PDF dosyasından metadata çıkarmaya çalışır.
        
        Returns:
            dict: Metadata bilgileri.
        """
        try:
            metadata = {}
            
            # PDF'den bilgileri çıkar
            with open(self.pdf_path, 'rb') as file:
                reader = PyPDF2.PdfReader(file)
                info = reader.metadata
                
                if info:
                    metadata["title"] = info.get('/Title', None)
                    metadata["authors"] = info.get('/Author', None)
                    metadata["created"] = info.get('/CreationDate', None)
            
            # Başlık bulunamadıysa dosya adını kullan
            if not metadata.get("title"):
                file_name = os.path.basename(self.pdf_path)
                metadata["title"] = file_name.replace(".pdf", "")
            
            # İlk sayfadan içerik çıkar ve başlık/yazar tahmin et
            if not metadata.get("authors"):
                text = self.extract_text()
                if text:
                    first_page = text.split('\n\n')[:10]
                    joined_first_page = "\n".join(first_page)
                    
                    # Yazar bilgisini ara (bazı genel kalıplar)
                    author_patterns = [
                        r"(?:Author|Authors|By)[s]?:?\s*(.*?)(?:\n|$)",
                        r"^(.*?)\n.*?(?:University|Institute|College|Laboratory|Department)",
                    ]
                    
                    for pattern in author_patterns:
                        author_match = re.search(pattern, joined_first_page, re.IGNORECASE | re.MULTILINE)
                        if author_match:
                            metadata["authors"] = author_match.group(1).strip()
                            break
            
            # Tarih bilgisi yoksa şimdiyi kullan
            if not metadata.get("created"):
                metadata["created"] = datetime.now().strftime("%Y-%m-%d")
            
            # ArXiv ID'si çıkarmayı dene (dosya adı genelde ID'dir)
            file_name = os.path.basename(self.pdf_path).replace(".pdf", "")
            if re.match(r"\d{4}\.\d{4,5}", file_name):  # ArXiv ID formatı
                metadata["arxiv_id"] = file_name
                metadata["source"] = "arxiv"
            else:
                metadata["source"] = "manual_upload"
            
            return metadata
        
        except Exception as e:
            print(f"Metadata çıkarma hatası ({self.pdf_path}): {e}")
            file_name = os.path.basename(self.pdf_path)
            return {
                "title": file_name.replace(".pdf", ""),
                "authors": "",
                "created": datetime.now().strftime("%Y-%m-%d"),
                "source": "manual_upload"
            }
    
    def get_file_info(self):
        """
        PDF dosyasının temel bilgilerini döndürür.
        
        Returns:
            dict: Dosya bilgileri.
        """
        try:
            file_stats = os.stat(self.pdf_path)
            file_name = os.path.basename(self.pdf_path)
            
            return {
                "file_name": file_name,
                "file_path": self.pdf_path,
                "file_size": file_stats.st_size,
                "created": datetime.fromtimestamp(file_stats.st_ctime).strftime("%Y-%m-%d %H:%M:%S"),
                "modified": datetime.fromtimestamp(file_stats.st_mtime).strftime("%Y-%m-%d %H:%M:%S")
            }
        except Exception as e:
            print(f"Dosya bilgisi alma hatası: {e}")
            return {
                "file_name": os.path.basename(self.pdf_path),
                "file_path": self.pdf_path,
                "file_size": 0,
                "created": "",
                "modified": ""
            }