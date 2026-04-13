document.addEventListener('DOMContentLoaded', () => {
    const feed = document.getElementById('feed');
    const modal = document.getElementById('modal');
    const closeBtn = document.querySelector('.close-btn');

    // 가상 데이터 또는 로컬 JSON 파일에서 데이터 로드
    async function loadTrends() {
        try {
            // 실제 환경에서는 API 엔드포인트 또는 DB 연동 (여기서는 collector.py가 생성한 json 사용 가정)
            const response = await fetch('trends_data.json');
            if (!response.ok) throw new Error('데이터를 불러올 수 없습니다.');
            const data = await response.json();
            renderFeed(data);
        } catch (error) {
            console.error(error);
            // 에러 발생 시 안내 메시지 (또는 테스트용 가상 데이터)
            feed.innerHTML = `<div style="text-align:center; grid-column:1/-1; padding:50px;">
                <p>데이터를 불러오는 중입니다... <code>collector.py</code>를 실행하여 데이터를 생성해주세요.</p>
            </div>`;
        }
    }

    function renderFeed(data) {
        feed.innerHTML = '';
        data.forEach((item, index) => {
            // 3개 카드마다 광고 슬롯 삽입
            if (index > 0 && index % 3 === 0) {
                const adSlot = document.createElement('div');
                adSlot.className = 'ad-placeholder';
                adSlot.innerHTML = '광고 - 네이티브 스폰서 배너';
                feed.appendChild(adSlot);
            }

            const card = document.createElement('div');
            card.className = 'trend-card';
            card.style.animationDelay = `${index * 0.1}s`;

            const posWidth = item.sentiment.positive;
            const negWidth = item.sentiment.negative;

            card.innerHTML = `
                <div class="keyword">
                    <span>${item.keyword}</span>
                    <span class="rank-badge">#${index + 1}</span>
                </div>
                <div class="sentiment-container">
                    <div class="sentiment-bar">
                        <div class="pos" style="width: ${posWidth}%"></div>
                        <div class="neg" style="width: ${negWidth}%"></div>
                    </div>
                    <div class="sentiment-labels">
                        <span class="pos-text">긍정 ${posWidth}%</span>
                        <span class="neg-text">부정 ${negWidth}%</span>
                    </div>
                </div>
                <ul class="summary-list">
                    ${item.summary.map(line => `<li class="summary-item">${line}</li>`).join('')}
                </ul>
            `;

            card.onclick = () => openModal(item);
            feed.appendChild(card);
        });
    }

    function openModal(item) {
        const modalTitle = document.getElementById('modal-title');
        const modalSummary = document.getElementById('modal-summary');
        const modalSources = document.getElementById('modal-sources');

        modalTitle.innerText = `${item.keyword} 여론 분석`;
        modalSummary.innerHTML = `
            <p style="margin-bottom:10px; font-weight:bold;">AI 3줄 요약 리포트</p>
            <ul class="summary-list">
                ${item.summary.map(line => `<li class="summary-item">${line}</li>`).join('')}
            </ul>
        `;

        modalSources.innerHTML = '<h3 style="margin: 20px 0;">커뮤니티별 원문 반응</h3>';
        
        if (item.sources && item.sources.length > 0) {
            item.sources.forEach(source => {
                const sourceItem = document.createElement('div');
                sourceItem.className = 'source-item';
                sourceItem.innerHTML = `
                    <div class="source-info">
                        <h4>${source.title}</h4>
                        <p>${source.source} | 원본 게시글</p>
                    </div>
                    <a href="${source.link}" target="_blank" class="outlink-btn">원문 보기</a>
                `;
                modalSources.appendChild(sourceItem);
            });
        } else {
            modalSources.innerHTML += '<p style="color:var(--text-dim);">검색된 커뮤니티 반응이 없습니다.</p>';
        }

        modal.style.display = 'flex';
        document.body.style.overflow = 'hidden';
    }

    closeBtn.onclick = () => {
        modal.style.display = 'none';
        document.body.style.overflow = 'auto';
    };

    window.onclick = (event) => {
        if (event.target == modal) {
            modal.style.display = 'none';
            document.body.style.overflow = 'auto';
        }
    };

    // 초기 로드
    loadTrends();
});
