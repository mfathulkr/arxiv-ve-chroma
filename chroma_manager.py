import os
import chromadb
import hashlib
from datetime import datetime
from pdf_processor import PDFProcessor
import re

class ChromaManager:
    def __init__(self, db_path="./chroma_data"):
        """
        ChromaDB veritabanı yöneticisi.
        
        Args:
            db_path (str): Veritabanı dizini.
        """
        self.db_path = db_path
        self.collection_name = "knowledge"  # Tek bir sabit koleksiyon adı
        
        if not os.path.exists(db_path):
            os.makedirs(db_path)
        
        try:
            # Chroma istemcisini başlat
            self.client = chromadb.PersistentClient(path=db_path)
            
            # Koleksiyonu oluştur veya mevcut olanı al
            try:
                self.collection = self.client.get_collection(name=self.collection_name)
                print(f"Mevcut koleksiyon alındı: {self.collection_name}")
            except:
                self.collection = self.client.create_collection(name=self.collection_name)
                print(f"Yeni koleksiyon oluşturuldu: {self.collection_name}")
        except Exception as e:
            print(f"ChromaDB başlatma hatası: {e}")
            # Hata durumunda varsayılan ayarlarla tekrar dene
            self.client = chromadb.Client()
            try:
                self.collection = self.client.get_collection(name=self.collection_name)
            except:
                self.collection = self.client.create_collection(name=self.collection_name)
    
    def _chunk_text(self, text, max_chunk_size):
        """
        Metni belirtilen boyutta parçalara böler.
        
        Args:
            text (str): Bölünecek metin
            max_chunk_size (int): Her parçanın maksimum karakter sayısı
            
        Returns:
            list: Metin parçalarının listesi
        """
        chunks = []
        current_chunk = []
        current_size = 0
        
        # Metni cümlelere böl
        sentences = re.split(r'(?<=[.!?])\s+', text)
        
        for sentence in sentences:
            sentence_size = len(sentence)
            
            # Eğer tek bir cümle maksimum boyuttan büyükse, kelimelere böl
            if sentence_size > max_chunk_size:
                words = sentence.split()
                current_word_chunk = []
                current_word_size = 0
                
                for word in words:
                    word_size = len(word) + 1  # +1 for space
                    if current_word_size + word_size > max_chunk_size:
                        chunks.append(' '.join(current_word_chunk))
                        current_word_chunk = [word]
                        current_word_size = word_size
                    else:
                        current_word_chunk.append(word)
                        current_word_size += word_size
                
                if current_word_chunk:
                    chunks.append(' '.join(current_word_chunk))
                continue
            
            # Normal cümle işleme
            if current_size + sentence_size > max_chunk_size:
                chunks.append(' '.join(current_chunk))
                current_chunk = [sentence]
                current_size = sentence_size
            else:
                current_chunk.append(sentence)
                current_size += sentence_size
        
        # Son parçayı ekle
        if current_chunk:
            chunks.append(' '.join(current_chunk))
        
        return chunks
    
    def get_collections(self):
        """
        Mevcut koleksiyonları döndürür - ancak artık hep tek koleksiyon kullanıyoruz.
        
        Returns:
            list: Koleksiyon adlarının listesi.
        """
        return [self.collection_name]
    
    def create_collection(self, name=None):
        """
        Koleksiyonu döndürür - name parametresi göz ardı edilir,
        her zaman varsayılan knowledge koleksiyonu kullanılır.
        
        Returns:
            chromadb.Collection: Koleksiyon.
        """
        return self.collection
    
    def add_pdf(self, pdf_path, metadata=None, collection_name=None):
        """
        PDF'i veritabanına ekler.
        
        Args:
            pdf_path (str): PDF dosya yolu
            metadata (dict, optional): Ek metadata bilgileri
            collection_name (str, optional): Kullanılmıyor, geriye dönük uyumluluk için
            
        Returns:
            dict: İşlem sonucu
        """
        try:
            # PDF işleyici başlat
            processor = PDFProcessor(pdf_path)
            
            # Metin çıkar
            text = processor.extract_text()
            if not text or len(text) < 100:
                return {
                    "success": False, 
                    "error": "PDF'den yeterli metin çıkarılamadı.", 
                    "id": None
                }
            
            # Metadata hazırla
            pdf_metadata = processor.extract_metadata()
            if metadata:
                pdf_metadata.update(metadata)  # Kullanıcının verdiği metadatayı ekle
            
            # Dosya içeriğinin hash değeri
            content_hash = hashlib.md5(text.encode()).hexdigest()
            
            # Sadece gerekli ve basit metadata alanlarını al
            simple_metadata = {
                "title": str(pdf_metadata.get("title", ""))[:100],
                "author": str(pdf_metadata.get("authors", ""))[:100],
                "source": str(pdf_metadata.get("source", ""))[:20],
                "hash": content_hash,
                "file": os.path.basename(pdf_path)
            }
            
            # Benzersiz ID oluştur
            if "arxiv_id" in pdf_metadata:
                doc_id = pdf_metadata["arxiv_id"]
            else:
                file_name = os.path.basename(pdf_path).replace(".pdf", "")
                doc_id = f"{file_name}_{content_hash[:8]}"
            
            # Duplikasyon kontrolü (hash kullanarak)
            try:
                # Hash ile mevcut belgeleri ara
                results = self.collection.get(
                    where={"hash": content_hash}
                )
                
                if results and results["ids"]:
                    return {
                        "success": False, 
                        "error": "Bu belge (veya çok benzer içeriğe sahip bir belge) zaten veritabanında mevcut.",
                        "id": results["ids"][0]
                    }
            except Exception as e:
                print(f"Duplikasyon kontrolü sırasında hata: {e}")
            
            # Metni parçalara böl (gerekirse)
            max_chunk_size = 8000  # Karakter sayısı
            
            if len(text) > max_chunk_size:
                chunks = self._chunk_text(text, max_chunk_size)
                for i, chunk in enumerate(chunks):
                    chunk_id = f"{doc_id}_chunk_{i}"
                    chunk_metadata = simple_metadata.copy()
                    chunk_metadata["chunk"] = i  # Daha basit bir isim
                    chunk_metadata["chunks"] = len(chunks)  # Daha basit bir isim
                    
                    self.collection.add(
                        documents=[chunk],
                        metadatas=[chunk_metadata],
                        ids=[chunk_id]
                    )
            else:
                self.collection.add(
                    documents=[text],
                    metadatas=[simple_metadata],
                    ids=[doc_id]
                )
            
            return {
                "success": True, 
                "id": doc_id, 
                "metadata": simple_metadata
            }
        
        except Exception as e:
            print(f"PDF ekleme hatası: {e}")
            return {
                "success": False, 
                "error": str(e), 
                "id": None
            }
    
    def search(self, query, n_results=5, collection_name=None, filter_query=None):
        """
        Veritabanında arama yapar.
        
        Args:
            query (str): Arama sorgusu
            n_results (int): Dönecek maksimum sonuç sayısı
            collection_name (str, optional): Kullanılmıyor
            filter_query (dict, optional): Filtreleme kriterleri
            
        Returns:
            dict: Arama sonuçları
        """
        try:
            results = self.collection.query(
                query_texts=[query],
                where=filter_query,
                n_results=n_results
            )
            
            return results
        except Exception as e:
            print(f"Arama hatası: {e}")
            return {"ids": [], "documents": [[]], "metadatas": [[]], "distances": [[]]}
    
    def get_all_documents(self, collection_name=None, limit=100, offset=0):
        """
        Koleksiyondaki tüm belgeleri döndürür.
        
        Args:
            collection_name (str, optional): Kullanılmıyor
            limit (int): Maksimum belge sayısı
            offset (int): Başlangıç indeksi
            
        Returns:
            dict: Belge listesi
        """
        try:
            # Tüm belgeleri al
            results = self.collection.get()
            
            # Chunk'ları grupla ve ana belgeleri bul
            main_documents = {}
            for i, (doc_id, metadata) in enumerate(zip(results["ids"], results["metadatas"])):
                if '_chunk_' in doc_id:
                    main_id = doc_id.split('_chunk_')[0]
                    if main_id not in main_documents:
                        main_documents[main_id] = {
                            'id': main_id,
                            'metadata': metadata.copy(),
                            'chunks': []
                        }
                    main_documents[main_id]['chunks'].append(doc_id)
                else:
                    main_documents[doc_id] = {
                        'id': doc_id,
                        'metadata': metadata,
                        'chunks': []
                    }
            
            # Ana belge listesini oluştur
            main_doc_list = list(main_documents.values())
            total_count = len(main_doc_list)
            
            # Sayfalama uygula
            start_idx = offset
            end_idx = min(offset + limit, total_count)
            paginated_docs = main_doc_list[start_idx:end_idx]
            
            # Sonuçları hazırla
            return {
                "ids": [doc['id'] for doc in paginated_docs],
                "metadatas": [doc['metadata'] for doc in paginated_docs],
                "total": total_count
            }
            
        except Exception as e:
            print(f"Belgeleri alma hatası: {e}")
            return {"ids": [], "metadatas": [], "total": 0}
    
    def delete_document(self, doc_id, collection_name=None):
        """
        Belgeyi veritabanından siler.
        
        Args:
            doc_id (str): Silinecek belge ID'si
            collection_name (str, optional): Kullanılmıyor
            
        Returns:
            bool: Başarı durumu
        """
        try:
            # Tüm belgeleri al
            all_results = self.collection.get()
            
            # Chunk ID'lerini bul
            chunk_ids = [id for id in all_results["ids"] 
                       if id.startswith(f"{doc_id}_chunk_")]
            
            # Önce chunk'ları sil
            if chunk_ids:
                print(f"Silinecek chunk'lar: {chunk_ids}")
                self.collection.delete(ids=chunk_ids)
            
            # Son olarak ana belgeyi sil
            print(f"Ana belge siliniyor: {doc_id}")
            self.collection.delete(ids=[doc_id])
            
            # Silme işleminin başarılı olduğunu kontrol et
            verify_result = self.collection.get(ids=[doc_id])
            if not verify_result["ids"]:
                return True
            else:
                print("Belge silme doğrulaması başarısız")
                return False
                
        except Exception as e:
            print(f"Silme hatası: {e}")
            return False
    
    def get_stats(self):
        """
        Veritabanı istatistiklerini döndürür.
        
        Returns:
            dict: İstatistikler
        """
        stats = {
            "total_docs": 0,
            "collections": [self.collection_name],
            "collection_stats": {}
        }
        
        try:
            # Tüm belgeleri al
            results = self.collection.get()
            
            # Chunk'ları grupla ve ana belgeleri say
            main_documents = set()
            for doc_id in results["ids"]:
                if '_chunk_' in doc_id:
                    main_id = doc_id.split('_chunk_')[0]
                    main_documents.add(main_id)
                else:
                    main_documents.add(doc_id)
            
            stats["total_docs"] = len(main_documents)
            stats["collection_stats"][self.collection_name] = {
                "count": len(main_documents)
            }
        except Exception as e:
            print(f"İstatistik hatası: {e}")
        
        return stats