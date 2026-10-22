
import streamlit as st
import pandas as pd
import requests
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

# -----------------------------------------
# 1. 기본 설정
# -----------------------------------------
st.set_page_config(
    page_title="일별 박스오피스",
    page_icon="🎬",
    layout="wide"
)

st.title("🎬 일별 박스오피스")
st.caption("KOBIS 공식 API로 확인하는 일별 영화 흥행 순위")

# 즐겨찾기 상태 유지
if "favorites" not in st.session_state:
    st.session_state.favorites = set()

# -----------------------------------------
# 2. 날짜 선택
# -----------------------------------------
today = datetime.now(ZoneInfo("Asia/Seoul")).date()
yesterday = today - timedelta(days=1)

st.subheader("📅 조회 날짜 선택")

selected_date = st.date_input(
    "박스오피스를 확인할 날짜",
    value=yesterday,
    min_value=datetime(2004, 1, 1).date(),
    max_value=yesterday,
    format="YYYY-MM-DD"
)

target_date = selected_date.strftime("%Y%m%d")
display_date = selected_date.strftime("%Y년 %m월 %d일")

st.write(f"**조회 기준일: {display_date}**")
st.divider()

# -----------------------------------------
# 3. API 인증키
# -----------------------------------------
try:
    api_key = str(st.secrets["KOBIS_KEY"]).strip()
    if not api_key:
        raise ValueError("빈 인증키")
except Exception:
    st.error(
        "🔑 API 인증키를 찾을 수 없습니다.\n\n"
        "Streamlit Cloud의 Settings → Secrets에 "
        'KOBIS_KEY = "발급받은_본인의_API_인증키"를 등록해 주세요.'
    )
    st.stop()

# -----------------------------------------
# 4. KOBIS API 요청
# -----------------------------------------
url = (
    "https://www.kobis.or.kr/kobisopenapi/"
    "webservice/rest/boxoffice/"
    "searchDailyBoxOfficeList.json"
)

try:
    response = requests.get(
        url,
        params={"key": api_key, "targetDt": target_date},
        timeout=20
    )
    response.raise_for_status()
    data = response.json()

except requests.exceptions.Timeout:
    st.error("⏰ 서버 응답 시간이 초과되었어요. 잠시 후 다시 시도해 주세요.")
    st.stop()

except requests.exceptions.HTTPError as e:
    st.error(f"🌐 HTTP 요청 오류: {e}")
    st.stop()

except requests.exceptions.RequestException as e:
    st.error(f"🌐 네트워크 요청 오류: {e}")
    st.stop()

except ValueError:
    st.error("📄 API 응답을 읽을 수 없어요. 서버 상태를 확인해 주세요.")
    st.stop()

# -----------------------------------------
# 5. API 응답 확인
# -----------------------------------------
if not isinstance(data, dict):
    st.error("API 응답 형식이 올바르지 않습니다.")
    st.stop()

if "faultInfo" in data:
    fault = data["faultInfo"]
    if isinstance(fault, dict):
        code = fault.get("errorCode", "알 수 없음")
        message = fault.get("message", "상세 오류 없음")
    else:
        code = "알 수 없음"
        message = str(fault)

    st.error(f"🚨 KOBIS API 오류\n\n코드: {code}\n\n내용: {message}")
    st.stop()

box_office = data.get("boxOfficeResult")

if not isinstance(box_office, dict):
    st.error("박스오피스 결과를 찾을 수 없습니다.")
    st.stop()

movie_list = box_office.get("dailyBoxOfficeList")

if not isinstance(movie_list, list) or not movie_list:
    st.warning("📭 그날은 아직 집계 전입니다")
    st.caption(
        "해당 날짜의 자료가 아직 제공되지 않았거나 "
        "조회 결과가 없을 수 있습니다. 다른 날짜를 선택해 주세요."
    )
    st.stop()

# -----------------------------------------
# 6. 데이터 변환
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
    name = movie.get("movieNm") or "영화명 없음"
    cumulative = to_number(movie.get("audiAcc"))
    rank_inten = to_number(movie.get("rankInten"))
    old_new = movie.get("rankOldAndNew", "")

    if old_new == "NEW":
        change = "🆕 신규 진입"
    elif rank_inten > 0:
        change = f"🔺 +{rank_inten}"
    elif rank_inten < 0:
        change = f"🔽 {rank_inten}"
    else:
        change = "➖ 0"

    display_name = f"🏆 {name}" if cumulative > 1_000_000 else name

    rows.append({
        "순위": to_number(movie.get("rank")),
        "영화명": name,
        "표시명": display_name,
        "순위 변동": change,
        "개봉일": movie.get("openDt") or "정보 없음",
        "관객수": to_number(movie.get("audiCnt")),
        "누적관객": cumulative,
        "스크린수": to_number(movie.get("scrnCnt"))
    })

df = pd.DataFrame(rows)
df = df.sort_values("순위").reset_index(drop=True)

# 현재 조회 결과에 있는 영화만 즐겨찾기에 표시
movie_names = df["영화명"].tolist()

# -----------------------------------------
# 7. 1위 영화 및 지표 카드
# -----------------------------------------
st.subheader("🏆 해당 날짜의 1위 영화")

first = df.iloc[0]

st.markdown(f"### {first['순위']}위 · {first['표시명']}")
st.caption(f"개봉일: {first['개봉일']}")

c1, c2, c3 = st.columns(3)

c1.metric("🍿 당일 관객수", f"{first['관객수']:,}명")
c2.metric("🎟️ 누적 관객수", f"{first['누적관객']:,}명")
c3.metric("🖥️ 스크린 수", f"{first['스크린수']:,}개")

st.divider()

# -----------------------------------------
# 8. 영화 검색
# -----------------------------------------
st.subheader("🔎 영화 검색")

search_text = st.text_input(
    "영화 제목을 입력하세요",
    placeholder="예: 파묘, 범죄도시"
)

if search_text.strip():
    search_df = df[
        df["영화명"].str.contains(
            search_text.strip(),
            case=False,
            na=False,
            regex=False
        )
    ]
else:
    search_df = df.copy()

if search_df.empty:
    st.info("검색 결과가 없어요. 다른 제목을 입력해 보세요.")
else:
    st.caption(f"검색 결과: {len(search_df)}편")

    search_display = search_df[
        ["순위", "순위 변동", "표시명", "개봉일",
         "관객수", "누적관객", "스크린수"]
    ].rename(columns={"표시명": "영화명"})

    st.dataframe(
        search_display,
        use_container_width=True,
        hide_index=True
    )

st.divider()

# -----------------------------------------
# 9. 즐겨찾기
# -----------------------------------------
st.subheader("⭐ 관심 영화 즐겨찾기")

st.caption(
    "영화를 선택해 추가하거나 삭제할 수 있어요. "
    "즐겨찾기는 현재 세션 동안 유지됩니다."
)

selected_favorite = st.selectbox(
    "관심 영화 선택",
    options=movie_names,
    key="favorite_movie_select"
)

f1, f2 = st.columns(2)

with f1:
    if st.button("⭐ 즐겨찾기에 추가", use_container_width=True):
        st.session_state.favorites.add(selected_favorite)
        st.rerun()

with f2:
    if st.button("🗑️ 즐겨찾기에서 삭제", use_container_width=True):
        st.session_state.favorites.discard(selected_favorite)
        st.rerun()

# 즐겨찾기 중 현재 날짜의 목록에 있는 영화 표시
favorite_names = [
    name for name in movie_names
    if name in st.session_state.favorites
]

if favorite_names:
    favorite_df = df[df["영화명"].isin(favorite_names)].copy()

    favorite_display = favorite_df[
        ["순위", "표시명", "관객수", "누적관객"]
    ].rename(columns={"표시명": "영화명"})

    st.dataframe(
        favorite_display,
        use_container_width=True,
        hide_index=True
    )
else:
    st.info("아직 즐겨찾기에 추가한 영화가 없어요.")

st.divider()

# -----------------------------------------
# 10. 영화 두 편 관객수 비교
# -----------------------------------------
st.subheader("⚖️ 영화 관객수 비교")

st.caption(
    "같은 날짜의 박스오피스에 있는 영화 두 편을 비교합니다."
)

if len(movie_names) >= 2:
    left, right = st.columns(2)

    with left:
        movie_a = st.selectbox(
            "첫 번째 영화",
            options=movie_names,
            index=0,
            key="compare_movie_a"
        )

    with right:
        movie_b = st.selectbox(
            "두 번째 영화",
            options=movie_names,
            index=1,
            key="compare_movie_b"
        )

    if movie_a == movie_b:
        st.warning("서로 다른 영화 두 편을 선택해 주세요.")
    else:
        a = df[df["영화명"] == movie_a].iloc[0]
        b = df[df["영화명"] == movie_b].iloc[0]

        st.markdown("#### 🍿 당일 관객수")

        a1, a2 = st.columns(2)

        a1.metric(
            label=a["표시명"],
            value=f"{a['관객수']:,}명"
        )

        a2.metric(
            label=b["표시명"],
            value=f"{b['관객수']:,}명"
        )

        difference = abs(a["관객수"] - b["관객수"])

        if a["관객수"] > b["관객수"]:
            st.success(
                f"당일 관객수는 {a['영화명']}이(가) "
                f"{difference:,}명 더 많아요."
            )
        elif b["관객수"] > a["관객수"]:
            st.success(
                f"당일 관객수는 {b['영화명']}이(가) "
                f"{difference:,}명 더 많아요."
            )
        else:
            st.info("두 영화의 당일 관객수가 같아요.")

        st.markdown("#### 🎟️ 누적 관객수")

        b1, b2 = st.columns(2)

        b1.metric(
            label=a["표시명"],
            value=f"{a['누적관객']:,}명"
        )

        b2.metric(
            label=b["표시명"],
            value=f"{b['누적관객']:,}명"
        )

        cumulative_difference = abs(
            a["누적관객"] - b["누적관객"]
        )

        if a["누적관객"] > b["누적관객"]:
            st.info(
                f"누적 관객수는 {a['영화명']}이(가) "
                f"{cumulative_difference:,}명 더 많아요."
            )
        elif b["누적관객"] > a["누적관객"]:
            st.info(
                f"누적 관객수는 {b['영화명']}이(가) "
                f"{cumulative_difference:,}명 더 많아요."
            )
        else:
            st.info("두 영화의 누적 관객수가 같아요.")

else:
    st.info("비교할 영화가 두 편 이상 있어야 해요.")

st.divider()

# -----------------------------------------
# 11. 관객수 TOP 5 그래프
# -----------------------------------------
st.subheader("📊 관객수 TOP 5")

top5 = df.nlargest(5, "관객수").copy()
chart_df = top5.set_index("표시명")[["관객수"]]

st.bar_chart(
    chart_df,
    horizontal=True,
    x_label="당일 관객수 (명)",
    y_label="영화명"
)

st.caption("※ 선택한 날짜의 당일 관객수를 기준으로 정렬합니다.")

st.divider()

# -----------------------------------------
# 12. 전체 박스오피스
# -----------------------------------------
st.subheader("🎞️ 전체 일별 박스오피스")

display_df = df[
    ["순위", "순위 변동", "표시명", "개봉일",
     "관객수", "누적관객", "스크린수"]
].rename(columns={"표시명": "영화명"}).copy()

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
# 13. 안내
# -----------------------------------------
st.divider()

st.markdown(
    """
    **📌 표시 안내**

    - 🔺 양수: 전날보다 순위 상승
    - 🔽 음수: 전날보다 순위 하락
    - ➖ 0: 순위 변동 없음
    - 🆕 신규 진입
    - 🏆 누적 관객수 100만 명 초과
    """
)

st.caption(
    "데이터 출처: 영화관입장권통합전산망(KOBIS) 공식 API"
)

st.caption(
    f"조회 날짜: {target_date} · "
    "집계 및 자료 갱신 상황에 따라 결과가 달라질 수 있습니다."
)
