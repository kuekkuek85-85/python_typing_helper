// 홈화면 명예의 전당 JavaScript
class Leaderboard {
    constructor() {
        this.currentMode = '자리';
        this.modes = ['자리', '낱말', '문장', '문단'];
        this.viewMode = 'top10'; // 'top10' 또는 'all'
        
        this.init();
    }

    init() {
        this.initEventListeners();
        this.updateToggleButton();
        this.loadModeData(this.currentMode);
    }

    initEventListeners() {
        // 탭 클릭 이벤트
        document.querySelectorAll('#modeTab button[data-bs-toggle="tab"]').forEach(tab => {
            tab.addEventListener('shown.bs.tab', (event) => {
                const mode = event.target.getAttribute('data-mode');
                this.currentMode = mode;
                this.loadModeData(mode);
            });
        });

        // 전체 보기/Top10 토글 버튼
        const viewToggleBtn = document.getElementById('viewToggleBtn');
        if (viewToggleBtn) {
            viewToggleBtn.addEventListener('click', () => {
                this.toggleViewMode();
            });
        }
    }

    async loadModeData(mode) {
        try {
            const loadingEl = document.getElementById(`${mode}-loading`);
            const contentEl = document.getElementById(`${mode}-content`);
            const emptyEl = document.getElementById(`${mode}-empty`);
            const tbodyEl = document.getElementById(`${mode}-tbody`);
            const countEl = document.getElementById(`${mode}-count`);

            // 로딩 표시
            loadingEl.style.display = 'block';
            contentEl.style.display = 'none';
            emptyEl.style.display = 'none';
            tbodyEl.innerHTML = '';

            // API 호출 (Top10 또는 전체)
            let response;
            if (this.viewMode === 'top10') {
                response = await fetch(`/api/records/top?mode=${encodeURIComponent(mode)}`);
            } else {
                // 전체 보기 모드에서는 모든 기록을 가져옴
                const limit = 10000; // 충분히 큰 수로 모든 기록 확보
                const offset = 0;
                response = await fetch(`/api/records?mode=${encodeURIComponent(mode)}&limit=${limit}&offset=${offset}`);
            }
            
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }
            
            const data = await response.json();
            const records = data.records || [];
            const pagination = data.pagination;

            // 기록 수 업데이트
            if (this.viewMode === 'top10') {
                countEl.textContent = records.length;
            } else {
                countEl.textContent = pagination ? pagination.total : records.length;
            }

            if (records.length === 0) {
                // 빈 상태 표시
                loadingEl.style.display = 'none';
                emptyEl.style.display = 'block';
            } else {
                // 테이블 채우기
                this.renderRecords(tbodyEl, records);
                
                loadingEl.style.display = 'none';
                contentEl.style.display = 'block';
                
                // 전체 보기 모드에서는 스크롤 가능한 높이 설정
                const tableContainer = contentEl.querySelector('.table-responsive');
                if (this.viewMode === 'all') {
                    tableContainer.style.maxHeight = '600px';
                    tableContainer.style.overflowY = 'auto';
                    tableContainer.classList.add('dashboard-scroll');
                } else {
                    tableContainer.style.maxHeight = 'none';
                    tableContainer.style.overflowY = 'visible';
                    tableContainer.classList.remove('dashboard-scroll');
                }
            }

        } catch (error) {
            console.error(`${mode} 모드 데이터 로딩 실패:`, error);
            
            // 에러 상태 표시
            const loadingEl = document.getElementById(`${mode}-loading`);
            const emptyEl = document.getElementById(`${mode}-empty`);
            
            loadingEl.style.display = 'none';
            emptyEl.style.display = 'block';
            
            // 에러 메시지를 빈 상태 영역에 표시
            const emptyContent = emptyEl.querySelector('h5');
            const emptyDesc = emptyEl.querySelector('p');
            
            if (emptyContent && emptyDesc) {
                emptyContent.textContent = '데이터를 불러올 수 없습니다';
                emptyDesc.innerHTML = '네트워크 연결을 확인하고 페이지를 새로고침해주세요.<br>문제가 계속되면 관리자에게 문의하세요.';
            }
        }
    }

    renderRecords(tbody, records) {
        tbody.innerHTML = '';
        
        records.forEach((record, index) => {
            const row = this.createRecordRow(record, index);
            tbody.appendChild(row);
        });
    }

    createRecordRow(record, index) {
        const row = document.createElement('tr');
        
        // 순위 셀
        const rankCell = document.createElement('td');
        rankCell.className = 'text-center';
        
        const rank = index + 1;
        if (rank <= 3) {
            const badge = document.createElement('span');
            badge.className = `badge bg-${rank === 1 ? 'warning' : rank === 2 ? 'secondary' : 'dark'}`;
            badge.textContent = rank;
            rankCell.appendChild(badge);
        } else {
            rankCell.textContent = rank;
        }
        
        // 학생 ID 셀
        const studentCell = document.createElement('td');
        studentCell.innerHTML = `<strong>${this.escapeHtml(record.student_id)}</strong>`;
        
        // 점수 셀
        const scoreCell = document.createElement('td');
        scoreCell.className = 'text-center';
        scoreCell.innerHTML = `<strong class="text-warning">${record.score}</strong>`;
        
        // WPM 셀
        const wpmCell = document.createElement('td');
        wpmCell.className = 'text-center';
        wpmCell.textContent = record.wpm;
        
        // 정확도 셀
        const accuracyCell = document.createElement('td');
        accuracyCell.className = 'text-center';
        accuracyCell.innerHTML = `<span class="text-success">${record.accuracy.toFixed(1)}%</span>`;
        
        // 연습 시간 셀
        const durationCell = document.createElement('td');
        durationCell.className = 'text-center';
        durationCell.textContent = this.formatDuration(record.duration_sec);
        
        // 기록 일시 셀
        const dateCell = document.createElement('td');
        dateCell.className = 'text-center';
        dateCell.innerHTML = `<small class="text-muted">${this.formatDate(record.created_at)}</small>`;
        
        // 행에 셀들 추가
        row.appendChild(rankCell);
        row.appendChild(studentCell);
        row.appendChild(scoreCell);
        row.appendChild(wpmCell);
        row.appendChild(accuracyCell);
        row.appendChild(durationCell);
        row.appendChild(dateCell);
        
        return row;
    }

    toggleViewMode() {
        this.viewMode = this.viewMode === 'top10' ? 'all' : 'top10';
        
        // 현재 활성 탭 다시 로드
        this.loadModeData(this.currentMode);
        
        // 토글 버튼 텍스트 업데이트
        this.updateToggleButton();
    }

    updateToggleButton() {
        const toggleBtn = document.getElementById('viewToggleBtn');
        if (toggleBtn) {
            if (this.viewMode === 'top10') {
                toggleBtn.innerHTML = '<i class="bi bi-list"></i> 전체 보기';
                toggleBtn.className = 'btn btn-outline-primary btn-sm';
            } else {
                toggleBtn.innerHTML = '<i class="bi bi-trophy"></i> Top10 보기';
                toggleBtn.className = 'btn btn-outline-warning btn-sm';
            }
        }
    }

    formatDuration(seconds) {
        const minutes = Math.floor(seconds / 60);
        const secs = seconds % 60;
        return `${minutes}분 ${secs}초`;
    }

    formatDate(dateString) {
        const date = new Date(dateString);
        const month = String(date.getMonth() + 1).padStart(2, '0');
        const day = String(date.getDate()).padStart(2, '0');
        const hours = String(date.getHours()).padStart(2, '0');
        const minutes = String(date.getMinutes()).padStart(2, '0');
        return `${month}/${day} ${hours}:${minutes}`;
    }

    escapeHtml(text) {
        if (typeof text !== 'string') return text;
        return text
            .replace(/&/g, "&amp;")
            .replace(/</g, "&lt;")
            .replace(/>/g, "&gt;")
            .replace(/"/g, "&quot;")
            .replace(/'/g, "&#039;");
    }
}

// 전역 리더보드 인스턴스
let leaderboard;

// DOM 로드 완료 후 리더보드 초기화
document.addEventListener('DOMContentLoaded', () => {
    leaderboard = new Leaderboard();
});