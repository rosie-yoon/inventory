import streamlit as st
import pandas as pd
from datetime import datetime
import time

# 구글 시트 연결 라이브러리
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
    .stNumberInput div div input { font-weight: bold; }
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
    /* 수량 텍스트 중앙 정렬 */
    .qty-text {
        text-align: center;
        font-size: 1.5rem;
        font-weight: bold;
        line-height: 2.2;
    }
    [data-testid="stSidebar"], [data-testid="stSidebarNav"] { display: none; }
    section[data-testid="stSidebar"] { width: 0px !important; }
    </style>
    """, unsafe_allow_html=True)

# --- 데이터 관리 로직 ---

if 'inventory' not in st.session_state:
    st.session_state.inventory = pd.DataFrame(columns=['SKU', '상품명', '이미지URL', '현재재고', '최근수정일'])

def get_gsheets_config():
    if "connections" in st.secrets and "gsheets" in st.secrets.connections:
        return st.secrets.connections.gsheets
    if "gsheets" in st.secrets:
        return st.secrets.gsheets
    return None

def is_write_enabled():
    config = get_gsheets_config()
    return config and "private_key" in config

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
                df = conn.read(ttl=0) 
                if df is not None:
                    df = df.dropna(how='all')
                    rename_map = {
                        'SKU': 'SKU', '상품명': '상품명',
                        '이미지 URL': '이미지URL', '이미지URL': '이미지URL', '이미지 주소': '이미지URL',
                        '초기 수량': '현재재고', '수량': '현재재고', '현재재고': '현재재고',
                        '수정일': '최근수정일', '최근수정일': '최근수정일'
                    }
                    df = df.rename(columns=rename_map)
                    
                    required_cols = ['SKU', '상품명', '이미지URL', '현재재고', '최근수정일']
                    for col in required_cols:
                        if col not in df.columns: df[col] = 0 if col == '현재재고' else ""
                    
                    df['현재재고'] = pd.to_numeric(df['현재재고'], errors='coerce').fillna(0).astype(int)
                    st.session_state.inventory = df[required_cols].copy()
                    st.toast("✅ 동기화 완료!")
                    return True
        except Exception as e:
            st.error(f"데이터 읽기 실패: {e}")
    return False

def commit_data():
    conn = get_connection()
    if conn:
        try:
            with st.spinner("클라우드에 저장 중..."):
                conn.update(data=st.session_state.inventory)
                st.success("🚀 구글 시트 저장이 완료되었습니다!")
        except Exception as e:
            st.error(f"저장 실패: {e}")

# --- 메인 화면 ---
st.title("🍎 스마트 재고 동기화 시스템")

# 제어판
with st.container():
    st.markdown('<div class="sync-box">', unsafe_allow_html=True)
    c1, c2, c3 = st.columns([2, 1, 1])
    with c1:
        st.subheader("🔄 데이터 동기화")
        status_color = "#dcfce7" if is_write_enabled() else "#fee2e2"
        status_text = "● 클라우드 연결됨 (저장 가능)" if is_write_enabled() else "● 읽기 전용 모드"
        st.markdown(f'<span class="status-badge" style="background:{status_color};">{status_text}</span>', unsafe_allow_html=True)
    with c2:
        if st.button("📥 불러오기", use_container_width=True):
            if fetch_data(): st.rerun()
    with c3:
        if st.button("💾 최종 저장", type="primary", use_container_width=True):
            commit_data()
    st.markdown('</div>', unsafe_allow_html=True)

tab_list, tab_add = st.tabs(["📊 재고 현황", "➕ 신규 등록"])

with tab_add:
    st.subheader("📦 신규 품목 추가")
    with st.form("add_form", clear_on_submit=True):
        f_sku = st.text_input("SKU")
        f_name = st.text_input("상품명")
        f_img = st.text_input("이미지 URL")
        f_qty = st.number_input("현재 재고", min_value=0, step=1)
        if st.form_submit_button("목록에 추가"):
            if f_sku and f_name:
                new_row = pd.DataFrame([[f_sku, f_name, f_img, int(f_qty), datetime.now().strftime("%Y-%m-%d")]], 
                                      columns=['SKU', '상품명', '이미지URL', '현재재고', '최근수정일'])
                st.session_state.inventory = pd.concat([st.session_state.inventory, new_row], ignore_index=True).drop_duplicates('SKU', keep='last')
                st.success("추가됨. [최종 저장]을 눌러야 시트에 반영됩니다.")

with tab_list:
    search = st.text_input("🔍 검색", "")
    view_df = st.session_state.inventory[
        st.session_state.inventory['상품명'].astype(str).str.contains(search, case=False, na=False) |
        st.session_state.inventory['SKU'].astype(str).str.contains(search, case=False, na=False)
    ].reset_index(drop=True)

    if view_df.empty:
        st.info("데이터가 없습니다. [불러오기]를 눌러보세요.")
    else:
        for idx, row in view_df.iterrows():
            real_idx = st.session_state.inventory.index[st.session_state.inventory['SKU'] == row['SKU']][0]
            with st.container():
                # 삭제 버튼을 제거하고 레이아웃을 이미지(1), 정보(3), 컨트롤(2)로 조정
                c_img, c_info, c_qty = st.columns([1, 3, 2])
                
                with c_img:
                    url = row['이미지URL'] if '이미지URL' in row and pd.notna(row['이미지URL']) and row['이미지URL'] != "" else "https://via.placeholder.com/100"
                    st.image(url, width=100)
                
                with c_info:
                    st.subheader(row['상품명'])
                    st.caption(f"SKU: {row['SKU']} | 수정일: {row['최근수정일']}")
                
                with c_qty:
                    # 마이너스 버튼, 숫자, 플러스 버튼을 한 줄에 배치
                    q_col1, q_col2, q_col3 = st.columns([1, 1.5, 1])
                    with q_col1:
                        if st.button("➖", key=f"down_{row['SKU']}", use_container_width=True):
                            if row['현재재고'] > 0:
                                st.session_state.inventory.at[real_idx, '현재재고'] -= 1
                                st.session_state.inventory.at[real_idx, '최근수정일'] = datetime.now().strftime("%Y-%m-%d")
                                st.rerun()
                    with q_col2:
                        st.markdown(f'<div class="qty-text">{int(row["현재재고"])} 개</div>', unsafe_allow_html=True)
                    with q_col3:
                        if st.button("➕", key=f"up_{row['SKU']}", use_container_width=True):
                            st.session_state.inventory.at[real_idx, '현재재고'] += 1
                            st.session_state.inventory.at[real_idx, '최근수정일'] = datetime.now().strftime("%Y-%m-%d")
                            st.rerun()
                st.divider()
