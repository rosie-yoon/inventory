import streamlit as st
import pandas as pd
from datetime import datetime
import time

# 구글 시트 연결 라이브러리 (st-gsheets-connection 설치 필요)
try:
    from streamlit_gsheets import GSheetsConnection
except ImportError:
    GSheetsConnection = None

# 1. 페이지 설정
st.set_page_config(
    page_title="재고 관리 시스템", 
    layout="wide",
    initial_sidebar_state="collapsed"
)

# 2. 스타일 및 UI 설정
st.markdown("""
    <style>
    .main { background-color: #f8fafc; }
    .sync-box {
        background-color: #ffffff;
        padding: 25px;
        border-radius: 15px;
        border: 1px solid #e2e8f0;
        margin-bottom: 25px;
        box-shadow: 0 4px 6px -1px rgb(0 0 0 / 0.1);
    }
    .status-badge {
        font-size: 12px;
        padding: 6px 14px;
        border-radius: 20px;
        font-weight: bold;
        display: inline-block;
        margin-bottom: 10px;
    }
    /* 수량 조절 섹션 중앙 정렬 */
    .qty-container {
        display: flex;
        align-items: center;
        justify-content: center;
        gap: 15px;
    }
    .qty-text {
        font-size: 1.6rem;
        font-weight: bold;
        min-width: 80px;
        text-align: center;
        color: #1e293b;
    }
    /* 사이드바 강제 숨기기 */
    [data-testid="stSidebar"], [data-testid="stSidebarNav"] { display: none; }
    section[data-testid="stSidebar"] { width: 0px !important; }
    </style>
    """, unsafe_allow_html=True)

# --- 데이터 관리 로직 ---

# 구글 시트 헤더 이름 설정 (사용자 시트와 동일해야 함)
COL_SKU = 'SKU'
COL_NAME = '상품명'
COL_IMG = '이미지URL'
COL_QTY = '현재재고'
COL_DATE = '최근수정일'

if 'inventory' not in st.session_state:
    st.session_state.inventory = pd.DataFrame(columns=[COL_SKU, COL_NAME, COL_IMG, COL_QTY, COL_DATE])

def get_connection():
    if not GSheetsConnection: return None
    try:
        return st.connection("gsheets", type=GSheetsConnection)
    except: return None

def fetch_data():
    conn = get_connection()
    if conn:
        try:
            with st.spinner("구글 시트에서 데이터를 불러오는 중..."):
                # TTL=0으로 설정하여 항상 최신 데이터를 읽어옴
                df = conn.read(ttl=0) 
                if df is not None:
                    df = df.dropna(how='all')
                    # 숫자 데이터 변환
                    if COL_QTY in df.columns:
                        df[COL_QTY] = pd.to_numeric(df[COL_QTY], errors='coerce').fillna(0).astype(int)
                    st.session_state.inventory = df.copy()
                    st.toast("✅ 구글 시트 데이터를 성공적으로 불러왔습니다!")
                    return True
        except Exception as e:
            st.error(f"불러오기 실패: {e}")
    return False

def commit_data():
    conn = get_connection()
    if conn:
        try:
            with st.spinner("구글 시트에 저장 중..."):
                # 현재 앱의 인벤토리 상태를 시트에 덮어쓰기
                conn.update(data=st.session_state.inventory)
                st.success("🚀 구글 시트에 변경사항이 안전하게 저장되었습니다!")
                time.sleep(1)
                st.rerun()
        except Exception as e:
            st.error(f"저장 실패: {e}")
            st.info("💡 시트 공유 설정에서 서비스 계정(streamlit-shopee@...)에 '편집자' 권한을 주었는지 확인하세요.")

# --- 메인 화면 ---
st.title("🍎 스마트 재고 동기화 시스템")

# 상단 제어판
with st.container():
    st.markdown('<div class="sync-box">', unsafe_allow_html=True)
    c1, c2, c3 = st.columns([2, 1, 1])
    with c1:
        st.subheader("🔄 실시간 동기화")
        # 서비스 계정 키 설정 여부 확인
        has_key = "connections" in st.secrets and "gsheets" in st.secrets.connections and "private_key" in st.secrets.connections.gsheets
        if has_key:
            st.markdown('<span class="status-badge" style="background:#dcfce7; color:#166534;">● 클라우드 연결됨</span>', unsafe_allow_html=True)
        else:
            st.markdown('<span class="status-badge" style="background:#fee2e2; color:#991b1b;">● 설정 확인 필요</span>', unsafe_allow_html=True)
    with c2:
        if st.button("📥 불러오기", use_container_width=True):
            if fetch_data(): st.rerun()
    with c3:
        if st.button("💾 최종 저장", type="primary", use_container_width=True):
            commit_data()
    st.markdown('</div>', unsafe_allow_html=True)

tab_list, tab_add = st.tabs(["📊 재고 현황 관리", "➕ 신규 품목 등록"])

with tab_add:
    st.subheader("📦 신규 품목 등록")
    with st.form("add_form", clear_on_submit=True):
        f_sku = st.text_input("SKU (코드)")
        f_name = st.text_input("상품명")
        f_img = st.text_input("이미지 URL (직접 링크)")
        f_qty = st.number_input("현재 재고 수량", min_value=0, step=1)
        if st.form_submit_button("목록에 추가"):
            if f_sku and f_name:
                new_row = pd.DataFrame([[f_sku, f_name, f_img, int(f_qty), datetime.now().strftime("%Y-%m-%d")]], 
                                      columns=[COL_SKU, COL_NAME, COL_IMG, COL_QTY, COL_DATE])
                st.session_state.inventory = pd.concat([st.session_state.inventory, new_row], ignore_index=True).drop_duplicates(COL_SKU, keep='last')
                st.success("목록에 추가되었습니다. 상단의 [최종 저장]을 눌러야 시트에 반영됩니다.")

with tab_list:
    search = st.text_input("🔍 상품명 또는 SKU 검색", "")
    
    df = st.session_state.inventory
    view_df = df[
        df[COL_NAME].astype(str).str.contains(search, case=False, na=False) |
        df[COL_SKU].astype(str).str.contains(search, case=False, na=False)
    ].reset_index(drop=True)

    if view_df.empty:
        st.info("데이터가 없습니다. [불러오기] 버튼을 눌러 시트와 동기화하세요.")
    else:
        # 요약 지표
        m1, m2, m3 = st.columns(3)
        m1.metric("총 품목 수", f"{len(view_df)}개")
        m2.metric("전체 재고량", f"{int(view_df[COL_QTY].sum()):,}개")
        m3.metric("부족 알림 (5개 미만)", f"{len(view_df[view_df[COL_QTY] < 5])}건")
        st.divider()

        # 리스트 출력
        for idx, row in view_df.iterrows():
            real_idx = st.session_state.inventory.index[st.session_state.inventory[COL_SKU] == row[COL_SKU]][0]
            
            with st.container():
                # [이미지] [정보] [수량 컨트롤] 3단 구성
                c_img, c_info, c_ctrl = st.columns([1, 3, 2.5])
                
                with c_img:
                    url = row[COL_IMG] if pd.notna(row[COL_IMG]) and row[COL_IMG] != "" else "https://via.placeholder.com/150?text=No+Image"
                    st.image(url, width=100)
                
                with c_info:
                    st.subheader(row[COL_NAME])
                    st.caption(f"코드: {row[COL_SKU]} | 마지막 수정: {row[COL_DATE]}")
                
                with c_ctrl:
                    # 요청하신 수량 조절 버튼 병렬 배치
                    st.write("") # 상단 여백 조절
                    q_col1, q_col2, q_col3 = st.columns([1, 1.5, 1])
                    with q_col1:
                        if st.button("➖", key=f"down_{row[COL_SKU]}", use_container_width=True):
                            if row[COL_QTY] > 0:
                                st.session_state.inventory.at[real_idx, COL_QTY] -= 1
                                st.session_state.inventory.at[real_idx, COL_DATE] = datetime.now().strftime("%Y-%m-%d")
                                st.rerun()
                    with q_col2:
                        st.markdown(f'<div class="qty-text">{int(row[COL_QTY])}</div>', unsafe_allow_html=True)
                    with q_col3:
                        if st.button("➕", key=f"up_{row[COL_SKU]}", use_container_width=True):
                            st.session_state.inventory.at[real_idx, COL_QTY] += 1
                            st.session_state.inventory.at[real_idx, COL_DATE] = datetime.now().strftime("%Y-%m-%d")
                            st.rerun()
                st.divider()
