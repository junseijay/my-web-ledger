import streamlit as st
import pandas as pd
import calendar
from datetime import datetime
import json
from streamlit_gsheets import GSheetsConnection

# 1. 페이지 설정 및 모바일 대응 CSS
st.set_page_config(page_title="우리매장 웹 장부", layout="wide")

st.markdown("""
    <style>
    @media (max-width: 768px) {
        .stMetric div div { font-size: 0.8rem !important; }
        [data-testid="column"] { width: 100% !important; flex: 1 1 100% !important; }
    }
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

# --- 3. 세션 초기화 및 로직 ---
for key in ['temp_costs', 'input_h_sales', 'input_d_sales', 'input_d_count', 'input_c_name', 'input_c_amount']:
    if key not in st.session_state:
        st.session_state[key] = [] if key == 'temp_costs' else 0

def add_cost_callback():
    if st.session_state.input_c_name and st.session_state.input_c_amount > 0:
        st.session_state.temp_costs.append({"항목": st.session_state.input_c_name, "금액": st.session_state.input_c_amount})
    st.session_state.input_c_name, st.session_state.input_c_amount = "", 0

def save_and_clear_callback(input_date):
    h, d, count = st.session_state.input_h_sales, st.session_state.input_d_sales, st.session_state.input_d_count
    pay = d - (d * 0.078) - (count * 3100)
    df = load_data()
    df = df[df['날짜'] != input_date]
    new_row = pd.DataFrame({'날짜': [input_date], '홀매출': [h], '배달매출': [d], '배달건수': [count],
                            '예상지급액': [pay], '비용내역': [json.dumps(st.session_state.temp_costs, ensure_ascii=False)],
                            '총비용': [sum(c['금액'] for c in st.session_state.temp_costs)]})
    save_data(pd.concat([df, new_row], ignore_index=True))
    st.session_state.input_h_sales, st.session_state.input_d_sales, st.session_state.input_d_count, st.session_state.temp_costs = 0, 0, 0, []
    st.toast("저장 완료! 💾")

def delete_callback(date_obj):
    df = load_data()
    save_data(df[df['날짜'] != date_obj])
    st.toast("삭제 완료 🗑️")

# --- 4. 메인 화면 ---
df = load_data()

with st.sidebar:
    st.header("📝 오늘의 기록")
    curr_date = st.date_input("날짜 선택", datetime.now().date())
    st.number_input("홀 매출", min_value=0, step=1000, key="input_h_sales")
    st.number_input("배달 매출", min_value=0, step=1000, key="input_d_sales")
    st.number_input("배달 건수", min_value=0, step=1, key="input_d_count")
    st.divider()
    st.text_input("지출 항목명", key="input_c_name")
    st.number_input("지출 금액", min_value=0, step=100, key="input_c_amount")
    st.button("➕ 비용 추가", on_click=add_cost_callback, use_container_width=True)
    st.button("💾 최종 데이터 저장", type="primary", use_container_width=True, on_click=save_and_clear_callback, args=(curr_date,))

st.title("📅 성과 분석 달력")
y_col, m_col = st.columns(2)
year = y_col.selectbox("연도", range(2024, 2030), index=datetime.now().year - 2024)
month = m_col.selectbox("월", range(1, 13), index=datetime.now().month - 1)

calendar.setfirstweekday(6)
cal = calendar.monthcalendar(year, month)
days = ["일", "월", "화", "수", "목", "금", "토"]
h_cols = st.columns(7)
for i, d in enumerate(days):
    color = "#FF4B4B" if i == 0 else ("#1C83E1" if i == 6 else "#31333F")
    h_cols[i].markdown(f"<p style='text-align:center; font-weight:bold; color:{color}; font-size:12px;'>{d}</p>", unsafe_allow_html=True)

for week in cal:
    cols = st.columns(7)
    for i, day in enumerate(week):
        with cols[i]:
            if day != 0:
                date_obj = datetime(year, month, day).date()
                day_data = df[df['날짜'] == date_obj]
                with st.container(border=True):
                    st.write(f"**{day}**")
                    if not day_data.empty:
                        row = day_data.iloc[0]
                        st.markdown(f"<div style='font-size:10px; line-height:1.1;'>"
                                    f"<p style='color:#2E7D32; margin:0;'>홀:{row['홀매출']//1000}k</p>"
                                    f"<p style='color:#1C83E1; margin:0;'>배:{row['배달매출']//1000}k</p>"
                                    f"<p style='color:#D32F2F; margin:0;'>비:{row['총비용']//1000}k</p></div>", unsafe_allow_html=True)
                        if st.button("X", key=f"del_{date_obj}"): delete_callback(date_obj)

# --- 리포트 섹션 ---
st.divider()
st.subheader(f"📊 {month}월 실적 리포트")
m_df = df[(pd.to_datetime(df['날짜']).dt.year == year) & (pd.to_datetime(df['날짜']).dt.month == month)].copy()

if not m_df.empty:
    m_df['당일총매출'] = m_df['홀매출'] + m_df['배달매출']
    total_sales = m_df['당일총매출'].sum()
    c1, c2, c3 = st.columns(3)
    c1.metric("월 총 매출액", f"{total_sales:,}원")
    c2.metric("월 누적 비용", f"{m_df['총비용'].sum():,}원")
    c3.metric("월 누적 순수익", f"{(total_sales - m_df['총비용'].sum()):,}원")
    
    st.markdown("#### 📝 일별 실적 요약")
    summary = m_df[['날짜', '홀매출', '배달매출', '당일총매출', '총비용']].copy()
    if total_sales > 0:
        summary['비용비중'] = (summary['총비용'].cumsum() / total_sales * 100).map("{:.1f}%".format)
    st.dataframe(summary, use_container_width=True, hide_index=True)
else:
    st.info("데이터가 없습니다.")