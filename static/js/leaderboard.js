/**
 * 홈화면 명예의 전당.
 *
 * 서버가 이미 (점수 → 정확도 → 타수 → 기록순)으로 정렬해서 보내준다.
 * 여기서는 동점자 등수 계산과 표 렌더링만 담당한다.
 */
(function () {
    'use strict';

    var ALL_VIEW_LIMIT = 2000; // 서버 MAX_PAGE_SIZE와 동일

    function Leaderboard() {
        this.modes = [];
        document.querySelectorAll('#modeTab button[data-mode]').forEach(function (tab) {
            this.modes.push(tab.getAttribute('data-mode'));
        }, this);

        this.currentMode = this.modes[0] || '자리';
        this.viewMode = 'top10'; // 'top10' | 'all'
    }

    Leaderboard.prototype.init = function () {
        this.bindEvents();
        this.updateToggleButton();
        this.loadAllCounts();
        this.loadModeData(this.currentMode);
    };

    Leaderboard.prototype.bindEvents = function () {
        var self = this;

        document.querySelectorAll('#modeTab button[data-bs-toggle="tab"]').forEach(function (tab) {
            tab.addEventListener('shown.bs.tab', function (event) {
                var mode = event.target.getAttribute('data-mode');
                if (!mode) return;
                self.currentMode = mode;
                self.loadModeData(mode);
            });
        });

        var toggleButton = document.getElementById('viewToggleBtn');
        if (toggleButton) {
            toggleButton.addEventListener('click', function () {
                self.viewMode = self.viewMode === 'top10' ? 'all' : 'top10';
                self.updateToggleButton();
                self.loadModeData(self.currentMode);
            });
        }
    };

    /** 탭 옆 배지에 모드별 전체 기록 수를 채운다. */
    Leaderboard.prototype.loadAllCounts = function () {
        this.modes.forEach(function (mode) {
            fetch('/api/records?mode=' + encodeURIComponent(mode) + '&limit=1&offset=0')
                .then(readJson)
                .then(function (data) {
                    var countEl = document.getElementById(mode + '-count');
                    if (countEl && data.pagination) {
                        countEl.textContent = data.pagination.total;
                    }
                })
                .catch(function () { /* 배지 숫자는 실패해도 무시한다. */ });
        });
    };

    Leaderboard.prototype.loadModeData = function (mode) {
        var view = this.panelElements(mode);
        if (!view) {
            console.error('순위표 영역을 찾을 수 없습니다:', mode);
            return;
        }

        var isAllView = this.viewMode === 'all';
        var url = isAllView
            ? '/api/records?mode=' + encodeURIComponent(mode) + '&limit=' + ALL_VIEW_LIMIT + '&offset=0'
            : '/api/records/top?mode=' + encodeURIComponent(mode);

        view.loading.style.display = 'block';
        view.content.style.display = 'none';
        view.empty.style.display = 'none';
        view.tbody.innerHTML = '';

        var self = this;
        fetch(url)
            .then(readJson)
            .then(function (data) {
                var records = Array.isArray(data.records) ? data.records : [];

                if (view.count) {
                    view.count.textContent = data.pagination ? data.pagination.total : records.length;
                }

                view.loading.style.display = 'none';

                if (records.length === 0) {
                    view.empty.style.display = 'block';
                    return;
                }

                self.renderRecords(view.tbody, records);
                view.content.style.display = 'block';

                var tableContainer = view.content.querySelector('.table-responsive');
                if (tableContainer) {
                    tableContainer.style.maxHeight = isAllView ? '600px' : '';
                    tableContainer.style.overflowY = isAllView ? 'auto' : '';
                    tableContainer.classList.toggle('dashboard-scroll', isAllView);
                }
            })
            .catch(function (error) {
                console.error(mode + ' 모드 데이터 로딩 실패:', error);

                view.loading.style.display = 'none';
                view.content.style.display = 'none';
                view.empty.style.display = 'block';

                var title = view.empty.querySelector('h5');
                var description = view.empty.querySelector('p');
                if (title) title.textContent = '데이터를 불러올 수 없습니다';
                if (description) {
                    description.textContent = '네트워크 연결을 확인하고 페이지를 새로고침해주세요. ' +
                        '문제가 계속되면 관리자에게 문의하세요.';
                }
            });
    };

    Leaderboard.prototype.panelElements = function (mode) {
        var loading = document.getElementById(mode + '-loading');
        var contentEl = document.getElementById(mode + '-content');
        var empty = document.getElementById(mode + '-empty');
        var tbody = document.getElementById(mode + '-tbody');

        if (!loading || !contentEl || !empty || !tbody) return null;

        return {
            loading: loading,
            content: contentEl,
            empty: empty,
            tbody: tbody,
            count: document.getElementById(mode + '-count')
        };
    };

    Leaderboard.prototype.renderRecords = function (tbody, records) {
        var fragment = document.createDocumentFragment();
        var currentRank = 1;

        records.forEach(function (record, index) {
            if (index > 0) {
                var previous = records[index - 1];
                // 점수·정확도·타수가 모두 같으면 같은 등수(다음 등수는 인원 수만큼 건너뛴다).
                if (record.score !== previous.score ||
                    record.accuracy !== previous.accuracy ||
                    record.wpm !== previous.wpm) {
                    currentRank = index + 1;
                }
            }
            fragment.appendChild(createRecordRow(record, currentRank));
        });

        tbody.innerHTML = '';
        tbody.appendChild(fragment);
    };

    Leaderboard.prototype.updateToggleButton = function () {
        var toggleButton = document.getElementById('viewToggleBtn');
        if (!toggleButton) return;

        if (this.viewMode === 'top10') {
            toggleButton.innerHTML = '<i class="bi bi-list"></i> 전체 보기';
            toggleButton.className = 'btn btn-outline-primary btn-sm';
        } else {
            toggleButton.innerHTML = '<i class="bi bi-trophy"></i> Top10 보기';
            toggleButton.className = 'btn btn-outline-warning btn-sm';
        }
    };

    // --- 렌더링 헬퍼 ------------------------------------------------------
    function createRecordRow(record, rank) {
        var row = document.createElement('tr');

        var rankCell = document.createElement('td');
        rankCell.className = 'text-center';
        if (rank <= 3) {
            var badge = document.createElement('span');
            badge.className = 'badge bg-' + (rank === 1 ? 'warning' : rank === 2 ? 'secondary' : 'dark');
            badge.textContent = rank;
            rankCell.appendChild(badge);
        } else {
            rankCell.textContent = rank;
        }
        row.appendChild(rankCell);

        // textContent를 쓰므로 학생 이름에 특수문자가 있어도 안전하다.
        row.appendChild(cell('td', record.student_id || '', '', 'strong'));
        row.appendChild(cell('td', formatNumber(record.score), 'text-center', 'strong', 'text-warning'));
        row.appendChild(cell('td', formatNumber(record.wpm), 'text-center'));
        row.appendChild(cell('td', formatAccuracy(record.accuracy), 'text-center', 'span', 'text-success'));
        row.appendChild(cell('td', formatDate(record.created_at), 'text-center', 'small', 'text-muted'));

        return row;
    }

    function cell(tagName, text, className, innerTag, innerClassName) {
        var element = document.createElement(tagName);
        if (className) element.className = className;

        if (innerTag) {
            var inner = document.createElement(innerTag);
            if (innerClassName) inner.className = innerClassName;
            inner.textContent = text;
            element.appendChild(inner);
        } else {
            element.textContent = text;
        }
        return element;
    }

    function formatNumber(value) {
        var number = Number(value);
        return Number.isFinite(number) ? String(number) : '-';
    }

    function formatAccuracy(value) {
        var number = Number(value);
        return Number.isFinite(number) ? number.toFixed(1) + '%' : '-';
    }

    function formatDate(value) {
        if (!value) return '-';
        var date = new Date(value);
        if (Number.isNaN(date.getTime())) return '-';

        var month = String(date.getMonth() + 1).padStart(2, '0');
        var day = String(date.getDate()).padStart(2, '0');
        var hours = String(date.getHours()).padStart(2, '0');
        var minutes = String(date.getMinutes()).padStart(2, '0');
        return month + '/' + day + ' ' + hours + ':' + minutes;
    }

    function readJson(response) {
        return response.json()
            .catch(function () {
                throw new Error('HTTP ' + response.status + ' - 서버 응답을 읽을 수 없습니다.');
            })
            .then(function (data) {
                if (!response.ok || data.success === false) {
                    throw new Error(data.error || ('HTTP ' + response.status));
                }
                return data;
            });
    }

    document.addEventListener('DOMContentLoaded', function () {
        if (!document.getElementById('modeTab')) return;
        new Leaderboard().init();
    });
})();
