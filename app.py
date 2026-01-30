import streamlit as st
import pandas as pd
import calendar
from datetime import datetime
import json
from streamlit_gsheets import GSheetsConnection

# 1. 페이지 설정 및 모바일용 CSS 추가
st.set_page_config(page_title="우리매장 웹 장부", layout="wide")

# 모바일에서 글자가 깨지지 않도록 하는 마법의 스타일 (CSS)
st.markdown("""
    <style>
    /* 모바일 기기(폭 600px 이하)에서만 적용 */
    @media (max-width: 600px) {
        .stMetric { font-size: 0.8rem !important; } /* 지표 글자 크기 축소 */
        .calendar-text { font-size: 10px !important; } /* 달력 안 글자 크기 축소 */
        [data-testid="stHorizontalBlock"] { flex-direction: column !important; } /* 가로 배치를 세로로 변경 */
    }
    /* 달력 칸 높이 조절 */
    .stContainer { padding: 5px !important; }
    </style>
    """, unsafe_allow_html=True)

# 2. 구글 시트 연결
conn = st.connection("gsheets", type=GSheetsConnection)

def load_data():
    try:
        df = conn.read(worksheet="sales", ttl=0)
        if df is None or df.empty:
            return pd.DataFrame(columns=['날짜','홀매출','배달매출','배달건수','예상지급액','비용내역','총비용'])
        df['날짜'] = pd.to_datetime(df['날짜']).dt.date
        return df
    except:
        return pd.DataFrame(columns=['날짜','홀매출','배달매출','배달건수','예상지급액','비용내역','총비용'])

def save_data(new_df):
    conn.update(worksheet="sales", data=new_df)
    st.cache_data.clear()

# --- 입력 로직 ---
if 'temp_costs' not in st.session_state: st.session_state.temp_costs = []

def save_and_clear_callback(input_date):
    h, d, count = st.session_state.input_h_sales, st.session_state.input_d_sales, st.session_state.input_d_count
    pay = d - (d * 0.078) - (count * 3100)
    df = load_data()
    df = df[df['날짜'] != input_date]
    new_row = pd.DataFrame({
        '날짜': [input_date], '홀매출': [h], '배달매출': [d], '배달건수': [count],
        '예상지급액': [pay], '비용내역': [json.dumps(st.session_state.temp_costs, ensure_ascii=False)],
        '총비용': [sum(c['금액'] for c in st.session_state.temp_costs)]
    })
    save_data(pd.concat([df, new_row], ignore_index=True))
    st.toast("저장 완료! ☁️")

# --- 메인 UI ---
df = load_data()

with st.sidebar:
    st.header("📝 실적 기록")
    curr_date = st.date_input("날짜", datetime.now().date())
    st.number_input("홀 매출", key="input_h_sales", step=1000)
    st.number_input("배달 매출", key="input_d_sales", step=1000)
    st.button("💾 저장하기", type="primary", use_container_width=True, on_click=save_and_clear_callback, args=(curr_date,))

st.title("📅 성과 분석")
year = st.selectbox("연도", range(2024, 2030), index=datetime.now().year - 2024)
month = st.selectbox("월", range(1, 13), index=datetime.now().month - 1)

# --- 달력 표시 (PC/모바일 공용 최적화) ---
calendar.setfirstweekday(6)
cal = calendar.monthcalendar(year, month)
days = ["일", "월", "화", "수", "목", "금", "토"]

# 요일 헤더
cols = st.columns(7)
for i, d in enumerate(days):
    color = "#FF4B4B" if i == 0 else ("#1C83E1" if i == 6 else "#31333F")
    cols[i].markdown(f"<p style='text-align:center; font-weight:bold; color:{color}; font-size:12px;'>{d}</p>", unsafe_allow_html=True)

for week in cal:
    cols = st.columns(7)
    for i, day in enumerate(week):
        with cols[i]:
            if day != 0:
                date_obj = datetime(year, month, day).date()
                day_data = df[df['날짜'] == date_obj]
                # 모바일에서 공간 확보를 위해 패딩 줄임
                with st.container(border=True):
                    st.markdown(f"<p style='font-size:12px; font-weight:bold; margin-bottom:2px;'>{day}</p>", unsafe_allow_html=True)
                    if not day_data.empty:
                        row = day_data.iloc[0]
                        # 모바일에서 글자 깨짐 방지용 요약 표시
                        st.markdown(f"""
                            <div style='line-height:1.2;'>
                                <p style='font-size:9px; color:#2E7D32; margin:0;'>H:{row['홀매출']//1000}k</p>
                                <p style='font-size:9px; color:#1C83E1; margin:0;'>D:{row['배달매출']//1000}k</p>
                            </div>
                        """, unsafe_allow_html=True)

# 📊 실적 리포트 (모바일에서 자동으로 세로 정렬됨)
st.divider()
st.subheader("📊 월간 리포트")
m_df = df[(pd.to_datetime(df['날짜']).dt.year == year) & (pd.to_datetime(df['날짜']).dt.month == month)].copy()

if not m_df.empty:
    m_df['총매출'] = m_df['홀매출'] + m_df['배달매출']
    t_sales = m_df['총매출'].sum()
    
    # 지표 카드 (PC 4열 / 모바일 1열 자동 전환)
    c1, c2, c3 = st.columns(3)
    c1.metric("총 매출", f"{t_sales:,}원")
    c2.metric("배달 비중", f"{(m_df['배달매출'].sum()/t_sales*100):.1f}%" if t_sales > 0 else "0%")
    c3.metric("누적 정산액", f"{m_df['예상지급액'].sum():,.0f}원")