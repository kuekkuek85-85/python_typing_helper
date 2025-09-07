// 메인 페이지 JavaScript

// 페이지 로드 시 초기화
document.addEventListener('DOMContentLoaded', function() {
    initializeMainPage();
});

// 메인 페이지 초기화
async function initializeMainPage() {
    renderPracticeModes();
    await loadLeaderboards();
    setupEventListeners();
}

// 연습 모드 카드 렌더링
function renderPracticeModes() {
    const container = document.getElementById('practice-modes');
    if (!container) return;

    container.innerHTML = '';

    Object.entries(PRACTICE_MODES).forEach(([modeKey, modeData]) => {
        const cardHtml = `
            <div class="col-md-6 col-lg-3">
                <div class="card h-100 mode-card">
                    <div class="card-body text-center">
                        <div class="mode-icon text-${modeData.color} mb-3" style="font-size: 3rem;">
                            ${modeData.icon}
                        </div>
                        <h5 class="card-title">${modeData.title}</h5>
                        <p class="card-text text-muted">
                            ${modeData.description}
                        </p>
                        ${modeData.available ? `
                            <a href="practice.html?mode=${encodeURIComponent(modeKey)}" 
                               class="btn btn-${modeData.color} btn-lg w-100">
                                <i class="bi bi-play-fill"></i>
                                시작하기
                            </a>
                        ` : `
                            <button class="btn btn-${modeData.color} btn-lg w-100 coming-soon-btn" 
                                    data-bs-toggle="modal" data-bs-target="#comingSoonModal">
                                <i class="bi bi-clock"></i>
                                시작하기
                            </button>
                        `}
                    </div>
                </div>
            </div>
        `;
        container.insertAdjacentHTML('beforeend', cardHtml);
    });
}

// 리더보드 탭 생성
function renderLeaderboardTabs() {
    const tabContainer = document.getElementById('modeTab');
    const contentContainer = document.getElementById('modeTabContent');
    
    if (!tabContainer || !contentContainer) return;

    tabContainer.innerHTML = '';
    contentContainer.innerHTML = '';

    Object.entries(PRACTICE_MODES).forEach(([modeKey, modeData], index) => {
        const isActive = index === 0;
        
        // 탭 생성
        const tabHtml = `
            <li class="nav-item" role="presentation">
                <button class="nav-link ${isActive ? 'active' : ''}" 
                        id="${modeKey}-tab" 
                        data-bs-toggle="tab" 
                        data-bs-target="#${modeKey}-pane" 
                        type="button" 
                        role="tab"
                        data-mode="${modeKey}">
                    ${modeData.icon} ${modeData.title}
                    <span class="badge bg-secondary ms-2" id="${modeKey}-count">0</span>
                </button>
            </li>
        `;
        tabContainer.insertAdjacentHTML('beforeend', tabHtml);

        // 탭 컨텐츠 생성
        const contentHtml = `
            <div class="tab-pane fade ${isActive ? 'show active' : ''}" 
                 id="${modeKey}-pane" 
                 role="tabpanel">
                
                <!-- 로딩 상태 -->
                <div class="text-center py-4" id="${modeKey}-loading">
                    <div class="spinner-border text-primary" role="status">
                        <span class="visually-hidden">로딩 중...</span>
                    </div>
                    <p class="mt-2 text-muted">기록을 불러오는 중...</p>
                </div>
                
                <!-- 컨텐츠 영역 -->
                <div id="${modeKey}-content" style="display: none;">
                    <div class="table-responsive" id="${modeKey}-table-container">
                        <table class="table table-hover">
                            <thead>
                                <tr>
                                    <th class="text-center">순위</th>
                                    <th>학생</th>
                                    <th class="text-center">점수</th>
                                    <th class="text-center">분당 타수</th>
                                    <th class="text-center">정확도</th>
                                    <th class="text-center">연습 시간</th>
                                    <th class="text-center">기록 일시</th>
                                </tr>
                            </thead>
                            <tbody id="${modeKey}-tbody">
                                <!-- 동적으로 채워짐 -->
                            </tbody>
                        </table>
                    </div>
                </div>
                
                <!-- 빈 상태 -->
                <div class="text-center py-5" id="${modeKey}-empty" style="display: none;">
                    <i class="bi bi-inbox text-muted" style="font-size: 3rem;"></i>
                    <h5 class="mt-3">아직 기록이 없습니다</h5>
                    <p class="text-muted">${modeData.title}에서 첫 번째 도전자가 되어보세요!</p>
                    ${modeData.available ? `
                        <a href="practice.html?mode=${encodeURIComponent(modeKey)}" class="btn btn-primary">
                            <i class="bi bi-play-fill"></i>
                            ${modeData.title} 시작하기
                        </a>
                    ` : `
                        <button class="btn btn-primary" disabled>
                            <i class="bi bi-clock"></i>
                            준비 중
                        </button>
                    `}
                </div>
            </div>
        `;
        contentContainer.insertAdjacentHTML('beforeend', contentHtml);
    });
}

// 리더보드 데이터 로드
async function loadLeaderboards() {
    renderLeaderboardTabs();
    
    // 기록 수 로드
    const recordCounts = await db.getRecordCounts();
    
    for (const [modeKey, modeData] of Object.entries(PRACTICE_MODES)) {
        const count = recordCounts[modeKey] || 0;
        updateRecordCount(modeKey, count);
        
        if (count > 0) {
            await loadModeLeaderboard(modeKey);
        } else {
            showEmptyState(modeKey);
        }
    }
}

// 모드별 리더보드 로드
async function loadModeLeaderboard(mode) {
    const showAll = Utils.getSession('leaderboard_show_all') || false;
    const limit = showAll ? null : 10;
    
    try {
        const result = await db.getLeaderboard(mode, limit);
        renderLeaderboardTable(mode, result.records);
        hideLoading(mode);
        showContent(mode);
    } catch (error) {
        console.error(`${mode} 리더보드 로드 실패:`, error);
        hideLoading(mode);
        showEmptyState(mode);
    }
}

// 리더보드 테이블 렌더링
function renderLeaderboardTable(mode, records) {
    const tbody = document.getElementById(`${mode}-tbody`);
    if (!tbody) return;

    tbody.innerHTML = '';

    records.forEach(record => {
        const rowHtml = `
            <tr>
                <td class="text-center">
                    ${record.rank <= 3 ? 
                        `<span class="badge bg-${record.rank === 1 ? 'warning' : record.rank === 2 ? 'secondary' : 'dark'}">${record.rank}</span>` :
                        record.rank
                    }
                </td>
                <td>${record.student_id}</td>
                <td class="text-center fw-bold">${record.score}</td>
                <td class="text-center">${record.wpm}</td>
                <td class="text-center">${record.accuracy}%</td>
                <td class="text-center">${Utils.formatTime(record.duration_sec)}</td>
                <td class="text-center">${Utils.formatDate(record.created_at)}</td>
            </tr>
        `;
        tbody.insertAdjacentHTML('beforeend', rowHtml);
    });
}

// UI 상태 관리 함수들
function updateRecordCount(mode, count) {
    const badge = document.getElementById(`${mode}-count`);
    if (badge) {
        badge.textContent = count;
    }
}

function hideLoading(mode) {
    const loading = document.getElementById(`${mode}-loading`);
    if (loading) {
        loading.style.display = 'none';
    }
}

function showContent(mode) {
    const content = document.getElementById(`${mode}-content`);
    if (content) {
        content.style.display = 'block';
    }
}

function showEmptyState(mode) {
    const empty = document.getElementById(`${mode}-empty`);
    const loading = document.getElementById(`${mode}-loading`);
    
    if (loading) loading.style.display = 'none';
    if (empty) empty.style.display = 'block';
}

// 이벤트 리스너 설정
function setupEventListeners() {
    // 전체보기/Top10 토글 버튼
    const viewToggleBtn = document.getElementById('viewToggleBtn');
    if (viewToggleBtn) {
        viewToggleBtn.addEventListener('click', toggleLeaderboardView);
    }

    // 탭 변경 이벤트
    const tabButtons = document.querySelectorAll('[data-bs-toggle="tab"]');
    tabButtons.forEach(tab => {
        tab.addEventListener('shown.bs.tab', function(e) {
            const mode = e.target.dataset.mode;
            if (mode) {
                loadModeLeaderboard(mode);
            }
        });
    });
}

// 리더보드 뷰 토글
async function toggleLeaderboardView() {
    const btn = document.getElementById('viewToggleBtn');
    const showAll = Utils.getSession('leaderboard_show_all') || false;
    const newShowAll = !showAll;
    
    Utils.setSession('leaderboard_show_all', newShowAll);
    
    // 버튼 텍스트 업데이트
    btn.innerHTML = newShowAll ? 
        '<i class="bi bi-trophy"></i> Top 10' : 
        '<i class="bi bi-list"></i> 전체 보기';
    
    // 현재 활성 탭의 데이터 다시 로드
    const activeTab = document.querySelector('.nav-link.active');
    if (activeTab) {
        const mode = activeTab.dataset.mode;
        if (mode) {
            showLoading(mode);
            await loadModeLeaderboard(mode);
        }
    }
}

function showLoading(mode) {
    const loading = document.getElementById(`${mode}-loading`);
    const content = document.getElementById(`${mode}-content`);
    const empty = document.getElementById(`${mode}-empty`);
    
    if (loading) loading.style.display = 'block';
    if (content) content.style.display = 'none';
    if (empty) empty.style.display = 'none';
}

// 관리자 로그인
function loginAdmin() {
    const username = document.getElementById('adminUser').value;
    const password = document.getElementById('adminPass').value;
    
    if (username === ADMIN_CONFIG.username && password === ADMIN_CONFIG.password) {
        Utils.setSession(SESSION_KEY, { 
            username: username, 
            loginTime: new Date().toISOString() 
        });
        
        // 모달 닫기
        const modal = bootstrap.Modal.getInstance(document.getElementById('teacherLoginModal'));
        modal.hide();
        
        // 성공 알림
        alert('관리자 로그인 성공! (현재 버전에서는 추가 기능이 제한됩니다)');
    } else {
        alert('로그인 정보가 올바르지 않습니다.');
    }
}