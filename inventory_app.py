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

# 2. 스타일 설정
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
    .qty-text {
        font-size: 1.6rem;
        font-weight: bold;
        min-width: 80px;
        text-align: center;
        color: #1e293b;
    }
    [data-testid="stSidebar"], [data-testid="stSidebarNav"] { display: none; }
    section[data-testid="stSidebar"] { width: 0px !important; }
    </style>
    """, unsafe_allow_html=True)

# --- 표준 컬럼명 정의 ---
COL_SKU = 'SKU'
COL_NAME = '상품명'
COL_IMG = '이미지URL'
COL_QTY = '현재재고'
COL_DATE = '최근수정일'
REQUIRED_COLS = [COL_SKU, COL_NAME, COL_IMG, COL_QTY, COL_DATE]

if 'inventory' not in st.session_state:
    st.session_state.inventory = pd.DataFrame(columns=REQUIRED_COLS)

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
                    
                    # [유연한 매핑 로직] 헤더 이름에 공백이 있거나 달라도 최대한 찾아냅니다.
                    raw_cols = {str(c).strip().replace(" ", ""): c for c in df.columns}
                    
                    mapping = {}
                    # SKU 찾기
                    mapping[raw_cols.get('SKU', df.columns[0])] = COL_SKU
                    # 상품명 찾기
                    mapping[raw_cols.get('상품명', df.columns[1] if len(df.columns)>1 else '상품명')] = COL_NAME
                    # 이미지URL 찾기 (다양한 변종 대응)
                    img_key = next((c for c in raw_cols if c in ['이미지URL', '이미지주소', '이미지', '사진']), None)
                    mapping[raw_cols.get(img_key, df.columns[2] if len(df.columns)>2 else '이미지URL')] = COL_IMG
                    # 현재재고 찾기
                    qty_key = next((c for c in raw_cols if c in ['현재재고', '재고', '수량', '초기수량']), None)
                    mapping[raw_cols.get(qty_key, df.columns[3] if len(df.columns)>3 else '현재재고')] = COL_QTY
                    # 최근수정일 찾기
                    date_key = next((c for c in raw_cols if c in ['최근수정일', '수정일', '날짜']), None)
                    mapping[raw_cols.get(date_key, df.columns[4] if len(df.columns)>4 else '최근수정일')] = COL_DATE
                    
                    df = df.rename(columns=mapping)
                    
                    # 필수 컬럼 보정
                    for col in REQUIRED_COLS:
                        if col not in df.columns: df[col] = 0 if col == COL_QTY else ""
                    
                    df[COL_QTY] = pd.to_numeric(df[COL_QTY], errors='coerce').fillna(0).astype(int)
                    st.session_state.inventory = df[REQUIRED_COLS].copy()
                    st.toast("✅ 동기화 완료!")
                    return True
        except Exception as e:
            st.error(f"불러오기 실패: {e}")
    return False

def commit_data():
    conn = get_connection()
    if conn:
        try:
            with st.spinner("구글 시트에 저장 중..."):
                # 저장 전 데이터 타입 정리
                save_df = st.session_state.inventory.copy()
                save_df[COL_QTY] = save_df[COL_QTY].astype(int)
                conn.update(data=save_df)
                st.success("🚀 구글 시트 저장이 완료되었습니다!")
                time.sleep(1)
                st.rerun()
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
        is_ready = "connections" in st.secrets and "gsheets" in st.secrets.connections and "private_key" in st.secrets.connections.gsheets
        status_color = "#dcfce7" if is_ready else "#fee2e2"
        status_text = "● 클라우드 연결됨" if is_ready else "● 설정 확인 필요"
        st.markdown(f'<span class="status-badge" style="background:{status_color};">{status_text}</span>', unsafe_allow_html=True)
    with c2:
        if st.button("📥 불러오기", use_container_width=True):
            if fetch_data(): st.rerun()
    with c3:
        if st.button("💾 최종 저장", type="primary", use_container_width=True):
            commit_data()
    st.markdown('</div>', unsafe_allow_html=True)

# [디버깅 도구] 이미지가 안 보일 때 원인 파악용
with st.expander("🛠️ 데이터 진단 도구 (이미지가 안 보일 때 클릭)"):
    st.write("현재 앱이 인식하고 있는 데이터 구조입니다.")
    st.dataframe(st.session_state.inventory.head())
    if not st.session_state.inventory.empty:
        st.write(f"첫 번째 상품 이미지 경로: `{st.session_state.inventory.iloc[0][COL_IMG]}`")

tab_list, tab_add = st.tabs(["📊 재고 현황", "➕ 신규 등록"])

with tab_add:
    st.subheader("📦 신규 품목 등록")
    with st.form("add_form", clear_on_submit=True):
        f_sku = st.text_input("SKU")
        f_name = st.text_input("상품명")
        f_img = st.text_input("이미지 URL")
        f_qty = st.number_input("현재 재고", min_value=0, step=1)
        if st.form_submit_button("목록에 추가"):
            if f_sku and f_name:
                new_row = pd.DataFrame([[f_sku, f_name, f_img, int(f_qty), datetime.now().strftime("%Y-%m-%d")]], 
                                      columns=REQUIRED_COLS)
                st.session_state.inventory = pd.concat([st.session_state.inventory, new_row], ignore_index=True).drop_duplicates(COL_SKU, keep='last')
                st.success("추가되었습니다. [최종 저장]을 눌러주세요.")

with tab_list:
    search = st.text_input("🔍 검색", "")
    df = st.session_state.inventory
    view_df = df[
        df[COL_NAME].astype(str).str.contains(search, case=False, na=False) |
        df[COL_SKU].astype(str).str.contains(search, case=False, na=False)
    ].reset_index(drop=True)

    if view_df.empty:
        st.info("데이터가 없습니다. [불러오기]를 눌러보세요.")
    else:
        for idx, row in view_df.iterrows():
            real_idx = st.session_state.inventory.index[st.session_state.inventory[COL_SKU] == row[COL_SKU]][0]
            with st.container():
                c_img, c_info, c_qty = st.columns([1, 3, 2])
                with c_img:
                    # 이미지 출력 로직 강화
                    img_val = row[COL_IMG]
                    final_url = img_val if pd.notna(img_val) and str(img_val).startswith('http') else "https://via.placeholder.com/150?text=No+Image"
                    st.image(final_url, width=100)
                with c_info:
                    st.subheader(row[COL_NAME])
                    st.caption(f"SKU: {row[COL_SKU]} | 수정일: {row[COL_DATE]}")
                with c_qty:
                    q_col1, q_col2, q_col3 = st.columns([1, 1.5, 1])
                    with q_col1:
                        if st.button("➖", key=f"down_{row[COL_SKU]}", use_container_width=True):
                            if row[COL_QTY] > 0:
                                st.session_state.inventory.at[real_idx, COL_QTY] -= 1
                                st.session_state.inventory.at[real_idx, COL_DATE] = datetime.now().strftime("%Y-%m-%d")
                                st.rerun()
                    with q_col2:
                        st.markdown(f'<div class="qty-text">{int(row[COL_QTY])} 개</div>', unsafe_allow_html=True)
                    with q_col3:
                        if st.button("➕", key=f"up_{row[COL_SKU]}", use_container_width=True):
                            st.session_state.inventory.at[real_idx, COL_QTY] += 1
                            st.session_state.inventory.at[real_idx, COL_DATE] = datetime.now().strftime("%Y-%m-%d")
                            st.rerun()
                st.divider()
