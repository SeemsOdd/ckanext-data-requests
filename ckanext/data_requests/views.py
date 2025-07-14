import ckan.plugins.toolkit as toolkit
import ckan.lib.helpers as h
from flask import request, redirect, url_for
from datetime import datetime


def get_db_connection():
    """Veritabanı bağlantısı ayarlarını CKAN konfigürasyonundan al"""
    try:
        # CKAN'ın datastore veritabanı URL'sini al
        datastore_url = toolkit.config.get('ckan.datastore.write_url')
        
        if datastore_url:
            # URL'yi parse et
            from urllib.parse import urlparse
            parsed = urlparse(datastore_url)
            
            db_config = {
                'host': parsed.hostname,
                'database': parsed.path.lstrip('/'),
                'user': parsed.username,
                'password': parsed.password,
                'port': parsed.port or 5432
            }
        else:
            # Alternatif: Ana veritabanı ayarlarını kullan
            db_url = toolkit.config.get('sqlalchemy.url')
            parsed = urlparse(db_url)
            
            db_config = {
                'host': parsed.hostname,
                'database': parsed.path.lstrip('/'),
                'user': parsed.username,
                'password': parsed.password,
                'port': parsed.port or 5432
            }
        
        return db_config
    except Exception as e:
        h.flash_error(f'Veritabanı konfigürasyonu alınamadı: {str(e)}')
        return None


def create_connection():
    """Veritabanı bağlantısı oluştur"""
    try:
        import psycopg2
        db_config = get_db_connection()
        
        if not db_config:
            return None
            
        conn = psycopg2.connect(**db_config)
        return conn
    except Exception as e:
        h.flash_error(f'Veritabanı bağlantısı kurulamadı: {str(e)}')
        return None


def data_requests_index():
    """Veri istekleri listesi - herkese açık (sadece aktif istekler)"""
    # Filtreleme parametrelerini al
    sort_by = request.args.get('sort', 'newest')
    organization_filter = request.args.get('organization', '')
    status_filter = request.args.get('status', '')
    
    # Sıralama seçenekleri
    sort_options = {
        'newest': 'ORDER BY dr._id DESC',
        'oldest': 'ORDER BY dr._id ASC', 
        'recently_updated': 'ORDER BY COALESCE(dr.response_date, dr.request_date) DESC',
        'title_asc': 'ORDER BY dr.title ASC',
        'title_desc': 'ORDER BY dr.title DESC'
    }
    
    # Geçerli sıralama kontrolü
    if sort_by not in sort_options:
        sort_by = 'newest'
    
    try:
        conn = create_connection()
        if not conn:
            return toolkit.render('data_requests/index.html', {
                'requests': [],
                'organizations': [],
                'current_sort': sort_by,
                'current_organization': organization_filter,
                'current_status': status_filter
            })
            
        cur = conn.cursor()
        
        # CKAN organizasyonlarını getir (filtreleme için)
        try:
            all_organizations = toolkit.get_action('organization_list')(
                {}, {'all_fields': True, 'include_extras': True, 'sort': 'title asc'}
            )
            # Sadece aktif organizasyonları al
            organizations = [
                {'id': org['id'], 'name': org['title'] or org['name']} 
                for org in all_organizations 
                if org.get('state') == 'active'
            ]
        except Exception as e:
            # Fallback: data_requests tablosundan al
            cur.execute("""
                SELECT DISTINCT organization_id, organization_name 
                FROM data_requests 
                WHERE is_active = TRUE AND organization_name IS NOT NULL 
                ORDER BY organization_name
            """)
            organizations = [{'id': row[0], 'name': row[1]} for row in cur.fetchall()]
        
        # Filtreleme koşullarını oluştur
        where_conditions = ['dr.is_active = TRUE']
        params = []
        
        if organization_filter:
            where_conditions.append('dr.organization_id = %s')
            params.append(organization_filter)
            
        if status_filter:
            where_conditions.append('dr.status = %s')
            params.append(status_filter)
        
        where_clause = ' AND '.join(where_conditions)
        
        # Ana sorgu
        query = f"""
            SELECT * FROM data_requests dr
            WHERE {where_clause}
            {sort_options[sort_by]}
        """
        
        cur.execute(query, params)
        requests = [dict(zip([desc[0] for desc in cur.description], row)) for row in cur.fetchall()]
        cur.close()
        conn.close()
    except Exception as e:
        requests = []
        organizations = []
        h.flash_error(f'Veri yüklenirken hata: {str(e)}')
        
    return toolkit.render('data_requests/index.html', {
        'requests': requests,
        'organizations': organizations,
        'current_sort': sort_by,
        'current_organization': organization_filter,
        'current_status': status_filter
    })


def data_requests_create():
    """Yeni veri isteği oluşturma - sadece giriş yapmış kullanıcılar"""
    # Kullanıcı giriş kontrolü
    if not toolkit.c.userobj:
        h.flash_error('Veri isteği oluşturmak için giriş yapmalısınız.')
        return toolkit.redirect_to('user.login')
    
    # CKAN organizasyonlarını getir
    try:
        organizations = toolkit.get_action('organization_list')(
            {}, {'all_fields': True, 'include_extras': True, 'sort': 'title asc'}
        )
        # Sadece aktif organizasyonları filtrele
        organizations = [org for org in organizations if org.get('state') == 'active']
    except Exception as e:
        organizations = []
        h.flash_error(f'Organizasyonlar yüklenirken hata: {str(e)}')
    
    if request.method == 'POST':
        try:
            title = request.form.get('title', '').strip()
            organization_id = request.form.get('organization_id', '').strip()
            request_text = request.form.get('request_text', '').strip()
            
            errors = {}
            if not title:
                errors['title'] = 'Başlık zorunludur'
            if len(title) < 5:
                errors['title'] = 'Başlık en az 5 karakter olmalıdır'
            if not organization_id:
                errors['organization_id'] = 'Organizasyon seçimi zorunludur'
            if not request_text:
                errors['request_text'] = 'Veri isteği açıklaması zorunludur'
            if len(request_text) < 10:
                errors['request_text'] = 'Açıklama en az 10 karakter olmalıdır'
                
            if errors:
                return toolkit.render('data_requests/create.html', {
                    'errors': errors, 
                    'data': request.form,
                    'user': toolkit.c.userobj,
                    'organizations': organizations
                })
            
            # Seçilen organizasyonun adını bul
            organization_name = 'Bilinmeyen Organizasyon'
            for org in organizations:
                if org['id'] == organization_id:
                    organization_name = org['title'] or org['name']
                    break
            
            # Kullanıcı bilgileri
            user_id = toolkit.c.userobj.id
            username = toolkit.c.userobj.display_name or toolkit.c.userobj.name
            
            # Veritabanına ekle
            conn = create_connection()
            if not conn:
                h.flash_error('Veritabanı bağlantısı kurulamadı')
                return toolkit.render('data_requests/create.html', {
                    'user': toolkit.c.userobj,
                    'organizations': organizations
                })
                
            cur = conn.cursor()
            cur.execute("""
                INSERT INTO data_requests (user_id, username, title, organization_id, organization_name, request_date, request_text, is_active)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """, (user_id, username, title, organization_id, organization_name, datetime.now(), request_text, False))
            conn.commit()
            cur.close()
            conn.close()
            
            h.flash_success('Veri isteğiniz başarıyla gönderildi! Admin onayından sonra yayınlanacaktır.')
            return redirect(url_for('data_requests.index'))
            
        except Exception as e:
            h.flash_error(f'Hata oluştu: {str(e)}')
    
    return toolkit.render('data_requests/create.html', {
        'user': toolkit.c.userobj,
        'organizations': organizations
    })


def data_requests_admin():
    """Admin paneli - sadece sistem adminleri"""
    # Admin kontrolü
    if not toolkit.c.userobj or not toolkit.c.userobj.sysadmin:
        toolkit.abort(403, 'Bu sayfaya erişim yetkiniz yok')
    
    if request.method == 'POST':
        try:
            request_id = request.form.get('request_id')
            action = request.form.get('action')
            
            conn = create_connection()
            if not conn:
                h.flash_error('Veritabanı bağlantısı kurulamadı')
                return toolkit.render('data_requests/admin.html', {
                    'requests': [],
                    'current_sort': 'newest'
                })
                
            cur = conn.cursor()
            
            if action == 'delete':
                # SİLME İŞLEMİ
                cur.execute("DELETE FROM data_requests WHERE _id = %s", (request_id,))
                
                # Silme işleminden sonra sequence'i sıfırla
                cur.execute("SELECT setval('data_requests__id_seq', COALESCE((SELECT MAX(_id) FROM data_requests), 0) + 1, false)")
                
                conn.commit()
                h.flash_success('Veri isteği silindi ve ID sırası güncellendi!')
                
            elif action in ['activate', 'deactivate']:
                # AKTİF/PASİF İŞLEMİ
                is_active = (action == 'activate')
                cur.execute("UPDATE data_requests SET is_active = %s WHERE _id = %s", 
                           (is_active, request_id))
                conn.commit()
                status = 'aktif' if is_active else 'pasif'
                h.flash_success(f'İstek {status} yapıldı!')
                
            elif action == 'respond':
                # YANIT VERME İŞLEMİ
                admin_response = request.form.get('admin_response', '').strip()
                new_status = request.form.get('status', 'completed')
                
                if admin_response:
                    admin_id = toolkit.c.userobj.id
                    admin_name = toolkit.c.userobj.display_name or toolkit.c.userobj.name
                    
                    cur.execute("""
                        UPDATE data_requests 
                        SET admin_response = %s, response_date = %s, responded_by = %s, status = %s 
                        WHERE _id = %s
                    """, (admin_response, datetime.now(), admin_name, new_status, request_id))
                    conn.commit()
                    h.flash_success('Yanıt başarıyla gönderildi!')
                else:
                    h.flash_error('Yanıt boş olamaz!')
                    
            elif action == 'change_status':
                # DURUM DEĞİŞTİRME
                new_status = request.form.get('status')
                cur.execute("UPDATE data_requests SET status = %s WHERE _id = %s", 
                           (new_status, request_id))
                conn.commit()
                h.flash_success(f'Durum "{new_status}" olarak güncellendi!')
            
            cur.close()
            conn.close()
            
        except Exception as e:
            h.flash_error(f'İşlem hatası: {str(e)}')
    
    # Sıralama parametresini al (admin için)
    sort_by = request.args.get('sort', 'newest') if request.method == 'GET' else 'newest'
    
    # Admin için genişletilmiş sıralama seçenekleri
    admin_sort_options = {
        'newest': 'ORDER BY _id DESC',
        'oldest': 'ORDER BY _id ASC',
        'recently_updated': 'ORDER BY COALESCE(response_date, request_date) DESC',
        'title_asc': 'ORDER BY title ASC',
        'title_desc': 'ORDER BY title DESC',
        'status_pending': 'ORDER BY CASE WHEN status = \'pending\' THEN 0 ELSE 1 END, _id DESC',
        'organization': 'ORDER BY organization_name ASC, _id DESC'
    }
    
    if sort_by not in admin_sort_options:
        sort_by = 'newest'
    
    # Tüm istekleri getir (admin tüm istekleri görebilir)
    try:
        conn = create_connection()
        if not conn:
            return toolkit.render('data_requests/admin.html', {
                'requests': [],
                'current_sort': sort_by
            })
            
        cur = conn.cursor()
        
        query = f"SELECT * FROM data_requests {admin_sort_options[sort_by]}"
        cur.execute(query)
        requests = [dict(zip([desc[0] for desc in cur.description], row)) for row in cur.fetchall()]
        cur.close()
        conn.close()
    except Exception as e:
        requests = []
        h.flash_error(f'Veri yüklenirken hata: {str(e)}')
        
    return toolkit.render('data_requests/admin.html', {
        'requests': requests,
        'current_sort': sort_by
    })


def data_requests_detail(request_id):
    """Veri isteği detay sayfası"""
    try:
        conn = create_connection()
        if not conn:
            h.flash_error('Veritabanı bağlantısı kurulamadı')
            return toolkit.redirect_to('data_requests.index')
            
        cur = conn.cursor()
        cur.execute("SELECT * FROM data_requests WHERE _id = %s", (request_id,))
        result = cur.fetchone()
        
        if result:
            # Sütun isimlerini al ve dictionary oluştur
            columns = [desc[0] for desc in cur.description]
            request_data = dict(zip(columns, result))
        else:
            request_data = None
            
        cur.close()
        conn.close()
        
        if not request_data:
            toolkit.abort(404, 'Veri isteği bulunamadı')
            
        # Sadece aktif istekleri herkese göster, admin tümünü görebilir
        if not request_data['is_active'] and (not toolkit.c.userobj or not toolkit.c.userobj.sysadmin):
            toolkit.abort(404, 'Veri isteği bulunamadı')
            
    except Exception as e:
        h.flash_error(f'Veri yüklenirken hata: {str(e)}')
        return toolkit.redirect_to('data_requests.index')
        
    return toolkit.render('data_requests/detail.html', {
        'request': request_data,
        'is_admin': toolkit.c.userobj and toolkit.c.userobj.sysadmin
    })