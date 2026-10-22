
import streamlit as st
import pandas as pd
import requests
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

# -----------------------------------------
# 1. 기본 화면 설정
# -----------------------------------------
st.set_page_config(
    page_title="일별 박스오피스",
    page_icon="🎬",
    layout="wide"
)

st.title("🎬 일별 박스오피스")
st.caption("KOBIS 공식 API로 확인하는 일별 영화 흥행 순위")

# -----------------------------------------
# 2. 날짜 선택
# -----------------------------------------
korea_now = datetime.now(ZoneInfo("Asia/Seoul"))
yesterday = korea_now.date() - timedelta(days=1)

st.subheader("📅 조회 날짜 선택")

selected_date = st.date_input(
    "박스오피스를 확인할 날짜를 선택하세요.",
    value=yesterday,
    max_value=yesterday,
    format="YYYY-MM-DD"
)

target_date = selected_date.strftime("%Y%m%d")
display_date = selected_date.strftime("%Y년 %m월 %d일")

st.write(f"**조회 기준일: {display_date}**")
st.divider()

# -----------------------------------------
# 3. API 인증키 확인
# -----------------------------------------
try:
    api_key = str(st.secrets["KOBIS_KEY"]).strip()

    if not api_key:
        raise ValueError("인증키가 비어 있습니다.")

except Exception:
    st.error(
        "🔑 KOBIS API 인증키를 찾을 수 없습니다.\n\n"
        "Streamlit Cloud의 Settings → Secrets에서 "
        "KOBIS_KEY를 등록해 주세요."
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
    data = response.json()

except requests.exceptions.Timeout:
    st.error(
        "⏰ KOBIS 서버의 응답 시간이 초과되었어요. "
        "잠시 후 다시 실행해 주세요."
    )
    st.stop()

except requests.exceptions.HTTPError as e:
    st.error(f"🌐 HTTP 요청 오류: {e}")
    st.stop()

except requests.exceptions.RequestException as e:
    st.error(f"🌐 네트워크 요청 오류: {e}")
    st.stop()

except ValueError:
    st.error(
        "📄 API 응답을 JSON으로 읽을 수 없어요. "
        "KOBIS 서버 상태를 확인해 주세요."
    )
    st.stop()

# -----------------------------------------
# 5. API 응답 오류 확인
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
        "🚨 KOBIS API 오류\n\n"
        f"오류 코드: {error_code}\n\n"
        f"오류 내용: {error_message}"
    )
    st.info(
        "인증키, API 이용 상태, 요청 제한을 확인해 주세요."
    )
    st.stop()

# -----------------------------------------
# 6. 영화 목록 확인
# -----------------------------------------
box_office = data.get("boxOfficeResult")

if not isinstance(box_office, dict):
    st.error(
        "박스오피스 결과를 찾을 수 없습니다. "
        "KOBIS API 응답을 확인해 주세요."
    )
    st.stop()

movie_list = box_office.get("dailyBoxOfficeList")

if not isinstance(movie_list, list) or len(movie_list) == 0:
    st.warning("📭 그날은 아직 집계 전입니다")
    st.caption(
        "선택한 날짜의 자료가 아직 제공되지 않았거나 "
        "조회 결과가 없을 수 있습니다. "
        "다른 날짜를 선택해 주세요."
    )
    st.stop()

# -----------------------------------------
# 7. 데이터 변환 함수
# -----------------------------------------
def to_number(value):
    try:
        if value is None or str(value).strip() == "":
            return 0
        return int(float(str(value).replace(",", "")))
    except (ValueError, TypeError, OverflowError):
        return 0


def movie_display_name(name, cumulative_audience):
    """누적 관객이 100만 명을 초과하면 트로피 표시"""
    if cumulative_audience > 1_000_000:
        return f"🏆 {name}"
    return name


# -----------------------------------------
# 8. 영화 데이터 정리
# -----------------------------------------
rows = []

for movie in movie_list:
    rank = to_number(movie.get("rank"))
    rank_inten = to_number(movie.get("rankInten"))
    cumulative = to_number(movie.get("audiAcc"))

    # KOBIS의 순위 변동 정보
    rank_old_and_new = movie.get("rankOldAndNew", "")

    if rank_old_and_new == "NEW":
        rank_change = "🆕 신규 진입"
    elif rank_inten > 0:
        rank_change = f"🔺 +{rank_inten}"
    elif rank_inten < 0:
        rank_change = f"🔽 {rank_inten}"
    else:
        rank_change = "➖ 0"

    movie_name = movie.get("movieNm") or "영화명 없음"

    rows.append({
        "순위": rank,
        "영화명": movie_name,
        "표시용 영화명": movie_display_name(
            movie_name, cumulative
        ),
        "순위 변동": rank_change,
        "개봉일": movie.get("openDt") or "정보 없음",
        "관객수": to_number(movie.get("audiCnt")),
        "누적관객": cumulative,
        "스크린수": to_number(movie.get("scrnCnt"))
    })

df = pd.DataFrame(rows)

if df.empty:
    st.warning("📭 그날은 아직 집계 전입니다")
    st.stop()

df = df.sort_values("순위").reset_index(drop=True)

# -----------------------------------------
# 9. 1위 영화 및 지표 카드
# -----------------------------------------
st.subheader("🏆 해당 날짜의 1위 영화")

first_movie = df.iloc[0]

st.markdown(
    f"### {first_movie['순위']}위 · "
    f"{first_movie['표시용 영화명']}"
)

st.caption(f"개봉일: {first_movie['개봉일']}")

card1, card2, card3 = st.columns(3)

with card1:
    st.metric(
        "🍿 당일 관객수",
        f"{first_movie['관객수']:,}명"
    )

with card2:
    st.metric(
        "🎟️ 누적 관객수",
        f"{first_movie['누적관객']:,}명"
    )

with card3:
    st.metric(
        "🖥️ 스크린 수",
        f"{first_movie['스크린수']:,}개"
    )

st.divider()

# -----------------------------------------
# 10. 관객수 TOP 5 그래프
# -----------------------------------------
st.subheader("📊 관객수 TOP 5")

top5 = df.nlargest(5, "관객수").copy()

# 그래프에도 트로피 표시를 적용
chart_df = top5.set_index("표시용 영화명")[["관객수"]]

st.bar_chart(
    chart_df,
    horizontal=True,
    x_label="당일 관객수 (명)",
    y_label="영화명"
)

st.caption(
    "※ 막대 길이는 선택한 날짜의 당일 관객수를 나타냅니다."
)

st.divider()

# -----------------------------------------
# 11. 전체 박스오피스 표
# -----------------------------------------
st.subheader("🎞️ 전체 일별 박스오피스")

display_df = df[
    [
        "순위",
        "순위 변동",
        "표시용 영화명",
        "개봉일",
        "관객수",
        "누적관객",
        "스크린수"
    ]
].copy()

display_df = display_df.rename(
    columns={"표시용 영화명": "영화명"}
)

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
# 12. 순위 변동 및 트로피 안내
# -----------------------------------------
st.divider()

st.markdown(
    """
    **📌 순위 변동 안내**

    - 🔺 양수: 전날보다 순위 상승
    - 🔽 음수: 전날보다 순위 하락
    - ➖ 0: 전날과 순위 동일
    - 🆕 신규 진입: 전날 순위 정보가 신규 진입으로 표시됨
    - 🏆 누적 관객수 100만 명 초과
    """
)

st.caption(
    "데이터 출처: 영화관입장권통합전산망(KOBIS) 공식 API"
)

st.caption(
    f"조회 날짜: {target_date} · "
    "자료 집계 및 갱신 상황에 따라 결과가 달라질 수 있습니다."
)
