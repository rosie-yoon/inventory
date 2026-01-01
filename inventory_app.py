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
    page_title="재고 관리 시스템 (INPUT->OUTPUT)", 
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
    /* 입력창 디자인 조정: 버튼 제거 후 단독 사용 시 최적화 */
    div[data-testid="stNumberInput"] {
        max-width: 150px;
        margin-left: auto;
    }
    div[data-testid="stNumberInput"] input {
        font-size: 1.3rem !important;
        font-weight: bold !important;
        text-align: center !important;
        color: #1e293b !important;
        height: 45px !important;
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
    except Exception as e:
        st.error(f"연결 에러: {e}")
        return None

def fetch_data():
    """INPUT 탭에서 데이터를 불러와서 세션에 저장"""
    conn = get_connection()
    if conn:
        try:
            with st.spinner("구글 시트(INPUT) 로딩 중..."):
                df = conn.read(worksheet="INPUT", ttl=0)
                if df is not None:
                    df = df.dropna(how='all')
                    df.columns = [str(c).strip() for c in df.columns]
                    mapping = {
                        '이미지 URL': COL_IMG, '이미지주소': COL_IMG,
                        '현재 재고': COL_QTY, '수량': COL_QTY, '재고': COL_QTY
                    }
                    df = df.rename(columns=mapping)
                    for col in REQUIRED_COLS:
                        if col not in df.columns:
                            df[col] = 0 if col == COL_QTY else ""
                    df[COL_QTY] = pd.to_numeric(df[COL_QTY], errors='coerce').fillna(0).astype(int)
                    st.session_state.inventory = df[REQUIRED_COLS].copy()
                    st.toast("✅ INPUT 데이터를 성공적으로 불러왔습니다!")
                    return True
        except Exception as e:
            st.error(f"불러오기 실패: {e}")
    return False

def commit_data():
    """세션의 데이터를 OUTPUT 탭에 덮어쓰기 저장"""
    conn = get_connection()
    if conn:
        try:
            with st.spinner("구글 시트(OUTPUT) 저장 중..."):
                conn.update(worksheet="OUTPUT", data=st.session_state.inventory)
                st.success("🚀 OUTPUT 탭에 모든 데이터가 저장되었습니다!")
                time.sleep(1)
                st.rerun()
        except Exception as e:
            st.error(f"저장 실패: {e}")

# --- 메인 화면 ---
st.title("🍎 스마트 재고 관리 (Cloud)")
st.caption("수정된 재고는 즉시 반영되며, 마지막에 'OUTPUT 저장' 버튼을 눌러 확정하세요.")

# 제어판
with st.container():
    st.markdown('<div class="sync-box">', unsafe_allow_html=True)
    c1, c2, c3 = st.columns([2, 1, 1])
    with c1:
        st.subheader("🔄 동기화 제어")
        is_ready = "connections" in st.secrets and "gsheets" in st.secrets.connections
        st.markdown(f'<span class="status-badge" style="background:{"#dcfce7" if is_ready else "#fee2e2"};">● {"연결됨" if is_ready else "설정 필요"}</span>', unsafe_allow_html=True)
    with c2:
        if st.button("📥 INPUT 불러오기", use_container_width=True):
            if fetch_data(): st.rerun()
    with c3:
        if st.button("💾 OUTPUT 저장", type="primary", use_container_width=True):
            commit_data()
    st.markdown('</div>', unsafe_allow_html=True)

# 검색창
search = st.text_input("🔍 품명 또는 SKU 검색", "")
df = st.session_state.inventory

if not df.empty:
    view_df = df[
        df[COL_NAME].astype(str).str.contains(search, case=False, na=False) |
        df[COL_SKU].astype(str).str.contains(search, case=False, na=False)
    ].reset_index(drop=True)
else:
    view_df = pd.DataFrame()

if view_df.empty:
    st.info("데이터가 없습니다. [INPUT 불러오기]를 눌러주세요.")
else:
    m1, m2 = st.columns(2)
    m1.metric("총 품목 수", f"{len(view_df)}개")
    m2.metric("전체 재고 합계", f"{int(view_df[COL_QTY].sum()):,}개")
    st.divider()

    for idx, row in view_df.iterrows():
        try:
            real_idx = st.session_state.inventory.index[st.session_state.inventory[COL_SKU] == row[COL_SKU]][0]
            
            with st.container():
                c_img, c_info, c_qty = st.columns([1, 4, 1.5]) # 레이아웃 조정
                with c_img:
                    url = str(row[COL_IMG]).strip()
                    final_url = url if url.startswith('http') else "https://via.placeholder.com/150?text=No+Image"
                    st.image(final_url, width=100)
                
                with c_info:
                    st.subheader(row[COL_NAME])
                    st.caption(f"SKU: {row[COL_SKU]} | 최근수정: {row[COL_DATE]}")
                
                with c_qty:
                    # 수량 직접 입력창만 단독 배치
                    current_val = int(row[COL_QTY])
                    new_qty = st.number_input(
                        label=f"qty_{row[COL_SKU]}",
                        min_value=0,
                        value=current_val,
                        step=1,
                        key=f"input_{row[COL_SKU]}",
                        label_visibility="collapsed"
                    )
                    
                    if new_qty != current_val:
                        st.session_state.inventory.at[real_idx, COL_QTY] = new_qty
                        st.session_state.inventory.at[real_idx, COL_DATE] = datetime.now().strftime("%Y-%m-%d")
                        st.rerun()
                st.divider()
        except Exception:
            continue
