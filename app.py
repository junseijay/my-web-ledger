import streamlit as st
import pandas as pd
import calendar
from datetime import datetime
import json
from streamlit_gsheets import GSheetsConnection

# 1. 페이지 설정 및 반응형 CSS 추가
st.set_page_config(page_title="매출 비용 관리 시스템", layout="wide")

# 모바일 호환성을 위한 마법의 CSS
st.markdown("""
    <style>
    /* 모바일 기기 (최대 폭 768px 이하) 설정 */
    @media (max-width: 768px) {
        .main .block-container { padding-left: 1rem; padding-right: 1rem; }
        .stMetric { padding: 5px !important; }
        .stMetric div div { font-size: 0.8rem !important; } /* 지표 숫자 크기 조절 */
        .calendar-text { font-size: 10px !important; }
        /* 가로로 나열된 컬럼들을 모바일에서는 세로로 전환 */
        [data-testid="column"] { width: 100% !important; flex: 1 1 100% !important; }
    }
    /* 달력 칸 안의 글자가 넘치지 않도록 조절 */
    .stContainer { padding: 5px !important; margin: 2px !important; }
    </style>
    """, unsafe_allow_html=True)

# 2. 구글 시트 연결 설정 (기존 데이터 로직 유지)
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

# --- 3. 콜백 및 비즈니스 로직 (기존 유지) ---
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

# 세션 초기화
for key in ['temp_costs', 'input_h_sales', 'input_d_sales', 'input_d_count', 'input_c_name', 'input_c_amount']:
    if key not in st.session_state:
        st.session_state[key] = [] if key == 'temp_costs' else (0 if 'sales' in key or 'count' in key or 'amount' in key else "")

# --- 4. 메인 UI 및 사이드바 ---
df = load_data()

with st.sidebar:
    st.header("📝 오늘의 기록")
    curr_date = st.date_input("날짜 선택", datetime.now().date())
    st.number_input("홀 매출", min_value=0, step=1000, key="input_h_sales")
    st.number_input("배달 매출(원금)", min_value=0, step=1000, key="input_d_sales")
    st.number_input("배달 건수", min_value=0, step=1, key="input_d_count")
    st.divider()
    st.text_input("지출 항목명", key="input_c_name")
    st.number_input("지출 금액", min_value=0, step=100, key="input_c_amount")
    st.button("➕ 비용 추가", on_click=add_cost_callback, use_container_width=True)
    if st.session_state.temp_costs:
        for c in st.session_state.temp_costs: st.caption(f"• {c['항목']}: {c['금액']:,}원")
    st.button("💾 최종 데이터 저장", type="primary", use_container_width=True, on_click=save_and_clear_callback, args=(curr_date,))

# --- 5. 달력 UI (PC 7열 유지 / 모바일 최적화) ---
st.title("📅 월간 성과 분석 달력")
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
                    # 날짜와 삭제버튼
                    st.markdown(f"<div style='display:flex; justify-content:space-between;'><b>{day}</b></div>", unsafe_allow_html=True)
                    if not day_data.empty:
                        row = day_data.iloc[0]
                        # 모바일 가독성을 위해 단위를 k(천원)로 요약 표시 시도하거나 폰트 축소
                        st.markdown(f"""
                            <div style='font-size:10px; line-height:1.1; margin-top:3px;'>
                                <p style='color:#2E7D32; margin:0;'>홀:{row['홀매출']//1000}k</p>
                                <p style='color:#1C83E1; margin:0;'>배:{row['배달매출']//1000}k</p>
                                <p style='color:#D32F2F; margin:0;'>비:{row['총비용']//1000}k</p>
                            </div>
                        """, unsafe_allow_html=True)
                        if st.button("X", key=f"del_{date_obj}"): delete_callback(date_obj)

# --- 6. 종합 분석 리포트 (기존 수식 및 비중 유지) ---
st.divider()
st.subheader(f"📊 {month}월 실적 리포트")
m_df = df[(pd.to_datetime(df['날짜']).dt.year == year) & (pd.to_datetime(df['날짜']).dt.month == month)].sort_values('날짜').copy()

if not m_df.empty:
    m_df['당일총매출'] = m_df['홀매출'] + m_df['배달매출']
    total_sales = m_df['당일총매출'].sum()
    total_h = m_df['홀매출'].sum()
    total_d = m_df['배달매출'].sum()
    total_cost = m_df['총비용'].sum()
    total_profit = total_sales - total_cost
    profit_pct = (total_profit / total_sales * 100) if total_sales > 0 else 0
    
    # 지표 카드 배치 (PC 4열 / 모바일 세로 자동전환)
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("월 총 매출", f"{total_sales:,}원")
    c2.metric("월 홀 매출", f"{total_h:,}원")
    c3.metric("월 배달 매출", f"{total_d:,}원")
    c4.metric("월 배달 정산액", f"{m_df['예상지급액'].sum():,.0f}원")
    
    c5, c6, c7, c8 = st.columns(4)
    c5.metric("월 누적 비용", f"{total_cost:,}원")
    c6.metric("월 누적 순수익", f"{total_profit:,}원")
    c7.metric("월 순수익률", f"{profit_pct:.1f}%")
    c8.empty()

    # 일별 실적 요약
    st.markdown("#### 📝 일별 실적 요약")
    summary = m_df[['날짜', '홀매출', '배달매출', '당일총매출', '총비용']].copy()
    if total_sales > 0:
        summary['순수익률(전체대비)'] = ((summary['당일총매출'] - summary['총비용']).cumsum() / total_sales * 100).map("{:.1f}%".format)
        summary['비용비중(전체대비)'] = (summary['총비용'].cumsum() / total_sales * 100).map("{:.1f}%".format)
    st.dataframe(summary, use_container_width=True, hide_index=True)

    # 지출 항목별 분석 (기존 유지)
    st.markdown("#### 💸 지출 항목별 분석")
    costs_list = []
    for _, row in m_df.iterrows():
        try:
            day_costs = json.loads(row['비용내역'])
            for c in day_costs:
                ratio = (c['금액'] / total_sales * 100) if total_sales > 0 else 0
                costs_list.append({'날짜': row['날짜'], '지출항목': c['항목'], '금액': f"{c['금액']:,}원", '전체매출대비': f"{ratio:.2f}%"})
        except: continue
    
    if costs_list:
        st.table(pd.DataFrame(costs_list).sort_values('날짜'))
else:
    st.info("데이터가 없습니다.")