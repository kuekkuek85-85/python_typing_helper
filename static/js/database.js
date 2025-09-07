// Supabase 데이터베이스 연결 및 쿼리 관리
class DatabaseManager {
    constructor() {
        this.supabase = null;
        this.initialized = false;
    }

    // Supabase 클라이언트 초기화
    async initialize() {
        try {
            // 실제 프로덕션에서는 환경변수나 설정 파일에서 가져와야 함
            if (!SUPABASE_CONFIG.url || SUPABASE_CONFIG.url === 'YOUR_SUPABASE_URL') {
                console.warn('Supabase 설정이 필요합니다. config.js 파일을 확인해주세요.');
                return false;
            }

            this.supabase = supabase.createClient(SUPABASE_CONFIG.url, SUPABASE_CONFIG.key);
            this.initialized = true;
            return true;
        } catch (error) {
            console.error('Supabase 초기화 실패:', error);
            return false;
        }
    }

    // 기록 저장
    async saveRecord(recordData) {
        if (!this.initialized) {
            throw new Error('데이터베이스가 초기화되지 않았습니다.');
        }

        try {
            const { data, error } = await this.supabase
                .from('records')
                .insert([{
                    student_id: recordData.student_id,
                    mode: recordData.mode,
                    wpm: recordData.wpm,
                    accuracy: recordData.accuracy,
                    score: recordData.score,
                    duration_sec: recordData.duration_sec,
                    created_at: new Date().toISOString()
                }]);

            if (error) {
                throw error;
            }

            return { success: true, data };
        } catch (error) {
            console.error('기록 저장 실패:', error);
            throw error;
        }
    }

    // 리더보드 조회
    async getLeaderboard(mode, limit = 10) {
        if (!this.initialized) {
            return { records: [], total: 0 };
        }

        try {
            let query = this.supabase
                .from('records')
                .select('*')
                .eq('mode', mode)
                .order('score', { ascending: false });

            if (limit) {
                query = query.limit(limit);
            }

            const { data, error } = await query;

            if (error) {
                throw error;
            }

            // 순위 계산
            const recordsWithRank = data.map((record, index) => ({
                ...record,
                rank: index + 1
            }));

            return {
                records: recordsWithRank,
                total: data.length
            };
        } catch (error) {
            console.error('리더보드 조회 실패:', error);
            return { records: [], total: 0 };
        }
    }

    // 전체 기록 조회 (교사용)
    async getAllRecords(mode) {
        if (!this.initialized) {
            return { records: [], total: 0 };
        }

        try {
            const { data, error } = await this.supabase
                .from('records')
                .select('*')
                .eq('mode', mode)
                .order('score', { ascending: false });

            if (error) {
                throw error;
            }

            // 순위 계산 (동점자 처리)
            const recordsWithRank = [];
            let currentRank = 1;
            let previousScore = null;

            data.forEach((record, index) => {
                if (previousScore !== null && record.score < previousScore) {
                    currentRank = index + 1;
                }
                
                recordsWithRank.push({
                    ...record,
                    rank: currentRank
                });
                
                previousScore = record.score;
            });

            return {
                records: recordsWithRank,
                total: data.length
            };
        } catch (error) {
            console.error('전체 기록 조회 실패:', error);
            return { records: [], total: 0 };
        }
    }

    // 모드별 기록 수 조회
    async getRecordCounts() {
        if (!this.initialized) {
            return {};
        }

        try {
            const counts = {};
            
            for (const mode of Object.keys(PRACTICE_MODES)) {
                const { count, error } = await this.supabase
                    .from('records')
                    .select('*', { count: 'exact', head: true })
                    .eq('mode', mode);

                if (!error) {
                    counts[mode] = count || 0;
                } else {
                    counts[mode] = 0;
                }
            }

            return counts;
        } catch (error) {
            console.error('기록 수 조회 실패:', error);
            return {};
        }
    }

    // 학생 개인 기록 조회
    async getStudentRecords(studentId) {
        if (!this.initialized) {
            return [];
        }

        try {
            const { data, error } = await this.supabase
                .from('records')
                .select('*')
                .eq('student_id', studentId)
                .order('created_at', { ascending: false });

            if (error) {
                throw error;
            }

            return data || [];
        } catch (error) {
            console.error('학생 기록 조회 실패:', error);
            return [];
        }
    }

    // 기록 삭제 (교사용)
    async deleteRecord(recordId) {
        if (!this.initialized) {
            throw new Error('데이터베이스가 초기화되지 않았습니다.');
        }

        try {
            const { error } = await this.supabase
                .from('records')
                .delete()
                .eq('id', recordId);

            if (error) {
                throw error;
            }

            return { success: true };
        } catch (error) {
            console.error('기록 삭제 실패:', error);
            throw error;
        }
    }

    // 연결 상태 확인
    isConnected() {
        return this.initialized;
    }
}

// 전역 데이터베이스 매니저 인스턴스
const db = new DatabaseManager();

// 페이지 로드 시 데이터베이스 초기화
document.addEventListener('DOMContentLoaded', async function() {
    const connected = await db.initialize();
    if (!connected) {
        console.warn('데이터베이스 연결 실패 - 오프라인 모드로 동작합니다.');
        // 오프라인 모드 알림 표시 (선택적)
        showOfflineNotice();
    }
});

// 오프라인 모드 알림
function showOfflineNotice() {
    const alertHtml = `
        <div class="alert alert-warning alert-dismissible fade show" role="alert" id="offlineAlert">
            <i class="bi bi-wifi-off"></i>
            <strong>오프라인 모드</strong> - 데이터베이스에 연결할 수 없습니다. 연습은 가능하지만 기록이 저장되지 않습니다.
            <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
        </div>
    `;
    
    const container = document.querySelector('.container');
    if (container) {
        container.insertAdjacentHTML('afterbegin', alertHtml);
    }
}