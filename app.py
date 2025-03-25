import streamlit as st
import os
import tempfile
import time
import base64
from datetime import datetime
import pandas as pd
from arxiv_downloader import ArxivDownloader
from pdf_processor import PDFProcessor
from chroma_manager import ChromaManager

# PDF silme fonksiyonu
def delete_pdf(file_path):
    try:
        if os.path.exists(file_path):
            os.remove(file_path)
            # Session state'den sil
            st.session_state.downloaded_pdfs = [p for p in st.session_state.downloaded_pdfs if p["file_path"] != file_path]
            return True
        return False
    except Exception as e:
        print(f"Silme hatası: {e}")
        return False

# Sabit değişkenler
DATA_DIR = "./data"
DOWNLOAD_DIR = os.path.join(DATA_DIR, "downloads")
DB_PATH = "./chroma_data"
COLLECTION_NAME = "knowledge"  # Tek koleksiyon adı

# Dizinleri oluştur
for directory in [DATA_DIR, DOWNLOAD_DIR, DB_PATH]:
    if not os.path.exists(directory):
        os.makedirs(directory)

# Streamlit sayfa yapılandırması
st.set_page_config(
    page_title="Chroma PDF Manager",
    page_icon="📚",
    layout="wide",
    initial_sidebar_state="expanded"
)

# CSS eklentisi
st.markdown("""
<style>
    .main .block-container {padding-top: 2rem;}
    .stButton>button {width: 100%;}
    .stProgress .st-bo {background-color: #4CAF50;}
    .pdf-item {border: 1px solid #ddd; padding: 10px; border-radius: 5px; margin-bottom: 10px;}
    .pdf-item:hover {background-color: #f9f9f9;}
    .pdf-container {border: 1px solid #ddd; padding: 15px; border-radius: 5px; margin-bottom: 15px;}
    .metadata-editor {background-color: #f0f0f0; padding: 10px; border-radius: 5px;}
    .star-button {color: gold; font-size: 24px; cursor: pointer;}
    .star-button-inactive {color: #ccc; font-size: 24px; cursor: pointer;}
    .pdf-action-button {background-color: #f5f5f5; border: 1px solid #ddd; padding: 5px 10px; border-radius: 3px; text-decoration: none; color: #333;}
    .pdf-action-button:hover {background-color: #e5e5e5;}
</style>
""", unsafe_allow_html=True)

# PDF görüntüleyici için yardımcı fonksiyon
def get_pdf_download_link(file_path):
    try:
        with open(file_path, "rb") as f:
            base64_pdf = base64.b64encode(f.read()).decode('utf-8')
        return f'<a href="data:application/pdf;base64,{base64_pdf}" download="{os.path.basename(file_path)}" style="display: inline-block; padding: 8px 16px; background-color: #4CAF50; color: white; text-decoration: none; border-radius: 4px;">PDF\'i İndir</a>'
    except Exception as e:
        st.error(f"PDF indirme hatası: {e}")
        return None

# Sınıf örneklerini oluştur
arxiv_downloader = ArxivDownloader(save_dir=DOWNLOAD_DIR)
chroma_manager = ChromaManager(db_path=DB_PATH)

# Yan menü
with st.sidebar:
    st.title("Chroma PDF Manager")
    st.write("Araştırma makalelerini indirin, yönetin ve veritabanına ekleyin.")
    
    # Sayfa Seçimi
    page = st.radio(
        "Sayfa",
        ["Ana Sayfa", "ArXiv İndirici", "İndirilen PDF'ler", "Ayrıca PDF Ekle", "Veritabanı Yönetimi"]
    )
    
    # Veritabanı durumu
    st.subheader("Veritabanı Durumu")
    try:
        stats = chroma_manager.get_stats()
        st.info(f"Toplam Belge: {stats['total_docs']}")
        
        if stats['collections']:
            st.write(f"Koleksiyon: {COLLECTION_NAME}")
            st.write(f"İçerik: {stats['collection_stats'].get(COLLECTION_NAME, {}).get('count', 0)} belge")
        else:
            st.warning("Henüz koleksiyon bulunmuyor.")
    except Exception as e:
        st.error(f"Veritabanı durumu alınamadı: {e}")
    
    # Yardım bilgisi
    with st.expander("Yardım"):
        st.write("""
        **ArXiv İndirici**: ArXiv'den makaleleri arayın ve indirin.
        
        **İndirilen PDF'ler**: İndirilen PDF dosyalarını görüntüleyin ve yönetin.
        
        **PDF Yönetimi**: PDF dosyalarını yükleyin ve inceleyin.
        
        **Veritabanı Yönetimi**: Chroma veritabanındaki belgeleri yönetin ve arama yapın.
        
        Bu uygulama, Claude AI ile kullanmak üzere araştırma makalelerinden bir veritabanı oluşturmanıza yardımcı olur.
        """)


# Ana Sayfa
if page == "Ana Sayfa":
    st.title("Chroma PDF Manager")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("Hoş Geldiniz! 👋")
        st.write("""
        Bu uygulama, araştırma makalelerini yönetmek ve veritabanı oluşturmak için tasarlanmıştır.
        
        **Neler yapabilirsiniz:**
        
        - ArXiv'den makaleleri arayın ve indirin
        - İndirilen PDF'leri görüntüleyin ve yönetin
        - PDF dosyalarınızı yükleyin ve inceleyin
        - Seçtiğiniz makaleleri Chroma veritabanına ekleyin
        - Veritabanında arama yapın ve belgeleri yönetin
        """)
        
        st.info("Claude AI, bu veritabanını kullanarak sorularınıza kapsamlı yanıtlar verebilir.")
    
    
    # En son eklenen makaleler
    st.subheader("Son Eklenen Makaleler")
    
    try:
        latest_docs = chroma_manager.get_all_documents(limit=5)
        
        if latest_docs["total"] > 0:
            for i, (doc_id, metadata) in enumerate(zip(latest_docs["ids"], latest_docs["metadatas"])):
                with st.expander(f"{i+1}. {metadata.get('title', 'Başlıksız')}"):
                    st.write(f"**ID:** {doc_id}")
                    st.write(f"**Yazarlar:** {metadata.get('author', metadata.get('authors', 'Belirtilmemiş'))}")
                    st.write(f"**Eklenme Tarihi:** {metadata.get('added_date', 'Belirtilmemiş')}")
                    st.write(f"**Kaynak:** {metadata.get('source', 'Manuel yükleme')}")
        else:
            st.info("Henüz veritabanına eklenmiş makale bulunmuyor.")
    except Exception as e:
        st.error(f"Son makaleleri getirirken hata: {e}")


# ArXiv İndirici
elif page == "ArXiv İndirici":
    st.title("ArXiv Makale İndirici")
    
    with st.form("arxiv_search_form"):
        st.subheader("Arama Kriterleri")
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            query = st.text_input("Anahtar Kelime", "reinforcement learning")
            st.info("Örnek: 'deep learning', 'transformer', 'attention mechanism'")
        
        with col2:
            current_year = datetime.now().year
            years = list(range(2005, current_year + 1))
            years.reverse()
            start_year = st.selectbox("Başlangıç Yılı", years, index=1)
        
        with col3:
            sort_by = st.selectbox(
                "Sıralama",
                ["En Yeni", "En Eski", "Alaka Düzeyi"],
                index=0
            )
        
        # Sayfalama seçenekleri
        per_page = st.selectbox(
            "Sayfa Başına Göster",
            [20, 50, 100, 200],
            index=0
        )
        
        submitted = st.form_submit_button("ArXiv'de Ara")
    
    if submitted:
        with st.spinner("ArXiv'de makaleler aranıyor..."):
            try:
                # Sıralama parametresini ayarla
                sort_param = {
                    "En Yeni": "submittedDate",
                    "En Eski": "submittedDate",
                    "Alaka Düzeyi": "relevance"
                }[sort_by]
                
                # Sıralama yönünü ayarla
                sort_order = "descending" if sort_by == "En Yeni" else "ascending"
                
                # Sayfalama için offset hesapla
                if "current_page" not in st.session_state:
                    st.session_state.current_page = 0
                
                offset = st.session_state.current_page * per_page
                
                total_count, papers = arxiv_downloader.search_papers(
                    query_keyword=query,
                    start_year=start_year,
                    sort_by=sort_param,
                    sort_order=sort_order,
                    offset=offset,
                    per_page=per_page
                )
                
                if not papers:
                    st.warning("Arama kriterlerinize uygun makale bulunamadı. Lütfen farklı anahtar kelimeler deneyin.")
                else:
                    st.session_state.arxiv_papers = papers
                    st.session_state.total_papers = total_count
                    st.success(f"Sayfa {st.session_state.current_page + 1} için {len(papers)} makale bulundu.")
                    
            except Exception as e:
                st.error(f"Arama sırasında hata oluştu: {str(e)}")
                st.info("Lütfen daha sonra tekrar deneyin veya farklı arama kriterleri kullanın.")
    
    # Bulunan makaleleri görüntüle
    if "arxiv_papers" in st.session_state and st.session_state.arxiv_papers:
        st.subheader("Bulunan Makaleler")
        
        # Toplu işlem butonları
        col1, col2, col3, col4 = st.columns([1, 1, 1, 1])
        
        with col1:
            if st.button("Tümünü Seç", key="select_all_arxiv"):
                for i in range(len(st.session_state.arxiv_papers)):
                    st.session_state[f"select_paper_{i}"] = True
        
        with col2:
            if st.button("Seçili Makaleleri İndir", key="download_selected"):
                selected_papers = [
                    paper for i, paper in enumerate(st.session_state.arxiv_papers)
                    if st.session_state.get(f"select_paper_{i}", False)
                ]
                
                if not selected_papers:
                    st.warning("İndirilecek makale seçilmedi.")
                else:
                    progress_bar = st.progress(0)
                    status_text = st.empty()
                    
                    downloaded = []
                    for i, paper in enumerate(selected_papers):
                        status_text.text(f"İndiriliyor: {paper['title']}")
                        file_path = arxiv_downloader.download_paper(paper)
                        
                        if file_path:
                            paper["downloaded"] = True
                            paper["local_path"] = file_path
                            downloaded.append(paper)
                        
                        progress_bar.progress((i + 1) / len(selected_papers))
                        time.sleep(1)  # API limitleri için bekleme
                    
                    status_text.text(f"{len(downloaded)} makale indirildi.")
                    st.success(f"{len(downloaded)} makale başarıyla indirildi.")
        
        with col3:
            if st.button("Tüm Makaleleri İndir", key="download_all", type="primary"):
                if st.warning(f"Toplam {st.session_state.total_papers} makale indirilecek. Bu işlem biraz zaman alabilir. Devam etmek istiyor musunuz?"):
                    col1, col2 = st.columns(2)
                    with col1:
                        if st.button("Evet", key="confirm_download_all"):
                            progress_bar = st.progress(0)
                            status_text = st.empty()
                            
                            downloaded = []
                            for i, paper in enumerate(st.session_state.arxiv_papers):
                                status_text.text(f"İndiriliyor: {paper['title']}")
                                file_path = arxiv_downloader.download_paper(paper)
                                
                                if file_path:
                                    paper["downloaded"] = True
                                    paper["local_path"] = file_path
                                    downloaded.append(paper)
                                
                                progress_bar.progress((i + 1) / len(st.session_state.arxiv_papers))
                                time.sleep(1)  # API limitleri için bekleme
                            
                            status_text.text(f"{len(downloaded)} makale indirildi.")
                            st.success(f"{len(downloaded)} makale başarıyla indirildi.")
                    with col2:
                        if st.button("Kapat", key="cancel_download_all"):
                            st.info("İşlem iptal edildi.")
        
        with col4:
            if st.button("Tüm Makaleleri DB'ye Ekle", key="add_all_to_db", type="primary"):
                if st.warning(f"Toplam {st.session_state.total_papers} makale veritabanına eklenecek. Bu işlem biraz zaman alabilir. Devam etmek istiyor musunuz?"):
                    col1, col2 = st.columns(2)
                    with col1:
                        if st.button("Evet", key="confirm_add_all_to_db"):
                            progress_bar = st.progress(0)
                            status_text = st.empty()
                            
                            added = []
                            for i, paper in enumerate(st.session_state.arxiv_papers):
                                status_text.text(f"Ekleniyor: {paper['title']}")
                                
                                # Önce indir
                                file_path = arxiv_downloader.download_paper(paper)
                                if file_path:
                                    # Metadata hazırla
                                    metadata = {
                                        "title": paper["title"],
                                        "author": ", ".join(paper["authors"]),
                                        "summary": paper["summary"][:500],
                                        "published": paper["published"].strftime("%Y-%m-%d"),
                                        "arxiv_id": paper["arxiv_id"],
                                        "source": "arxiv"
                                    }
                                    
                                    # Veritabanına ekle
                                    result = chroma_manager.add_pdf(file_path, metadata)
                                    if result["success"]:
                                        added.append(paper)
                                
                                progress_bar.progress((i + 1) / len(st.session_state.arxiv_papers))
                                time.sleep(1)  # API limitleri için bekleme
                            
                            status_text.text(f"{len(added)} makale veritabanına eklendi.")
                            st.success(f"{len(added)} makale başarıyla veritabanına eklendi.")
                    with col2:
                        if st.button("Kapat", key="cancel_add_all_to_db"):
                            st.info("İşlem iptal edildi.")
        
        # Sayfalama
        total_papers = st.session_state.total_papers
        total_pages = (total_papers + per_page - 1) // per_page
        
        col1, col2, col3 = st.columns([1, 2, 1])
        with col1:
            if st.button("Önceki Sayfa") and st.session_state.current_page > 0:
                st.session_state.current_page -= 1
                st.experimental_rerun()
        with col2:
            # ArXiv web arayüzüne benzer şekilde göster
            start_idx = st.session_state.current_page * per_page + 1
            end_idx = min(start_idx + per_page - 1, total_papers)
            st.write(f"Showing {start_idx}–{end_idx} of {total_papers} results")
        with col3:
            if st.button("Sonraki Sayfa") and st.session_state.current_page < total_pages - 1:
                st.session_state.current_page += 1
                st.experimental_rerun()
        
        # Mevcut sayfadaki makaleleri göster
        start_idx = st.session_state.current_page * per_page
        end_idx = min(start_idx + per_page, total_papers)
        current_papers = st.session_state.arxiv_papers[start_idx:end_idx]
        
        # Makale listesi
        for i, paper in enumerate(current_papers):
            col1, col2 = st.columns([1, 20])
            
            with col1:
                if f"select_paper_{start_idx + i}" not in st.session_state:
                    st.session_state[f"select_paper_{start_idx + i}"] = False
                
                selected = st.checkbox("", key=f"select_paper_{start_idx + i}")
            
            with col2:
                with st.expander(f"{paper['title']} ({paper['published'].strftime('%Y-%m-%d')})"):
                    st.write(f"**Yazarlar:** {', '.join(paper['authors'])}")
                    st.write(f"**ArXiv ID:** {paper['arxiv_id']}")
                    st.write(f"**Kategoriler:** {', '.join(paper['categories'])}")
                    st.write(f"**PDF URL:** {paper['pdf_url']}")
                    st.write("**Özet:**")
                    st.write(paper['summary'])
                    
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        # İndirme durumunu kontrol et
                        if paper.get("downloaded", False):
                            st.success("İndirildi ✓")
                            
                            # PDF görüntüleme butonu
                            if st.button("PDF'i İndir", key=f"download_{paper['arxiv_id']}"):
                                st.markdown(get_pdf_download_link(paper["local_path"]), unsafe_allow_html=True)
                            
                            # ChomraDB'ye ekleme düğmesi
                            if st.button("Veritabanına Ekle", key=f"add_to_db_{paper['arxiv_id']}"):
                                with st.spinner("Veritabanına ekleniyor..."):
                                    # Metadata hazırla (basitleştirilmiş)
                                    metadata = {
                                        "title": paper["title"],
                                        "author": ", ".join(paper["authors"]),
                                        "summary": paper["summary"][:500],
                                        "published": paper["published"].strftime("%Y-%m-%d"),
                                        "arxiv_id": paper["arxiv_id"],
                                        "source": "arxiv"
                                    }
                                    
                                    result = chroma_manager.add_pdf(paper["local_path"], metadata)
                                    
                                    if result["success"]:
                                        st.success("Veritabanına eklendi!")
                                    else:
                                        st.error(f"Ekleme hatası: {result['error']}")
                        else:
                            if st.button("İndir", key=f"download_{paper['arxiv_id']}"):
                                with st.spinner("İndiriliyor..."):
                                    file_path = arxiv_downloader.download_paper(paper)
                                    if file_path:
                                        st.session_state.arxiv_papers[start_idx + i]["downloaded"] = True
                                        st.session_state.arxiv_papers[start_idx + i]["local_path"] = file_path
                                        st.success("İndirildi!")
                                        st.experimental_rerun()
                                    else:
                                        st.error("İndirme başarısız.")


# İndirilen PDF'ler
elif page == "İndirilen PDF'ler":
    st.title("İndirilen PDF'ler")
    
    # İndirilen PDF'leri listele
    if "downloaded_pdfs" not in st.session_state:
        st.session_state.downloaded_pdfs = []
        # PDF'leri bir kere yükle ve session state'de sakla
        for file in os.listdir(DOWNLOAD_DIR):
            if file.endswith(".pdf"):
                file_path = os.path.join(DOWNLOAD_DIR, file)
                try:
                    # PDF işleyici başlat
                    processor = PDFProcessor(file_path)
                    metadata = processor.extract_metadata()
                    
                    st.session_state.downloaded_pdfs.append({
                        "file_name": file,
                        "file_path": file_path,
                        "title": metadata.get("title", file),
                        "authors": metadata.get("authors", ""),
                        "created": datetime.fromtimestamp(os.path.getctime(file_path)).strftime("%Y-%m-%d %H:%M:%S")
                    })
                except Exception as e:
                    print(f"PDF işleme hatası ({file}): {e}")
                    st.session_state.downloaded_pdfs.append({
                        "file_name": file,
                        "file_path": file_path,
                        "title": file,
                        "authors": "Bilinmiyor",
                        "created": datetime.fromtimestamp(os.path.getctime(file_path)).strftime("%Y-%m-%d %H:%M:%S")
                    })
        
        # PDF'leri tarihe göre sırala (en yeniden en eskiye)
        st.session_state.downloaded_pdfs.sort(key=lambda x: x["created"], reverse=True)
    
    if not st.session_state.downloaded_pdfs:
        st.info("Henüz indirilmiş PDF bulunmuyor.")
    else:
        # Toplu seçim ve işlem butonları
        col1, col2, col3 = st.columns([1, 1, 2])
        with col1:
            if st.button("Tümünü Seç", key="select_all_downloaded"):
                for i in range(len(st.session_state.downloaded_pdfs)):
                    st.session_state[f"select_pdf_{i}"] = True
        
        with col2:
            if st.button("Seçili PDF'leri DB'ye Ekle", key="add_selected_to_db"):
                selected_pdfs = [
                    pdf for i, pdf in enumerate(st.session_state.downloaded_pdfs)
                    if st.session_state.get(f"select_pdf_{i}", False)
                ]
                
                if not selected_pdfs:
                    st.warning("Veritabanına eklenecek PDF seçilmedi.")
                else:
                    progress_bar = st.progress(0)
                    status_text = st.empty()
                    
                    added = []
                    for i, pdf in enumerate(selected_pdfs):
                        status_text.text(f"Ekleniyor: {pdf['title']}")
                        # Basitleştirilmiş metadata
                        metadata = {
                            "title": pdf["title"],
                            "author": pdf["authors"],
                            "source": "download_folder"
                        }
                        
                        result = chroma_manager.add_pdf(pdf["file_path"], metadata)
                        
                        if result["success"]:
                            added.append(pdf)
                        
                        progress_bar.progress((i + 1) / len(selected_pdfs))
                        time.sleep(0.5)  # API limitleri için bekleme
                    
                    status_text.text(f"{len(added)} PDF veritabanına eklendi.")
                    st.success(f"{len(added)} PDF başarıyla veritabanına eklendi.")
        
        with col3:
            if st.button("Seçili PDF'leri Sil", key="delete_selected_pdfs"):
                selected_pdfs = [
                    pdf for i, pdf in enumerate(st.session_state.downloaded_pdfs)
                    if st.session_state.get(f"select_pdf_{i}", False)
                ]
                
                if not selected_pdfs:
                    st.warning("Silinecek PDF seçilmedi.")
                else:
                    if st.warning(f"{len(selected_pdfs)} PDF siliniyor."):
                        progress_bar = st.progress(0)
                        status_text = st.empty()
                        
                        deleted = []
                        for i, pdf in enumerate(selected_pdfs):
                            status_text.text(f"Siliniyor: {pdf['title']}")
                            if delete_pdf(pdf["file_path"]):
                                deleted.append(pdf)
                            
                            progress_bar.progress((i + 1) / len(selected_pdfs))
                            time.sleep(0.5)
                        
                        status_text.text(f"{len(deleted)} PDF silindi.")
                        st.success(f"{len(deleted)} PDF başarıyla silindi.")
                        st.experimental_rerun()
        
        # PDF listesi
        for i, pdf in enumerate(st.session_state.downloaded_pdfs):
            col1, col2 = st.columns([1, 20])
            
            with col1:
                if f"select_pdf_{i}" not in st.session_state:
                    st.session_state[f"select_pdf_{i}"] = False
                
                selected = st.checkbox("", key=f"select_pdf_{i}")
            
            with col2:
                with st.expander(f"{i+1}. {pdf['title']}", expanded=False):
                    col1, col2, col3 = st.columns([2, 1, 1])
                    
                    with col1:
                        st.write(f"**Dosya:** {pdf['file_name']}")
                        st.write(f"**Yazarlar:** {pdf['authors']}")
                        st.write(f"**Tarih:** {pdf['created']}")
                    
                    with col2:
                        # PDF indirme butonu
                        if st.button("📥 İndir", key=f"download_{pdf['file_path']}"):
                            st.markdown(get_pdf_download_link(pdf["file_path"]), unsafe_allow_html=True)
                    
                    with col3:
                        # Veritabanına ekleme butonu
                        if st.button("💾 DB'ye Ekle", key=f"add_to_db_{pdf['file_path']}"):
                            with st.spinner("Veritabanına ekleniyor..."):
                                # Basitleştirilmiş metadata
                                metadata = {
                                    "title": pdf["title"],
                                    "author": pdf["authors"],
                                    "source": "download_folder"
                                }
                                
                                result = chroma_manager.add_pdf(pdf["file_path"], metadata)
                                
                                if result["success"]:
                                    st.success("Veritabanına eklendi!")
                                else:
                                    st.error(f"Ekleme hatası: {result['error']}")
                    
                    # Silme butonu
                    if st.button("🗑️ Sil", key=f"delete_{pdf['file_path']}"):
                        if delete_pdf(pdf["file_path"]):
                            st.success("PDF başarıyla silindi!")
                            st.experimental_rerun()
                        else:
                            st.error("PDF silinemedi. Lütfen tekrar deneyin.")


# PDF Yönetimi
elif page == "Ayrıca PDF Ekle":
    st.title("Ayrıca PDF Ekle")
    
    # PDF yükleme alanı
    uploaded_files = st.file_uploader("PDF Dosyalarını Yükleyin", type=["pdf"], accept_multiple_files=True)
    
    # Yüklenen PDF'leri işle
    if uploaded_files:
        st.subheader("Yüklenen PDF'ler")
        
        for i, uploaded_file in enumerate(uploaded_files):
            # PDF'i indirme dizinine kaydet
            file_path = os.path.join(DOWNLOAD_DIR, uploaded_file.name)
            with open(file_path, "wb") as f:
                f.write(uploaded_file.getvalue())
            
            # PDF'i işle
            processor = PDFProcessor(file_path)
            metadata = processor.extract_metadata()
            
            with st.expander(f"{uploaded_file.name}"):
                col1, col2 = st.columns(2)
                
                with col1:
                    st.write("**Metadata**")
                    title = st.text_input("Başlık", value=metadata.get("title", uploaded_file.name), key=f"title_{i}")
                    authors = st.text_input("Yazarlar", value=metadata.get("authors", ""), key=f"authors_{i}")
                    
                    # Kaydet ve ekle
                    if st.button(f"Veritabanına Ekle #{i}"):
                        with st.spinner("İşleniyor ve ekleniyor..."):
                            # Basitleştirilmiş metadata
                            updated_metadata = {
                                "title": title,
                                "author": authors,
                                "source": "manual_upload"
                            }
                            
                            # Veritabanına ekle
                            result = chroma_manager.add_pdf(file_path, updated_metadata)
                            
                            if result["success"]:
                                st.success("Veritabanına eklendi!")
                            else:
                                st.error(f"Ekleme hatası: {result['error']}")
                
                with col2:
                    st.write("**İçerik Önizleme**")
                    text = processor.extract_text()
                    if text:
                        st.text_area("Metin Önizleme", value=text[:1000] + "...", height=300, key=f"preview_{i}")
                    else:
                        st.warning("Bu PDF'den metin çıkarılamadı.")
                    
                    # PDF görüntüleme butonu
                    if st.button(f"PDF'i İndir #{i}"):
                        st.markdown(get_pdf_download_link(file_path), unsafe_allow_html=True)


# Veritabanı Yönetimi
elif page == "Veritabanı Yönetimi":
    st.title("Veritabanı Yönetimi")
    
    tabs = st.tabs(["Belge Listesi", "Arama"])
    
    with tabs[0]:  # Belge Listesi
        st.subheader("Veritabanındaki Belgeler")
        
        # Sayfalama
        page_size = st.slider("Sayfa Başına Belge", min_value=5, max_value=50, value=10, step=5)
        
        if "doc_page" not in st.session_state:
            st.session_state.doc_page = 0
        
        col1, col2 = st.columns(2)
        with col1:
            if st.button("Önceki Sayfa") and st.session_state.doc_page > 0:
                st.session_state.doc_page -= 1
        with col2:
            if st.button("Sonraki Sayfa"):
                st.session_state.doc_page += 1
        
        offset = st.session_state.doc_page * page_size
        
        # Belgeleri getir
        docs = chroma_manager.get_all_documents(
            limit=page_size,
            offset=offset
        )
        
        # Chunk'ları grupla ve ana belgeleri bul
        main_documents = {}
        for i, (doc_id, metadata) in enumerate(zip(docs["ids"], docs["metadatas"])):
            # Chunk ID'sini kontrol et
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
        
        total_docs = len(main_documents)
        total_pages = (total_docs + page_size - 1) // page_size if total_docs > 0 else 1
        st.write(f"Sayfa {st.session_state.doc_page + 1}/{max(1, total_pages)} (Toplam {total_docs} belge)")
        
        if total_docs == 0:
            st.info(f"Koleksiyonda '{COLLECTION_NAME}' henüz belge bulunmuyor.")
        else:
            # Belgeleri listele
            doc_list = list(main_documents.values())[offset:offset+page_size]
            for i, doc_info in enumerate(doc_list):
                doc_id = doc_info['id']
                metadata = doc_info['metadata']
                with st.expander(f"📄 {metadata.get('title', 'Başlıksız')}", expanded=False):
                    col1, col2 = st.columns([3, 1])
                    
                    with col1:
                        st.write(f"**Yazar:** {metadata.get('author', 'Bilinmiyor')}")
                        st.write(f"**Kaynak:** {metadata.get('source', 'Bilinmiyor')}")
                        st.write(f"**Dosya:** {metadata.get('file', 'Bilinmiyor')}")
                        # Chunk bilgisini göster
                        if doc_info['chunks']:
                            st.write(f"**Bölüm Sayısı:** {len(doc_info['chunks'])}")
                    
                    with col2:
                        if st.button(f"Sil", key=f"delete_{doc_id}"):
                            # Belgeyi ve tüm chunk'larını tek seferde sil
                            if chroma_manager.delete_document(doc_id):
                                st.success("Belge ve tüm bölümleri silindi.")
                                st.experimental_rerun()
                            else:
                                st.error("Belge silinemedi. Lütfen tekrar deneyin.")
    
    with tabs[1]:  # Arama
        st.subheader("Veritabanında Ara")
        
        # Arama formu
        with st.form("search_form"):
            query = st.text_input("Arama Sorgusu")
            n_results = st.slider("Maksimum Sonuç", min_value=1, max_value=20, value=5)
            submitted = st.form_submit_button("Ara")
        
        if submitted and query:
            with st.spinner("Aranıyor..."):
                results = chroma_manager.search(query, n_results=n_results)
                
                if results["ids"] and results["ids"][0]:
                    # Sonuçları grupla
                    main_documents = {}
                    for doc_id, doc, metadata in zip(
                        results["ids"][0], results["documents"][0], results["metadatas"][0]
                    ):
                        if '_chunk_' in doc_id:
                            main_id = doc_id.split('_chunk_')[0]
                            if main_id not in main_documents:
                                main_documents[main_id] = {
                                    'id': main_id,
                                    'metadata': metadata,
                                    'chunks': []
                                }
                            main_documents[main_id]['chunks'].append((doc_id, doc))
                        else:
                            main_documents[doc_id] = {
                                'id': doc_id,
                                'metadata': metadata,
                                'chunks': [(doc_id, doc)]
                            }
                    
                    st.success(f"{len(main_documents)} sonuç bulundu.")
                    
                    # Ana belgeleri göster
                    for i, (doc_id, doc_info) in enumerate(main_documents.items()):
                        metadata = doc_info['metadata']
                        with st.expander(f"{i+1}. {metadata.get('title', 'Başlıksız')}"):
                            st.write(f"**ID:** {doc_id}")
                            st.write(f"**Yazarlar:** {metadata.get('author', metadata.get('authors', 'Belirtilmemiş'))}")
                            
                            # İlk chunk'ın içeriğini göster
                            if doc_info['chunks']:
                                first_chunk = doc_info['chunks'][0][1]
                                st.write("**İçerik Önizleme:**")
                                st.text_area("", value=first_chunk[:1000] + "..." if len(first_chunk) > 1000 else first_chunk, 
                                          height=200, key=f"result_preview_{i}")
                            
                            # Eğer dosya yolu varsa, indirme butonu göster
                            if 'file_path' in metadata and os.path.exists(metadata['file_path']):
                                if st.button(f"PDF'i İndir #{i}"):
                                    st.markdown(get_pdf_download_link(metadata['file_path']), unsafe_allow_html=True)
                else:
                    st.info("Sonuç bulunamadı.")
    

# Başlangıçta oturum durumunu ayarla
if "page" in st.session_state:
    page = st.session_state.page
    # Oturum durumunu temizle
    del st.session_state.page