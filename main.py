
import streamlit as st
import pandas as pd
import requests
from datetime import date, timedelta

# ==========================================
# 1. 페이지 설정
# ==========================================
st.set_page_config(
    page_title="CINEMA BOX",
    page_icon="🎬",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# ==========================================
# 2. 디자인 CSS
# ==========================================
st.markdown("""
<style>
.stApp {
    background: linear-gradient(180deg, #10111D 0%, #151629 100%);
    color: #F4F3FF;
}

.block-container {
    max-width: 1250px;
    padding-top: 2rem;
    padding-bottom: 3rem;
}

h1, h2, h3, p, label {
    color: #F4F3FF !important;
}

.hero {
    background: linear-gradient(135deg, #292347, #1D2441);
    border: 1px solid #393456;
    border-radius: 24px;
    padding: 30px;
    margin-bottom: 24px;
}

.hero-label {
    color: #C4B5FD;
    font-size: 12px;
    font-weight: 800;
    letter-spacing: 3px;
}

.hero-title {
    color: white;
    font-size: 36px;
    font-weight: 850;
    margin: 10px 0;
}

.hero-desc {
    color: #C2C0DB;
    font-size: 15px;
    line-height: 1.8;
}

div[data-testid="stMetric"] {
    background: #202136;
    border: 1px solid #34344E;
    border-radius: 18px;
    padding: 20px;
    min-height: 120px;
}

div[data-testid="stMetricLabel"] {
    color: #C1BEDD !important;
}

div[data-testid="stMetricValue"] {
    color: #C4B5FD !important;
    font-weight: 800;
}

div[data-baseweb="select"] > div,
div[data-baseweb="input"] > div {
    background-color: #202136 !important;
    border: 1px solid #454361 !important;
    border-radius: 12px !important;
    color: white !important;
}

input {
    color: white !important;
}

.stButton > button {
    background: linear-gradient(135deg, #8B7CF6, #A78BFA);
    color: #171528 !important;
    border: none;
    border-radius: 12px;
    font-weight: 800;
    min-height: 44px;
}

.stButton > button:hover {
    background: #C4B5FD;
    color: #171528 !important;
    border: none;
}

div[data-testid="stDataFrame"] {
    border: 1px solid #34344E;
    border-radius: 14px;
    overflow: hidden;
}

.movie-card {
    background: #202136;
    border: 1px solid #34344E;
    border-radius: 16px;
    padding: 16px;
    margin-bottom: 12px;
    text-align: center;
}

.movie-poster {
    background: linear-gradient(145deg, #343052, #24263F);
    border-radius: 12px;
    height: 190px;
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    color: #C4B5FD;
}

.movie-icon {
    font-size: 48px;
    margin-bottom: 10px;
}

.movie-name {
    font-size: 15px;
    font-weight: 800;
    color: #FFFFFF;
    margin-top: 12px;
    overflow-wrap: anywhere;
}

.movie-info {
    font-size: 12px;
    color: #B8B5D5;
    margin-top: 6px;
}

hr {
    border-color: #34344E !important;
}

div[data-testid="stCaptionContainer"] p {
    color: #A6A5C3 !important;
}

#MainMenu {
    visibility: hidden;
}

footer {
    visibility: hidden;
}

@media (max-width: 700px) {
    .block-container {
        padding: 1rem;
    }

    .hero {
        padding: 22px;
    }

    .hero-title {
        font-size: 28px;
    }
}
</style>
""", unsafe_allow_html=True)

# ==========================================
# 3. 상단 헤더
# ==========================================
st.markdown("""
<div class="hero">
    <div class="hero-label">C I N E M A &nbsp; B O X</div>
    <div class="hero-title">🎬 오늘의 영화 순위</div>
    <div class="hero-desc">
        지금 가장 많은 관객이 보고 있는 영화는 무엇일까요?<br>
        박스오피스 순위와 관객 수를 한눈에 확인해 보세요.
    </div>
</div>
""", unsafe_allow_html=True)

# ==========================================
# 4. KOBIS API 키
# ==========================================
try:
    KOBIS_KEY = st.secrets["KOBIS_KEY"]
except Exception:
    KOBIS_KEY = ""

if not KOBIS_KEY:
    st.error(
        "KOBIS API 키가 설정되지 않았어요. "
        "Streamlit Cloud의 Manage app → Settings → Secrets에서 "
        "KOBIS_KEY를 등록해 주세요."
    )
    st.stop()

# ==========================================
# 5. 공통 함수
# ==========================================
def to_number(value):
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return 0


def get_rank_change(rank_inten, rank_old_and_new):
    if rank_old_and_new == "NEW":
        return "🆕 신규 진입"

    change = to_number(rank_inten)

    if change > 0:
        return f"🔺 {change}계단 상승"
    elif change < 0:
        return f"🔻 {abs(change)}계단 하락"

    return "➖ 순위 유지"


def show_movie_card(movie):
    """API 키 없이 영화 정보를 카드 형태로 표시."""
    st.markdown(
        f"""
        <div class="movie-card">
            <div class="movie-poster">
                <div class="movie-icon">🎬</div>
                <div>NOW SHOWING</div>
            </div>
            <div class="movie-name">{movie['영화명']}</div>
            <div class="movie-info">{movie['순위']}위</div>
            <div class="movie-info">
                관객 {movie['당일 관객 수']:,}명
            </div>
        </div>
        """,
        unsafe_allow_html=True
    )


# ==========================================
# 6. 날짜 선택
# ==========================================
st.markdown("## 📅 날짜별 박스오피스")

yesterday = date.today() - timedelta(days=1)

selected_date = st.date_input(
    "조회할 날짜",
    value=yesterday,
    min_value=date(2004, 1, 1),
    max_value=yesterday
)

target_date = selected_date.strftime("%Y%m%d")

# ==========================================
# 7. KOBIS 데이터 가져오기
# ==========================================
@st.cache_data(ttl=1800, show_spinner=False)
def get_box_office(api_key, target_dt):
    url = (
        "https://www.kobis.or.kr/kobisopenapi/webservice/"
        "rest/boxoffice/searchDailyBoxOfficeList.json"
    )

    response = requests.get(
        url,
        params={
            "key": api_key,
            "targetDt": target_dt
        },
        timeout=15
    )

    response.raise_for_status()
    data = response.json()

    if "faultInfo" in data:
        message = data["faultInfo"].get(
            "message", "KOBIS API 요청에 실패했어요."
        )
        raise ValueError(message)

    return data.get("boxOfficeResult", {}).get(
        "dailyBoxOfficeList", []
    )


try:
    with st.spinner("🎞️ 영화 정보를 불러오는 중..."):
        movies = get_box_office(KOBIS_KEY, target_date)

except (requests.RequestException, ValueError) as error:
    st.error("박스오피스 데이터를 불러오지 못했어요.")
    st.caption(str(error))
    st.stop()

if not movies:
    st.warning(
        "해당 날짜의 자료가 없어요. 다른 날짜를 선택해 주세요."
    )
    st.stop()

# ==========================================
# 8. 데이터 정리
# ==========================================
rows = []

for movie in movies:
    rank = to_number(movie.get("rank"))
    audience = to_number(movie.get("audiCnt"))
    total_audience = to_number(movie.get("audiAcc"))
    name = movie.get("movieNm", "")

    display_name = (
        "🏆 " + name
        if total_audience >= 10_000_000
        else name
    )

    rows.append({
        "순위": rank,
        "영화명": name,
        "표시명": display_name,
        "순위 변동": get_rank_change(
            movie.get("rankInten", 0),
            movie.get("rankOldAndNew", "")
        ),
        "개봉일": movie.get("openDt", ""),
        "당일 관객 수": audience,
        "누적 관객 수": total_audience,
        "스크린 수": to_number(movie.get("scrnCnt", 0)),
        "상영 횟수": to_number(movie.get("showCnt", 0))
    })

df = pd.DataFrame(rows)
df = df.sort_values("순위").reset_index(drop=True)

st.caption(
    f"📆 {selected_date.strftime('%Y년 %m월 %d일')} 기준"
)

# ==========================================
# 9. 주요 지표
# ==========================================
st.markdown("## ✨ 오늘의 기록")

col1, col2, col3 = st.columns(3)

with col1:
    st.metric(
        "🥇 박스오피스 1위",
        df.iloc[0]["영화명"]
    )

with col2:
    st.metric(
        "🎟️ 1위 당일 관객",
        f'{df.iloc[0]["당일 관객 수"]:,}명'
    )

with col3:
    st.metric(
        "👥 TOP 10 관객 합계",
        f'{df["당일 관객 수"].sum():,}명'
    )

# ==========================================
# 10. TOP 5 그래프
# ==========================================
st.markdown("## 📈 관객 수 TOP 5")

top5 = df.head(5).copy()

st.bar_chart(
    top5.set_index("영화명")[["당일 관객 수"]]
)

# ==========================================
# 11. 영화 검색 및 카드
# ==========================================
st.markdown("## 🍿 영화 둘러보기")

search_text = st.text_input(
    "🔎 영화 제목 검색",
    placeholder="궁금한 영화의 제목을 입력하세요"
)

if search_text.strip():
    search_df = df[
        df["영화명"].str.contains(
            search_text.strip(),
            case=False,
            na=False,
            regex=False
        )
    ].copy()
else:
    search_df = df.copy()

if search_df.empty:
    st.info("검색 결과가 없어요. 다른 제목을 입력해 주세요.")
else:
    st.caption(
        "영화 포스터 API 키 없이 표시하는 카드예요. "
        "실제 포스터 이미지는 별도의 이미지 주소가 필요해요."
    )

    card_columns = st.columns(5)

    for index, (_, movie) in enumerate(
        search_df.head(10).iterrows()
    ):
        with card_columns[index % 5]:
            show_movie_card(movie)

    st.markdown("### 검색 결과 목록")

    search_table = search_df[
        [
            "순위", "영화명", "순위 변동", "개봉일",
            "당일 관객 수", "누적 관객 수"
        ]
    ].copy()

    for column in ["당일 관객 수", "누적 관객 수"]:
        search_table[column] = search_table[column].map(
            lambda x: f"{x:,}명"
        )

    st.dataframe(
        search_table,
        use_container_width=True,
        hide_index=True
    )

# ==========================================
# 12. 즐겨찾기
# ==========================================
st.markdown("## ⭐ 나만의 즐겨찾기")

if "favorites" not in st.session_state:
    st.session_state["favorites"] = []

movie_names = df["영화명"].tolist()

favorite_movie = st.selectbox(
    "즐겨찾기에 추가할 영화",
    options=movie_names,
    key="favorite_movie_select"
)

fav_col1, fav_col2 = st.columns(2)

with fav_col1:
    if st.button("⭐ 즐겨찾기 추가", use_container_width=True):
        if favorite_movie not in st.session_state["favorites"]:
            st.session_state["favorites"].append(favorite_movie)
            st.success("즐겨찾기에 추가했어요!")
        else:
            st.info("이미 즐겨찾기에 있는 영화예요.")

with fav_col2:
    if st.button("🗑️ 선택 영화 삭제", use_container_width=True):
        if favorite_movie in st.session_state["favorites"]:
            st.session_state["favorites"].remove(favorite_movie)
            st.success("즐겨찾기에서 삭제했어요.")
        else:
            st.info("해당 영화는 즐겨찾기에 없어요.")

if st.session_state["favorites"]:
    for favorite in st.session_state["favorites"]:
        st.markdown(f"⭐ {favorite}")
else:
    st.caption("아직 즐겨찾기에 추가한 영화가 없어요.")

# ==========================================
# 13. 영화 비교
# ==========================================
st.markdown("## ⚖️ 두 영화 비교하기")

if len(movie_names) >= 2:
    compare_col1, compare_col2 = st.columns(2)

    with compare_col1:
        movie_a = st.selectbox(
            "첫 번째 영화",
            movie_names,
            index=0,
            key="compare_movie_a"
        )

    with compare_col2:
        movie_b = st.selectbox(
            "두 번째 영화",
            movie_names,
            index=1,
            key="compare_movie_b"
        )

    if movie_a == movie_b:
        st.info("서로 다른 두 영화를 선택해 주세요.")
    else:
        data_a = df[df["영화명"] == movie_a].iloc[0]
        data_b = df[df["영화명"] == movie_b].iloc[0]

        compare_a, compare_b = st.columns(2)

        with compare_a:
            show_movie_card(data_a)
            st.metric(
                "당일 관객 수",
                f'{data_a["당일 관객 수"]:,}명'
            )
            st.metric(
                "누적 관객 수",
                f'{data_a["누적 관객 수"]:,}명'
            )

        with compare_b:
            show_movie_card(data_b)
            st.metric(
                "당일 관객 수",
                f'{data_b["당일 관객 수"]:,}명'
            )
            st.metric(
                "누적 관객 수",
                f'{data_b["누적 관객 수"]:,}명'
            )

        difference = (
            data_a["당일 관객 수"] - data_b["당일 관객 수"]
        )

        if difference > 0:
            st.info(
                f"오늘은 {movie_a}의 관객이 "
                f"{difference:,}명 더 많아요."
            )
        elif difference < 0:
            st.info(
                f"오늘은 {movie_b}의 관객이 "
                f"{abs(difference):,}명 더 많아요."
            )
        else:
            st.info("두 영화의 당일 관객 수가 같아요.")

# ==========================================
# 14. 전체 박스오피스 표
# ==========================================
st.markdown("## 🏆 전체 박스오피스")

display_df = df[
    [
        "순위", "표시명", "순위 변동", "개봉일",
        "당일 관객 수", "누적 관객 수",
        "스크린 수", "상영 횟수"
    ]
].copy()

display_df = display_df.rename(
    columns={"표시명": "영화명"}
)

for column in [
    "당일 관객 수", "누적 관객 수",
    "스크린 수", "상영 횟수"
]:
    display_df[column] = display_df[column].map(
        lambda x: f"{x:,}"
    )

st.dataframe(
    display_df,
    use_container_width=True,
    hide_index=True
)

st.caption("🏆 누적 관객 수 1,000만 명 이상인 영화에 표시돼요.")

# ==========================================
# 15. 데이터 출처
# ==========================================
st.divider()

st.markdown("""
<div style="
    background:#1B1C2E;
    border:1px solid #34344E;
    border-radius:16px;
    padding:20px;
">
    <div style="font-size:18px;font-weight:800;color:#C4B5FD">
        ℹ️ DATA SOURCES
    </div>
    <div style="margin-top:10px;color:#C2C0DB;line-height:2">
        박스오피스 데이터:
        <a href="https://www.kobis.or.kr/" target="_blank">
        KOBIS 영화관입장권통합전산망</a>
    </div>
</div>
""", unsafe_allow_html=True)

st.caption("CINEMA BOX · Daily Movie Rankings")
