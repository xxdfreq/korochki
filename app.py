import pymysql
from flask import Flask, render_template_string, jsonify, request
from flask_compress import Compress

app = Flask(__name__)
Compress(app)

# ============================================================
#  ПОДКЛЮЧЕНИЕ К MYSQL
# ============================================================
DB_CONFIG = {
    'host': '127.0.0.1',
    'user': 'root',
    'password': 'T1988r0522x!',
    'database': 'korochki',
    'charset': 'utf8mb4'
}

# ============================================================
#  ФУНКЦИЯ ЗАГРУЗКИ КНИГ ИЗ БД
# ============================================================
def get_books_from_db(search='', sort='title', page=1, per_page=20):
    conn = None
    try:
        conn = pymysql.connect(**DB_CONFIG)
        with conn.cursor(pymysql.cursors.DictCursor) as cursor:
            offset = (page - 1) * per_page

            # Защита от SQL-инъекции через sort
            allowed_sort = ['title', 'author']
            if sort not in allowed_sort:
                sort = 'title'

            if search:
                # FULLTEXT поиск
                count_sql = """
                    SELECT COUNT(*) as total FROM books 
                    WHERE MATCH(title, author) AGAINST(%s IN BOOLEAN MODE)
                """
                cursor.execute(count_sql, (search + '*',))
                total = cursor.fetchone()['total']

                sql = """
                    SELECT *, MATCH(title, author) AGAINST(%s IN BOOLEAN MODE) as relevance
                    FROM books
                    WHERE MATCH(title, author) AGAINST(%s IN BOOLEAN MODE)
                    ORDER BY relevance DESC
                    LIMIT %s OFFSET %s
                """
                cursor.execute(sql, (search + '*', search + '*', per_page, offset))
            else:
                cursor.execute("SELECT COUNT(*) as total FROM books")
                total = cursor.fetchone()['total']

                sql = f"SELECT * FROM books ORDER BY {sort} LIMIT %s OFFSET %s"
                cursor.execute(sql, (per_page, offset))

            books = cursor.fetchall()
            return books, total

    except pymysql.Error as e:
        print(f"Ошибка MySQL: {e}")
        return [], 0
    except Exception as e:
        print(f"Неизвестная ошибка: {e}")
        return [], 0
    finally:
        if conn:
            conn.close()


#  HTML-ШАБЛОН (с улучшенной доступностью)

HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Библиотека «Корочки.есть»</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; font-family: 'Segoe UI', system-ui, sans-serif; }
        body { background: #f4f7fb; padding: 20px; color: #1e293b; }
        .app { max-width: 1200px; margin: 0 auto; }
        header { display: flex; justify-content: space-between; align-items: center; padding: 15px 20px; background: white; border-radius: 12px; box-shadow: 0 2px 10px rgba(0,0,0,0.05); margin-bottom: 25px; }
        .logo { font-size: 24px; font-weight: 800; color: #1e293b; }
        .logo span { color: #3b82f6; }
        .auth-btns { display: flex; gap: 10px; }
        .auth-btns button { padding: 8px 20px; border: none; border-radius: 8px; font-weight: 600; background: #e2e8f0; color: #1e293b; cursor: default; }
        .search-section { background: white; padding: 20px; border-radius: 12px; box-shadow: 0 2px 10px rgba(0,0,0,0.05); margin-bottom: 25px; display: flex; gap: 15px; flex-wrap: wrap; align-items: center; }
        .search-section .field { flex: 3; min-width: 200px; }
        .search-section .field label { display: block; font-weight: 600; margin-bottom: 4px; font-size: 14px; color: #334155; }
        .search-section .field input { width: 100%; padding: 12px 18px; border: 2px solid #e2e8f0; border-radius: 10px; font-size: 16px; outline: none; transition: 0.3s; }
        .search-section .field input:focus { border-color: #3b82f6; }
        .search-section .field select { width: 100%; padding: 12px 18px; border: 2px solid #e2e8f0; border-radius: 10px; font-size: 16px; background: white; }
        .badge-debounce { background: #dbeafe; color: #1e40af; padding: 4px 12px; border-radius: 20px; font-size: 12px; font-weight: 700; white-space: nowrap; }
        .book-grid { display: grid; grid-template-columns: 1fr; gap: 1rem; margin-bottom: 30px; }
        @media (min-width: 768px) { .book-grid { grid-template-columns: repeat(2, 1fr); } }
        @media (min-width: 1024px) { .book-grid { grid-template-columns: repeat(auto-fill, minmax(220px, 1fr)); } }
        .book-card { background: white; border-radius: 16px; overflow: hidden; box-shadow: 0 4px 12px rgba(0,0,0,0.06); cursor: pointer; transition: 0.2s; }
        .book-card:hover { transform: translateY(-4px); box-shadow: 0 8px 25px rgba(0,0,0,0.1); }
        .cover { width: 100%; aspect-ratio: 3/4; background: #f1f5f9; display: flex; align-items: center; justify-content: center; font-size: 48px; color: #94a3b8; }
        .info { padding: 15px; }
        .info h3 { font-size: 16px; color: #0f172a; margin-bottom: 4px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
        .info p { font-size: 14px; color: #64748b; }
        .pagination { display: flex; justify-content: center; gap: 8px; flex-wrap: wrap; margin-top: 10px; align-items: center; }
        .pagination button { padding: 8px 16px; border: 1px solid #e2e8f0; background: white; border-radius: 8px; font-weight: 600; cursor: pointer; }
        .pagination button.active { background: #3b82f6; color: white; border-color: #3b82f6; }
        .pagination button:disabled { opacity: 0.4; cursor: not-allowed; }
        .pagination .info-text { color: #64748b; font-size: 14px; margin-left: 10px; }
        .tabs { display: flex; gap: 5px; background: white; padding: 6px; border-radius: 12px; margin-bottom: 25px; box-shadow: 0 2px 10px rgba(0,0,0,0.05); }
        .tabs button { flex: 1; padding: 12px; border: none; background: transparent; border-radius: 8px; font-weight: 700; cursor: pointer; color: #64748b; }
        .tabs button.active { background: #3b82f6; color: white; }
        .panel { display: none; }
        .panel.active { display: block; }
        .lk-table { background: white; border-radius: 16px; padding: 20px; overflow-x: auto; box-shadow: 0 2px 10px rgba(0,0,0,0.05); }
        .lk-table table { width: 100%; border-collapse: collapse; }
        .lk-table th { text-align: left; padding: 12px 15px; background: #f8fafc; color: #475569; font-size: 14px; }
        .lk-table td { padding: 12px 15px; border-bottom: 1px solid #f1f5f9; }
        .status { padding: 4px 12px; border-radius: 20px; font-size: 12px; font-weight: 600; }
        .status.pending { background: #fef9c3; color: #854d0e; }
        .status.active { background: #dbeafe; color: #1e40af; }
        .status.returned { background: #dcfce7; color: #166534; }
        .modal-overlay { display: none; position: fixed; inset: 0; background: rgba(0,0,0,0.4); backdrop-filter: blur(4px); z-index: 1000; align-items: center; justify-content: center; }
        .modal-overlay.show { display: flex; }
        .modal { background: white; max-width: 450px; width: 90%; padding: 30px; border-radius: 24px; box-shadow: 0 20px 60px rgba(0,0,0,0.2); }
        .modal h2 { margin-bottom: 20px; color: #0f172a; }
        .modal label { display: block; font-weight: 600; margin: 15px 0 5px; font-size: 14px; color: #334155; }
        .modal input { width: 100%; padding: 10px 14px; border: 2px solid #e2e8f0; border-radius: 10px; font-size: 16px; }
        .modal .actions { display: flex; gap: 10px; margin-top: 25px; justify-content: flex-end; }
        .modal .actions button { padding: 10px 30px; border-radius: 10px; border: none; font-weight: 700; cursor: pointer; }
        .btn-primary { background: #3b82f6; color: white; }
        .btn-secondary { background: #e2e8f0; color: #1e293b; }
        .footer-note { text-align: center; margin-top: 30px; color: #94a3b8; font-size: 13px; border-top: 1px solid #e2e8f0; padding-top: 20px; }
        /* Доступность: скрытый элемент для скринридеров */
        .sr-only { position: absolute; width: 1px; height: 1px; padding: 0; margin: -1px; overflow: hidden; clip: rect(0,0,0,0); border: 0; }
        /* Видимый фокус */
        :focus-visible { outline: 2px solid #3b82f6; outline-offset: 2px; }
    </style>
</head>
<body>
<div class="app">
    <header>
        <div class="logo"><span>Корочки</span>.есть</div>
        <div class="auth-btns"><button>👤 Иван (Читатель)</button><button>Выйти</button></div>
    </header>
    <div class="tabs" role="tablist">
        <button class="active" role="tab" aria-selected="true" onclick="switchTab('catalog')">Каталог книг</button>
        <button role="tab" aria-selected="false" onclick="switchTab('profile')">Мои брони</button>
    </div>
    <div id="panel-catalog" class="panel active" role="tabpanel" aria-labelledby="tab-catalog">
        <div class="search-section">
            <div class="field">
                <label for="searchInput">Поиск по названию или автору</label>
                <input type="text" id="searchInput" placeholder="Введите название или автора..." aria-label="Поиск книг" oninput="handleSearch()">
            </div>
            <div class="field">
                <label for="sortSelect">Сортировка</label>
                <select id="sortSelect" aria-label="Сортировка книг" onchange="loadBooks()">
                    <option value="title">По названию</option>
                    <option value="author">По автору</option>
                </select>
            </div>
            <span class="badge-debounce">Debounce 300 мс</span>
        </div>
        <div id="bookGrid" class="book-grid" role="list"></div>
        <div class="pagination" id="pagination" role="navigation" aria-label="Пагинация"></div>
        <div role="alert" id="errorMessage" style="display:none; color: #dc2626; text-align:center; padding:20px;"></div>
    </div>
    <div id="panel-profile" class="panel" role="tabpanel" aria-labelledby="tab-profile">
        <div class="lk-table">
            <h2>Мои бронирования</h2>
            <table aria-label="История бронирований">
                <thead><tr><th>Книга</th><th>Дата брони</th><th>Дата возврата</th><th>Статус</th></tr></thead>
                <tbody>
                    <tr><td>Мастер и Маргарита</td><td>10.06.2026</td><td>24.06.2026</td><td><span class="status active">Выдана</span></td></tr>
                    <tr><td>Война и мир</td><td>01.06.2026</td><td>15.06.2026</td><td><span class="status returned">Возвращена</span></td></tr>
                    <tr><td>Преступление и наказание</td><td>20.06.2026</td><td>04.07.2026</td><td><span class="status pending">Ожидает</span></td></tr>
                </tbody>
            </table>
        </div>
    </div>
    <div class="modal-overlay" id="bookingModal" role="dialog" aria-modal="true" aria-labelledby="modalTitle">
        <div class="modal">
            <h2 id="modalTitle">Бронирование книги</h2>
            <label for="startDate">Дата начала</label>
            <input type="date" id="startDate" value="2026-06-24" aria-label="Дата начала бронирования">
            <label for="endDate">Дата возврата</label>
            <input type="date" id="endDate" value="2026-07-08" aria-label="Дата возврата">
            <div class="actions">
                <button class="btn-secondary" onclick="closeModal()" aria-label="Отменить бронирование">Отмена</button>
                <button class="btn-primary" onclick="alert('Заявка создана!'); closeModal();" aria-label="Подтвердить бронирование">Забронировать</button>
            </div>
        </div>
    </div>
    <div class="footer-note">Flask + MySQL (FULLTEXT) | Debounce 300 мс | Пагинация 20</div>
</div>
<script>
    let currentPage = 1, PER_PAGE = 20, debounceTimer = null;

    function loadBooks() {
        const search = document.getElementById('searchInput').value;
        const sort = document.getElementById('sortSelect').value;
        const errorDiv = document.getElementById('errorMessage');
        errorDiv.style.display = 'none';

        fetch(`/api/books?search=${encodeURIComponent(search)}&sort=${sort}&page=${currentPage}`)
            .then(r => {
                if (!r.ok) throw new Error('Ошибка загрузки данных');
                return r.json();
            })
            .then(data => {
                const grid = document.getElementById('bookGrid');
                if (!data.data || data.data.length === 0) {
                    grid.innerHTML = '<p style="grid-column:1/-1;text-align:center;padding:60px;background:white;border-radius:16px;color:#94a3b8;">📭 Книг не найдено</p>';
                } else {
                    grid.innerHTML = data.data.map((b, i) => `
                        <div class="book-card" onclick="openModal('${b.title}')" role="listitem">
                            <div class="cover">📖</div>
                            <div class="info">
                                <h3>${b.title}</h3>
                                <p>${b.author}</p>
                            </div>
                        </div>
                    `).join('');
                }
                const totalPages = Math.ceil((data.total || 0) / PER_PAGE);
                const pag = document.getElementById('pagination');
                if (totalPages <= 1) {
                    pag.innerHTML = `<span class="info-text">Всего ${data.total || 0} книг (LIMIT ${PER_PAGE})</span>`;
                } else {
                    let html = `<button onclick="changePage(-1)" ${currentPage<=1?'disabled':''} aria-label="Предыдущая страница">◀ Назад</button>`;
                    for (let i=1; i<=totalPages; i++) {
                        if (i===1 || i===totalPages || (i>=currentPage-1 && i<=currentPage+1))
                            html += `<button class="${i===currentPage?'active':''}" onclick="goTo(${i})" aria-label="Страница ${i}">${i}</button>`;
                        else if (i===currentPage-2 || i===currentPage+2) html += `<button disabled>…</button>`;
                    }
                    html += `<button onclick="changePage(1)" ${currentPage>=totalPages?'disabled':''} aria-label="Следующая страница">Вперед ▶</button>`;
                    html += `<span class="info-text">${data.total || 0} книг (LIMIT ${PER_PAGE})</span>`;
                    pag.innerHTML = html;
                }
            })
            .catch(err => {
                console.error('Ошибка загрузки:', err);
                const errorDiv = document.getElementById('errorMessage');
                errorDiv.textContent = '❌ Не удалось загрузить данные. Проверьте подключение к серверу.';
                errorDiv.style.display = 'block';
                document.getElementById('bookGrid').innerHTML = '';
                document.getElementById('pagination').innerHTML = '';
            });
    }

    function changePage(d) { currentPage += d; loadBooks(); }
    function goTo(p) { currentPage = p; loadBooks(); }

    function handleSearch() {
        clearTimeout(debounceTimer);
        debounceTimer = setTimeout(() => {
            currentPage = 1;
            loadBooks();
        }, 300);
    }

    function switchTab(tab) {
        document.querySelectorAll('.panel').forEach(p => p.classList.remove('active'));
        document.querySelectorAll('.tabs button').forEach(b => b.classList.remove('active'));
        document.getElementById('panel-' + tab).classList.add('active');
        event.target.classList.add('active');
    }

    function openModal(title) {
        document.getElementById('modalTitle').innerText = 'Бронирование: ' + title;
        document.getElementById('bookingModal').classList.add('show');
    }

    function closeModal() {
        document.getElementById('bookingModal').classList.remove('show');
    }

    document.getElementById('bookingModal').addEventListener('click', function(e) {
        if (e.target === this) closeModal();
    });

    window.onload = loadBooks;
</script>
</body>
</html>
"""


#  МАРШРУТЫ FLASK

@app.route('/')
def index():
    books, total = get_books_from_db()
    return render_template_string(HTML_TEMPLATE, books=books)

@app.route('/api/books')
def api_books():
    search = request.args.get('search', '').strip()
    sort = request.args.get('sort', 'title')
    page = int(request.args.get('page', 1))
    per_page = 20
    books, total = get_books_from_db(search, sort, page, per_page)
    return jsonify({
        'data': books,
        'total': total,
        'page': page,
        'limit': per_page
    })


#  КЭШИРОВАНИЕ СТАТИКИ (для Lighthouse)

@app.after_request
def add_cache_headers(response):
    if request.path.startswith('/static/'):
        response.cache_control.max_age = 86400  # 24 часа
        response.cache_control.public = True
    return response


#  ЗАПУСК

if __name__ == '__main__':
    app.run(debug=True, host='127.0.0.1', port=5000)