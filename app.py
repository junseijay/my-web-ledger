import streamlit as st
import pandas as pd
import calendar
from datetime import datetime
import json
from streamlit_gsheets import GSheetsConnection

# 1. 페이지 설정
st.set_page_config(page_title="우리매장 웹 장부", layout="wide")

# 2. 구글 시트 연결
try:
    conn = st.connection("gsheets", type=GSheetsConnection)
except Exception as e:
    st.error(f"연결 설정(Secrets) 오류: {e}")
    st.stop()

def load_data():
    try:
        # worksheet="sales" 부분이 구글 시트 하단 탭 이름과 일치해야 합니다.
        df = conn.read(worksheet="sales", ttl=0)
        if df is None or len(df) == 0:
            return pd.DataFrame(columns=['날짜','홀매출','배달매출','배달건수','예상지급액','비용내역','총비용'])
        
        # 데이터 형식 정리
        df['날짜'] = pd.to_datetime(df['날짜']).dt.date
        df[['홀매출', '배달매출', '배달건수', '총비용']] = df[['홀매출', '배달매출', '배달건수', '총비용']].fillna(0).astype(int)
        return df
    except Exception as e:
        # 시트 이름이 다르면 여기서 에러 메시지를 보여줍니다.
        st.sidebar.warning(f"⚠️ 시트 연결 확인 중: {e}")
        return pd.DataFrame(columns=['날짜','홀매출','배달매출','배달건수','예상지급액','비용내역','총비용'])

def save_data(new_df):
    try:
        # 시트에 데이터 쓰기
        conn.update(worksheet="sales", data=new_df)
        st.cache_data.clear()
        return True
    except Exception as e:
        st.error(f"❌ 저장 실패! 원인: {e}")
        st.info("💡 구글 시트 오른쪽 상단 [공유]에서 '편집자' 권한을 주셨는지 확인해 보세요.")
        return False

# --- 세션 상태 초기화 ---
if 'temp_costs' not in st.session_state: st.session_state.temp_costs = []

def save_and_clear_callback(input_date):
    h, d, count = st.session_state.input_h_sales, st.session_state.input_d_sales, st.session_state.input_d_count
    # 배달 수수료 계산 (사장님 기존 공식 적용)
    pay = d - (d * 0.078) - (count * 3100)
    
    df = load_data()
    # 수정 기능을 위해 동일 날짜 데이터는 미리 삭제
    df = df[df['날짜'] != input_date]
    
    new_row = pd.DataFrame({
        '날짜': [input_date],
        '홀매출': [h],
        '배달매출': [d],
        '배달건수': [count],
        '예상지급액': [pay],
        '비용내역': [json.dumps(st.session_state.temp_costs, ensure_ascii=False)],
        '총비용': [sum(c['금액'] for c in st.session_state.temp_costs)]
    })
    
    final_df = pd.concat([df, new_row], ignore_index=True).sort_values('날짜')
    
    if save_data(final_df):
        # 저장 성공 시 입력창 초기화
        st.session_state.input_h_sales = 0
        st.session_state.input_d_sales = 0
        st.session_state.input_d_count = 0
        st.session_state.temp_costs = []
        st.toast("구글 클라우드에 안전하게 저장되었습니다! ✅")

# --- 메인 화면 구성 ---
df = load_data()

with st.sidebar:
    st.header("📝 오늘의 기록")
    curr_date = st.date_input("날짜 선택", datetime.now().date())
    st.number_input("홀 매출액", min_value=0, step=1000, key="input_h_sales")
    st.number_input("배달 매출액(원금)", min_value=0, step=1000, key="input_d_sales")
    st.number_input("배달 건수", min_value=0, step=1, key="input_d_count")
    
    st.divider()
    if st.button("☁️ 데이터 저장하기", type="primary", use_container_width=True):
        save_and_clear_callback(curr_date)

# 달력 UI
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
    h_cols[i].markdown(f"<p style='text-align:center; font-weight:bold; color:{color};'>{d}</p>", unsafe_allow_html=True)

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
                        st.markdown(f"<p style='font-size:11px; color:#2E7D32; margin:0;'>홀:{row['홀매출']:,}</p>", unsafe_allow_html=True)
                        st.markdown(f"<p style='font-size:11px; color:#1C83E1; margin:0;'>배달:{row['배달매출']:,}</p>", unsafe_allow_html=True)

# 실적 리포트
st.divider()
st.subheader(f"📊 {month}월 실적 요약")
m_df = df[(pd.to_datetime(df['날짜']).dt.year == year) & (pd.to_datetime(df['날짜']).dt.month == month)].copy()

if not m_df.empty:
    m_df['당일총매출'] = m_df['홀매출'] + m_df['배달매출']
    t_sales = m_df['당일총매출'].sum()
    t_pay = m_df['예상지급액'].sum()
    
    c1, c2 = st.columns(2)
    c1.metric("월 총 매출액", f"{t_sales:,}원")
    c2.metric("월 배달 예상 정산금", f"{t_pay:,.0f}원")
    st.write("*(배달 정산금은 입력하신 매출에서 수수료와 배달비를 제외한 예상치입니다.)*")
else:
    st.info("해당 월에 저장된 데이터가 없습니다.")