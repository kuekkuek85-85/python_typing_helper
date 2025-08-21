// 대시보드 JavaScript
class Dashboard {
    constructor() {
        this.currentMode = '자리';
        this.modes = ['자리', '낱말', '문장', '문단'];
        this.init();
    }

    init() {
        this.initEventListeners();
        this.loadModeData(this.currentMode);
        this.loadStatistics();
    }

    initEventListeners() {
        // 탭 클릭 이벤트
        document.querySelectorAll('[data-bs-toggle="tab"]').forEach(tab => {
            tab.addEventListener('shown.bs.tab', (event) => {
                const mode = event.target.getAttribute('data-mode');
                this.currentMode = mode;
                this.loadModeData(mode);
            });
        });

        // 교사 로그인 버튼 (향후 구현)
        const teacherBtn = document.getElementById('teacherLoginBtn');
        if (teacherBtn) {
            teacherBtn.addEventListener('click', () => {
                // 향후 교사 로그인 모달 표시
                console.log('교사 로그인 기능은 v0.9에서 구현됩니다');
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

            // API 호출
            const response = await fetch(`/api/records/top?mode=${encodeURIComponent(mode)}`);
            
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }
            
            const data = await response.json();
            const records = data.records || [];

            // 기록 수 업데이트
            countEl.textContent = records.length;

            if (records.length === 0) {
                // 빈 상태 표시
                loadingEl.style.display = 'none';
                emptyEl.style.display = 'block';
            } else {
                // 테이블 채우기
                this.renderRecords(tbodyEl, records);
                loadingEl.style.display = 'none';
                contentEl.style.display = 'block';
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
            const row = document.createElement('tr');
            
            // 순위 셀
            const rankCell = document.createElement('td');
            rankCell.className = 'text-center';
            
            if (index < 3) {
                const badge = document.createElement('span');
                badge.className = `badge bg-${index === 0 ? 'warning' : index === 1 ? 'secondary' : 'dark'}`;
                badge.textContent = index + 1;
                rankCell.appendChild(badge);
            } else {
                rankCell.textContent = index + 1;
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
            
            tbody.appendChild(row);
        });
    }

    async loadStatistics() {
        try {
            const response = await fetch('/api/records/stats');
            
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }
            
            const stats = await response.json();
            
            // 통계 업데이트
            document.getElementById('total-students').textContent = stats.total_students || 0;
            document.getElementById('total-records').textContent = stats.total_records || 0;
            document.getElementById('avg-wpm').textContent = stats.avg_wpm ? Math.round(stats.avg_wpm) : 0;
            document.getElementById('avg-accuracy').textContent = stats.avg_accuracy ? `${stats.avg_accuracy.toFixed(1)}%` : '0%';
            
        } catch (error) {
            console.error('통계 데이터 로딩 실패:', error);
            // 기본값 유지 (-)
        }
    }

    formatDuration(seconds) {
        const minutes = Math.floor(seconds / 60);
        const remainingSeconds = seconds % 60;
        return `${minutes}분 ${remainingSeconds}초`;
    }

    formatDate(dateString) {
        if (!dateString) return '-';
        
        try {
            const date = new Date(dateString);
            const month = String(date.getMonth() + 1).padStart(2, '0');
            const day = String(date.getDate()).padStart(2, '0');
            const hour = String(date.getHours()).padStart(2, '0');
            const minute = String(date.getMinutes()).padStart(2, '0');
            
            return `${month}/${day} ${hour}:${minute}`;
        } catch (error) {
            console.error('날짜 포맷팅 오류:', error);
            return '-';
        }
    }

    escapeHtml(unsafe) {
        return unsafe
            .replace(/&/g, "&amp;")
            .replace(/</g, "&lt;")
            .replace(/>/g, "&gt;")
            .replace(/"/g, "&quot;")
            .replace(/'/g, "&#039;");
    }
}

// DOM 로드 완료 후 대시보드 초기화
document.addEventListener('DOMContentLoaded', () => {
    new Dashboard();
});