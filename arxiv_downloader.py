import os
import time
from datetime import datetime
import arxiv
from tqdm import tqdm

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
    
    def search_papers(self, query_keyword, start_year, end_year=None, max_results=20):
        """
        ArXiv'de makaleleri arar, henüz indirmez.
        
        Args:
            query_keyword (str): Aramak için kullanılacak anahtar kelime(ler).
            start_year (int): Başlangıç yılı.
            end_year (int, optional): Bitiş yılı. None ise günümüz.
            max_results (int): İndirilecek maksimum makale sayısı.
            
        Returns:
            list: Bulunan makale bilgilerinin listesi.
        """
        if end_year is None:
            end_year = datetime.now().year
            
        # Sorguyu oluştur
        query = f"ti:{query_keyword} AND cat:cs.* AND submittedDate:[{start_year} TO {end_year}]"
        
        print(f"ArXiv'de '{query}' araması yapılıyor...")
        
        # ArXiv API ile arama yapma
        search = arxiv.Search(
            query=query,
            max_results=max_results,
            sort_by=arxiv.SortCriterion.SubmittedDate
        )
        
        # Sonuçları client ile al
        results = self.client.results(search)
        papers = []
        
        # İlerleme için sonuçları listeye çevirelim
        try:
            results_list = list(results)
            print(f"Toplam {len(results_list)} makale bulundu.")
        except Exception as e:
            print(f"Sonuçları listeleme hatası: {e}")
            return papers
        
        # Makaleleri listele
        for result in results_list:
            # Yayın tarihini kontrol et
            if result.published.year < start_year or result.published.year > end_year:
                continue
                
            paper_info = {
                "title": result.title,
                "authors": [author.name for author in result.authors],
                "summary": result.summary,
                "published": result.published,
                "pdf_url": result.pdf_url,
                "arxiv_id": result.entry_id.split('/')[-1],
                "categories": result.categories,
                "query_keyword": query_keyword,
                "downloaded": False
            }
            
            # Dosya zaten indirilmiş mi kontrol et
            file_path = os.path.join(self.save_dir, f"{paper_info['arxiv_id']}.pdf")
            if os.path.exists(file_path):
                paper_info["downloaded"] = True
                paper_info["local_path"] = file_path
                
            papers.append(paper_info)
            
            # API limitlerini aşmamak için kısa bir bekleme
            time.sleep(0.5)
        
        print(f"Toplam {len(papers)} makale listelendi.")
        return papers
    
    def download_paper(self, paper):
        """
        Belirli bir makaleyi indirir.
        
        Args:
            paper (dict): İndirilecek makale bilgileri.
            
        Returns:
            str: İndirilen dosyanın yolu veya None (hata durumunda).
        """
        try:
            # Dosya zaten var mı kontrol et
            arxiv_id = paper["arxiv_id"]
            file_path = os.path.join(self.save_dir, f"{arxiv_id}.pdf")
            
            if os.path.exists(file_path):
                print(f"Dosya zaten mevcut: {file_path}")
                return file_path
            
            # ArXiv ID'ye göre makaleyi al ve indir
            search = arxiv.Search(id_list=[arxiv_id])
            result = next(self.client.results(search))
            
            result.download_pdf(dirpath=self.save_dir, filename=f"{arxiv_id}.pdf")
            print(f"İndirildi: {paper['title']}")
            
            return file_path
        
        except Exception as e:
            print(f"İndirme hatası ({paper['title']}): {e}")
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
        papers = self.search_papers(query_keyword, start_year, end_year, max_results)
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