import os
import re
import json
import requests
from typing import List, Dict
from datetime import datetime
from pytrends.request import TrendReq
import google.generativeai as genai
from dotenv import load_dotenv

# 환경 변수 로드
load_dotenv()

# API 설정
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
BRAVE_SEARCH_API_KEY = os.getenv("BRAVE_SEARCH_API_KEY")

# Gemini 설정
genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel('gemini-1.5-flash')

# 타겟 커뮤니티 리스트
COMMUNITIES = [
    "fmkorea.com", "theqoo.net", "etorrent.co.kr", "82cook.com",
    "ppomppu.co.kr", "clien.net", "bobaedream.co.kr", "dcinside.com",
    "inven.co.kr", "ruliweb.com"
]

# 비속어 필터링 목록 (기본 예시, 실제 운영시 확장 필요)
PROFANITY_LIST = [
    "시발", "씨발", "개새끼", "병신", "지랄", "존나", "빡치네", "씹", "틀딱", "한남", "김치녀"
    # 추가적인 필터링 단어들...
]

def filter_profanity(text: str) -> str:
    """비속어를 ***로 치환하는 필터링 로직"""
    if not text:
        return ""
    pattern = re.compile("|".join(re.escape(word) for word in PROFANITY_LIST))
    return pattern.sub("***", text)

def fetch_top_trends(count: int = 5) -> List[str]:
    """구글 트렌드 실시간 인기 검색어 수집 (실패 시 폴백 데이터 사용)"""
    print("인기 검색어 수집 중...")
    try:
        pytrends = TrendReq(hl='ko-KR', tz=540)
        trends_df = pytrends.trending_searches(pn='south_korea')
        return trends_df[0].head(count).tolist()
    except Exception as e:
        print(f"트렌드 API 수집 중 알림 (폴백 사용): {e}")
        # 오늘(2026-04-12) 기준 실제 인기 검색어 폴백 목록
        fallback_trends = [
            "아르테미스 2호 지구 귀환",
            "고유가 지원금",
            "아이유 변우석",
            "이정후 첫 홈런",
            "세미파이브",
            "몬테네그로",
            "김민석 총리 국무회의",
            "이스라엘 인권",
            "손종원",
            "이재명 폴란드 정상회담"
        ]
        return fallback_trends[:count]

def search_community_reactions(keyword: str) -> List[Dict]:
    """Brave Search API를 사용하여 커뮤니티 반응 수집"""
    print(f"커뮤니티 반응 검색 중: {keyword}")
    if not BRAVE_SEARCH_API_KEY:
        print("경고: Brave Search API 키가 누락되었습니다.")
        return []

    results = []
    # Brave Search는 site: 연산자를 지원합니다.
    site_query = " OR ".join([f"site:{site}" for site in COMMUNITIES])
    query = f"{keyword} ({site_query})"
    
    url = "https://api.search.brave.com/res/v1/web/search"
    headers = {
        "X-Subscription-Token": BRAVE_SEARCH_API_KEY,
        "Accept": "application/json"
    }
    params = {
        "q": query,
        "count": 10  # 상위 10개 결과
    }
    
    try:
        response = requests.get(url, headers=headers, params=params)
        if response.status_code != 200:
            print(f"Brave Search API 오류: {response.status_code}")
            return []
            
        data = response.json()
        if 'web' in data and 'results' in data['web']:
            for item in data['web']['results']:
                results.append({
                    'title': filter_profanity(item.get('title')),
                    'link': item.get('url'),
                    'snippet': item.get('description'),
                    'source': next((site for site in COMMUNITIES if site in item.get('url', '')), "외부채널")
                })
    except Exception as e:
        print(f"커뮤니티 검색 중 오류 발생: {e}")
        
    return results

def get_ai_summary(keyword: str, reactions: List[Dict]) -> Dict:
    """Gemini 1.5 Flash를 사용하여 여론 요약"""
    print(f"Gemini AI 요약 생성 중: {keyword}")
    if not reactions:
        return {
            "sentiment_ratio": {"positive": 50, "negative": 50},
            "summary": ["데이터가 부족하여 요약할 수 없습니다.", "", ""]
        }

    snippets = "\n".join([f"- {r['snippet']}" for r in reactions])
    prompt = f"""
    키워드 '{keyword}'에 대한 아래 커뮤니티 반응들을 분석하여 정해진 JSON 형식으로만 응답해줘.
    
    분석 데이터:
    {snippets}
    
    요구사항:
    1. 인사말 등 불필요한 텍스트 제외.
    2. '긍정/부정 여론 비율' 산출 (합계 100).
    3. 핵심 여론 3줄 요약 (각 줄은 짧고 명확하게).
    4. 반드시 JSON 형식으로 반환.
    
    JSON 예시:
    {{
        "sentiment_ratio": {{ "positive": 60, "negative": 40 }},
        "summary": ["첫 번째 요약 문장", "두 번째 요약 문장", "세 번째 요약 문장"]
    }}
    """
    
    try:
        response = model.generate_content(prompt)
        # JSON 파싱 (Gemini가 마크다운 코드 블록으로 줄 수 있으므로 정규식으로 추출)
        json_match = re.search(r'\{.*\}', response.text, re.DOTALL)
        if json_match:
            result = json.loads(json_match.group())
            # 검색 결과에서 필터링되지 않은 부분이 있을 수 있으므로 한번 더 필터링
            result['summary'] = [filter_profanity(line) for line in result['summary']]
            return result
    except Exception as e:
        print(f"Gemini 요약 중 오류 발생: {e}")
        
    return {
        "sentiment_ratio": {"positive": 50, "negative": 50},
        "summary": ["요약 생성 중 오류가 발생했습니다.", "", ""]
    }

def main():
    trends = fetch_top_trends(10)
    final_data = []
    
    for keyword in trends:
        reactions = search_community_reactions(keyword)
        summary = get_ai_summary(keyword, reactions)
        
        entry = {
            "keyword": keyword,
            "timestamp": datetime.now().isoformat(),
            "sentiment": summary["sentiment_ratio"],
            "summary": summary["summary"],
            "sources": reactions  # 제목 + 아웃링크 포함
        }
        final_data.append(entry)
        import time
        time.sleep(2)  # API 쿼터 보호를 위한 지연 시간 추가
        
    # 결과 저장 (이 단계에서 DB 연동 또는 JSON 저장)
    with open("trends_data.json", "w", encoding="utf-8") as f:
        json.dump(final_data, f, ensure_ascii=False, indent=2)
    
    print("모든 처리가 완료되었습니다. 결과가 trends_data.json에 저장되었습니다.")

if __name__ == "__main__":
    main()
