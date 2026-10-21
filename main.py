
import streamlit as st
import pandas as pd
import requests
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

# -----------------------------------------
# 1. 기본 화면 설정
# -----------------------------------------
st.set_page_config(
    page_title="어제의 박스오피스",
    page_icon="🎬",
    layout="wide"
)

st.title("🎬 어제의 박스오피스")
st.caption("KOBIS 공식 API로 확인하는 일별 영화 흥행 순위")

# -----------------------------------------
# 2. 한국 시간 기준으로 어제 날짜 계산
# -----------------------------------------
korea_now = datetime.now(ZoneInfo("Asia/Seoul"))
yesterday = korea_now.date() - timedelta(days=1)

target_date = yesterday.strftime("%Y%m%d")
display_date = yesterday.strftime("%Y년 %m월 %d일")

st.write(f"📅 조회 기준일: **{display_date}**")
st.divider()

# -----------------------------------------
# 3. API 인증키 확인
# -----------------------------------------
try:
    api_key = st.secrets["KOBIS_KEY"]
    api_key = str(api_key).strip()

    if not api_key:
        raise ValueError("인증키가 비어 있습니다.")

except Exception:
    st.error(
        "🔑 KOBIS API 인증키를 확인할 수 없습니다.\n\n"
        "Streamlit Cloud의 앱 설정 → Secrets에서 "
        "다음 내용을 등록해 주세요."
    )
    st.code('KOBIS_KEY = "발급받은_본인의_API_인증키"')
    st.stop()

# -----------------------------------------
# 4. KOBIS API 요청
# -----------------------------------------
url = (
    "https://www.kobis.or.kr/kobisopenapi/"
    "webservice/rest/boxoffice/"
    "searchDailyBoxOfficeList.json"
)

params = {
    "key": api_key,
    "targetDt": target_date
}

try:
    response = requests.get(
        url,
        params=params,
        timeout=20
    )

    response.raise_for_status()

    try:
        data = response.json()
    except ValueError:
        st.error(
            "📄 KOBIS 서버가 올바른 JSON 응답을 보내지 않았어요.\n\n"
            "잠시 후 다시 실행해 주세요."
        )
        st.stop()

except requests.exceptions.Timeout:
    st.error(
        "⏰ KOBIS 서버의 응답 시간이 초과되었어요.\n\n"
        "잠시 후 다시 실행해 주세요."
    )
    st.stop()

except requests.exceptions.HTTPError as e:
    st.error(
        f"🌐 HTTP 요청 오류가 발생했어요.\n\n"
        f"상세 내용: {e}"
    )
    st.stop()

except requests.exceptions.RequestException as e:
    st.error(
        "🌐 네트워크 요청에 실패했어요.\n\n"
        f"상세 내용: {e}"
    )
    st.stop()

# -----------------------------------------
# 5. API 응답 및 인증 오류 확인
# -----------------------------------------
if not isinstance(data, dict):
    st.error("API 응답 형식이 올바르지 않습니다.")
    st.stop()

if "faultInfo" in data:
    fault = data["faultInfo"]

    if isinstance(fault, dict):
        error_code = fault.get("errorCode", "알 수 없음")
        error_message = fault.get(
            "message",
            "상세 오류 메시지가 없습니다."
        )
    else:
        error_code = "알 수 없음"
        error_message = str(fault)

    st.error(
        "🚨 KOBIS API에서 오류를 반환했어요.\n\n"
        f"오류 코드: {error_code}\n\n"
        f"오류 내용: {error_message}"
    )

    st.info(
        "확인 사항:\n"
        "1. KOBIS_KEY가 정확한지 확인하세요.\n"
        "2. KOBIS에서 발급받은 인증키인지 확인하세요.\n"
        "3. API 이용 상태와 요청 제한을 확인하세요."
    )
    st.stop()

# -----------------------------------------
# 6. 영화 목록 확인
# -----------------------------------------
box_office = data.get("boxOfficeResult")

if not isinstance(box_office, dict):
    st.error(
        "📭 박스오피스 결과를 찾을 수 없어요.\n\n"
        "KOBIS API 응답을 확인해 주세요."
    )
    st.stop()

movie_list = box_office.get("dailyBoxOfficeList")

if not isinstance(movie_list, list) or not movie_list:
    st.warning(
        f"📭 {display_date}의 영화 목록이 비어 있어요.\n\n"
        "해당 날짜의 집계 자료가 아직 제공되지 않았거나 "
        "조회 결과가 없을 수 있어요."
    )
    st.stop()

# -----------------------------------------
# 7. 데이터 정리
# -----------------------------------------
def to_number(value):
    try:
        if value is None or str(value).strip() == "":
            return 0
        return int(float(str(value).replace(",", "")))
    except (ValueError, TypeError, OverflowError):
        return 0


rows = []

for movie in movie_list:
    rows.append({
        "순위": to_number(movie.get("rank")),
        "영화명": movie.get("movieNm") or "영화명 없음",
        "개봉일": movie.get("openDt") or "정보 없음",
        "관객수": to_number(movie.get("audiCnt")),
        "누적관객": to_number(movie.get("audiAcc")),
        "스크린수": to_number(movie.get("scrnCnt"))
    })

df = pd.DataFrame(rows)

if df.empty:
    st.warning("표시할 영화 데이터가 없습니다.")
    st.stop()

df = df.sort_values("순위").reset_index(drop=True)

# -----------------------------------------
# 8. 1위 영화 및 지표 카드
# -----------------------------------------
st.subheader("🏆 조회 날짜의 1위 영화")

first_movie = df.iloc[0]

st.markdown(
    f"### {first_movie['순위']}위 · {first_movie['영화명']}"
)

st.caption(f"개봉일: {first_movie['개봉일']}")

card1, card2, card3 = st.columns(3)

with card1:
    st.metric(
        label="🍿 당일 관객수",
        value=f"{first_movie['관객수']:,}명"
    )

with card2:
    st.metric(
        label="🎟️ 누적 관객수",
        value=f"{first_movie['누적관객']:,}명"
    )

with card3:
    st.metric(
        label="🖥️ 스크린 수",
        value=f"{first_movie['스크린수']:,}개"
    )

st.divider()

# -----------------------------------------
# 9. 관객수 TOP 5 그래프
# -----------------------------------------
st.subheader("📊 관객수 TOP 5")

top5 = df.nlargest(5, "관객수").copy()
chart_df = top5.set_index("영화명")[["관객수"]]

st.bar_chart(
    chart_df,
    horizontal=True,
    x_label="당일 관객수 (명)",
    y_label="영화명"
)

st.caption(
    "※ 막대 길이는 조회 기준일의 당일 관객수를 나타냅니다."
)

st.divider()

# -----------------------------------------
# 10. 전체 박스오피스 표
# -----------------------------------------
st.subheader("🎞️ 전체 일별 박스오피스")

display_df = df[
    ["순위", "영화명", "개봉일", "관객수", "누적관객", "스크린수"]
].copy()

for col in ["관객수", "누적관객", "스크린수"]:
    display_df[col] = display_df[col].map(
        lambda value: f"{value:,}"
    )

st.dataframe(
    display_df,
    use_container_width=True,
    hide_index=True
)

# -----------------------------------------
# 11. 데이터 출처
# -----------------------------------------
st.divider()

st.caption(
    "데이터 출처: 영화관입장권통합전산망(KOBIS) 공식 API"
)

st.caption(
    f"조회 날짜: {target_date} · "
    "집계 및 자료 갱신 상황에 따라 결과가 달라질 수 있습니다."
)
