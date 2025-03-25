import os
import time
from datetime import datetime
import arxiv
from tqdm import tqdm
import requests
import re

class ArxivDownloader:
    def __init__(self, save_dir="./data/downloads"):
        """
        ArXiv'den makale indirmek için bir sınıf.
        
        Args:
            save_dir (str): İndirilen makalelerin kaydedileceği dizin.
        """
        self.save_dir = save_dir
        
        if not os.path.exists(save_dir):
            os.makedirs(save_dir)
        
        # ArXiv client oluşturma
        self.client = arxiv.Client()
    
    def search_papers(self, query_keyword, start_year=2005, sort_by="submittedDate", sort_order="descending", offset=0, per_page=20):
        """
        ArXiv'de makale araması yapar.
        
        Args:
            query_keyword (str): Arama kelimesi
            start_year (int): Başlangıç yılı
            sort_by (str): Sıralama kriteri ("submittedDate", "relevance")
            sort_order (str): Sıralama yönü ("ascending", "descending")
            offset (int): Başlangıç indeksi (sayfalama için)
            per_page (int): Sayfa başına gösterilecek makale sayısı
            
        Returns:
            tuple: (toplam_makale_sayısı, bulunan_makaleler)
        """
        try:
            # Sıralama kriterini ayarla
            if sort_by == "submittedDate":
                sort_criterion = arxiv.SortCriterion.SubmittedDate
            else:  # relevance
                sort_criterion = arxiv.SortCriterion.Relevance
                
            # Sıralama yönünü ayarla
            if sort_order == "descending":
                sort_order = arxiv.SortOrder.Descending
            else:
                sort_order = arxiv.SortOrder.Ascending
            
            # ArXiv API'sini kullanarak arama yap
            search = arxiv.Search(
                query=query_keyword,
                max_results=per_page,  # Sadece bir sayfa kadar sonuç al
                sort_by=sort_criterion,
                sort_order=sort_order,
                offset=offset  # Sayfalama için offset kullan
            )
            
            papers = []
            total_count = 0
            
            # Sonuçları topla
            for result in search.results():
                try:
                    # Makale bilgilerini hazırla
                    paper = {
                        "title": result.title,
                        "authors": [author.name for author in result.authors],
                        "summary": result.summary,
                        "pdf_url": result.pdf_url,
                        "arxiv_id": result.entry_id.split("/")[-1],
                        "published": result.published,
                        "categories": result.categories,
                        "downloaded": False,
                        "local_path": None
                    }
                    
                    # Yıl kontrolü
                    if paper["published"].year >= start_year:
                        papers.append(paper)
                        total_count += 1
                    
                except Exception as e:
                    print(f"Makale işlenirken hata: {e}")
                    continue
                
                # API limitleri için bekleme
                time.sleep(0.5)
            
            print(f"Sayfa {offset//per_page + 1} için {len(papers)} makale bulundu.")
            
            # Eğer hiç sonuç bulunamadıysa, arama sorgusunu basitleştir ve tekrar dene
            if not papers:
                print("İlk denemede sonuç bulunamadı, sorguyu basitleştirip tekrar deneniyor...")
                # Sorguyu basitleştir (ilk kelimeyi al)
                simple_query = query_keyword.split()[0]
                search = arxiv.Search(
                    query=simple_query,
                    max_results=per_page,
                    sort_by=sort_criterion,
                    sort_order=sort_order,
                    offset=offset
                )
                
                for result in search.results():
                    try:
                        paper = {
                            "title": result.title,
                            "authors": [author.name for author in result.authors],
                            "summary": result.summary,
                            "pdf_url": result.pdf_url,
                            "arxiv_id": result.entry_id.split("/")[-1],
                            "published": result.published,
                            "categories": result.categories,
                            "downloaded": False,
                            "local_path": None
                        }
                        
                        if paper["published"].year >= start_year:
                            papers.append(paper)
                            total_count += 1
                        
                    except Exception as e:
                        print(f"Makale işlenirken hata: {e}")
                        continue
                    
                    time.sleep(0.5)
                
                print(f"Basitleştirilmiş sorgu ile {len(papers)} makale bulundu.")
            
            return total_count, papers
            
        except Exception as e:
            print(f"Arama hatası: {e}")
            print(f"Hata detayı: {str(e)}")
            return 0, []
    
    def download_paper(self, paper):
        """
        Makaleyi indirir ve kaydeder.
        
        Args:
            paper (dict): Makale bilgileri
            
        Returns:
            str: İndirilen dosyanın yolu
        """
        try:
            # Dosya adını oluştur
            safe_title = re.sub(r'[<>:"/\\|?*]', '_', paper["title"])
            safe_title = safe_title[:100]  # Dosya adı uzunluğunu sınırla
            file_name = f"{safe_title}_{paper['arxiv_id']}.pdf"
            file_path = os.path.join(self.save_dir, file_name)
            
            # Dosya zaten varsa tekrar indirme
            if os.path.exists(file_path):
                return file_path
            
            # PDF'i indir
            response = requests.get(paper["pdf_url"])
            if response.status_code == 200:
                with open(file_path, "wb") as f:
                    f.write(response.content)
                return file_path
            else:
                print(f"İndirme hatası: {response.status_code}")
                return None
                
        except Exception as e:
            print(f"İndirme hatası: {e}")
            return None
    
    def download_papers_by_criteria(self, query_keyword, start_year, end_year=None, max_results=20):
        """
        Belirtilen kriterlere göre makaleleri arar ve indirir.
        
        Args:
            query_keyword (str): Aramak için kullanılacak anahtar kelime(ler).
            start_year (int): Başlangıç yılı.
            end_year (int, optional): Bitiş yılı. None ise günümüz.
            max_results (int): İndirilecek maksimum makale sayısı.
            
        Returns:
            list: İndirilen makale bilgilerinin listesi.
        """
        # Önce ara
        papers = self.search_papers(query_keyword, start_year)
        downloaded = []
        
        # İndir
        for paper in tqdm(papers, desc="Makaleler indiriliyor"):
            if paper.get("downloaded"):
                downloaded.append(paper)
                continue
                
            file_path = self.download_paper(paper)
            if file_path:
                paper["downloaded"] = True
                paper["local_path"] = file_path
                downloaded.append(paper)
            
            # ArXiv API limitlerini aşmamak için kısa bir bekleme
            time.sleep(3)
        
        print(f"Toplam {len(downloaded)} makale indirildi.")
        return downloaded