
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
# 배포 서버의 시간대가 한국과 달라도 정확하도록
# Asia/Seoul 시간대를 명시해서 사용해요.
korea_now = datetime.now(ZoneInfo("Asia/Seoul"))
yesterday = (korea_now.date() - timedelta(days=1))
target_date = yesterday.strftime("%Y%m%d")
display_date = yesterday.strftime("%Y년 %m월 %d일")

st.write(f"📅 조회 기준일: **{display_date}**")
st.divider()

# -----------------------------------------
# 3. API 인증키와 요청 주소 설정
# -----------------------------------------
# 인증키는 코드에 직접 적지 않고
# Streamlit Cloud의 Secrets에서 가져와요.
try:
    api_key = st.secrets["KOBIS_KEY"]
except (KeyError, FileNotFoundError):
    st.error(
        "🔑 API 인증키를 찾을 수 없어요.\n\n"
        "Streamlit Cloud의 앱 설정에서 Secrets를 열고 "
        "다음 내용을 추가했는지 확인해 주세요."
    )
    st.code('KOBIS_KEY = "발급받은_본인의_API_인증키"')
    st.stop()

# KOBIS 일별 박스오피스 API 주소
url = (
    "https://www.kobis.or.kr/kobisopenapi/"
    "webservice/rest/boxoffice/"
    "searchDailyBoxOfficeList.json"
)

# 조회 날짜는 위에서 계산한 한국 시간 기준 어제 날짜예요.
params = {
    "key": api_key,
    "targetDt": target_date
}

# -----------------------------------------
# 4. API 요청 및 응답 오류 확인
# -----------------------------------------
try:
    response = requests.get(
        url,
        params=params,
        timeout=15
    )

    # HTTP 요청 자체가 실패했는지 확인해요.
    response.raise_for_status()

    # KOBIS는 인증키가 틀려도 HTTP 상태 코드가
    # 200일 수 있으므로 JSON 내부도 검사해야 해요.
    data = response.json()

except requests.exceptions.Timeout:
    st.error(
        "⏰ API 응답 시간이 초과되었어요.\n\n"
        "인터넷 연결이나 KOBIS 서버 상태를 확인한 뒤 "
        "잠시 후 다시 실행해 주세요."
    )
    st.stop()

except requests.exceptions.HTTPError as e:
    st.error(
        f"🌐 API 요청에 실패했어요. (HTTP 오류: {e})\n\n"
        "요청 주소와 KOBIS 서버 상태를 확인해 주세요."
    )
    st.stop()

except requests.exceptions.RequestException as e:
    st.error(
        f"🌐 네트워크 요청 중 오류가 발생했어요.\n\n"
        f"인터넷 연결과 API 주소를 확인해 주세요.\n\n"
        f"오류 내용: {e}"
    )
    st.stop()

except ValueError:
    st.error(
        "📄 API 응답을 JSON 형식으로 읽을 수 없어요.\n\n"
        "KOBIS 서버의 응답 상태를 확인한 뒤 다시 시도해 주세요."
    )
    st.stop()

# -----------------------------------------
# 5. API 응답 내부의 오류 상자 확인
# -----------------------------------------
# 인증키 오류 등은 HTTP 200이어도 faultInfo로
# 전달될 수 있으므로 먼저 확인해요.
if not isinstance(data, dict):
    st.error(
        "API 응답 형식이 예상과 달라요. "
        "KOBIS API 응답을 확인해 주세요."
    )
    st.stop()

if "faultInfo" in data:
    fault = data["faultInfo"]

    if isinstance(fault, dict):
        error_code = fault.get("errorCode", "알 수 없음")
        error_message = fault.get(
            "message",
            "오류 상세 내용이 제공되지 않았어요."
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
        "확인할 사항\n"
        "1. Secrets에 등록한 KOBIS_KEY가 정확한지 확인하세요.\n"
        "2. KOBIS에서 발급받은 인증키인지 확인하세요.\n"
        "3. API 이용 가능 상태와 요청 주소를 확인하세요."
    )
    st.stop()

# -----------------------------------------
# 6. 영화 목록 가져오기
# -----------------------------------------
box_office = data.get("boxOfficeResult")

if not isinstance(box_office, dict):
    st.error(
        "📭 박스오피스 결과를 찾을 수 없어요.\n\n"
        "API 응답 구조와 KOBIS 서버 상태를 확인해 주세요."
    )
    st.stop()

movie_list = box_office.get("dailyBoxOfficeList")

if not isinstance(movie_list, list) or len(movie_list) == 0:
    st.warning(
        f"📭 {display_date}의 영화 목록이 비어 있어요.\n\n"
        "아직 집계 자료가 제공되지 않았거나 해당 날짜의 "
        "박스오피스 자료가 없을 수 있어요.\n\n"
        "KOBIS에서 해당 날짜의 집계 자료와 API 응답을 확인해 주세요."
    )
    st.stop()

# -----------------------------------------
# 7. 문자열로 받은 숫자를 숫자 자료형으로 변환
# -----------------------------------------
# KOBIS API의 관객수와 스크린 수는 문자열로 오므로
# 그래프와 지표 계산에 사용할 수 있게 변환해요.
def to_number(value):
    try:
        return int(str(value).replace(",", ""))
    except (ValueError, TypeError):
        return 0


rows = []

for movie in movie_list:
    rows.append({
        "순위": to_number(movie.get("rank", 0)),
        "영화명": movie.get("movieNm", "영화명 없음"),
        "개봉일": movie.get("openDt", "") or "정보 없음",
        "관객수": to_number(movie.get("audiCnt", 0)),
        "누적관객": to_number(movie.get("audiAcc", 0)),
        "스크린수": to_number(movie.get("scrnCnt", 0))
    })

df = pd.DataFrame(rows)

# 순위가 빠르거나 관객수가 많은 영화가 위에 오도록 정렬해요.
df = df.sort_values("순위").reset_index(drop=True)

# -----------------------------------------
# 8. 1위 영화 정보와 지표 카드 3개
# -----------------------------------------
st.subheader("🏆 오늘의 1위 영화")

first_movie = df.iloc[0]

st.markdown(
    f"### {first_movie['순위']}위 · {first_movie['영화명']}"
)

st.caption(
    f"개봉일: {first_movie['개봉일']}"
)

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
# 9. 관객수 상위 5편 막대그래프
# -----------------------------------------
st.subheader("📊 관객수 TOP 5")

# 순위가 아니라 실제 관객수를 기준으로 상위 5편을 골라요.
top5 = df.nlargest(5, "관객수").copy()

# 영화명을 그래프의 가로축 항목으로 사용해요.
chart_df = top5.set_index("영화명")[["관객수"]]

st.bar_chart(
    chart_df,
    x_label="영화명",
    y_label="당일 관객수 (명)",
    horizontal=True
)

st.caption(
    "※ 막대 길이는 조회 기준일의 당일 관객수를 나타내요."
)

st.divider()

# -----------------------------------------
# 10. 전체 박스오피스 표
# -----------------------------------------
st.subheader("🎞️ 전체 일별 박스오피스")

# 화면에 표시할 열의 순서와 이름을 지정해요.
display_df = df[
    ["순위", "영화명", "개봉일", "관객수", "누적관객", "스크린수"]
].copy()

# 관객수와 스크린 수를 읽기 편하게 천 단위 쉼표로 표시해요.
for col in ["관객수", "누적관객", "스크린수"]:
    display_df[col] = display_df[col].map(
        lambda x: f"{x:,}"
    )

st.dataframe(
    display_df,
    use_container_width=True,
    hide_index=True
)

# -----------------------------------------
# 11. 데이터 출처와 주의 사항
# -----------------------------------------
st.divider()

st.caption(
    "데이터 출처: 영화관입장권통합전산망(KOBIS) 공식 API"
)

st.caption(
    f"조회 날짜: {target_date} · "
    "자료 집계 및 갱신 상황에 따라 결과가 달라질 수 있어요."
)
