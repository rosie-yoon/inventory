import streamlit as st
import pandas as pd
from datetime import datetime
import time

# 구글 시트 연결 라이브러리 (st-gsheets-connection)
try:
    from streamlit_gsheets import GSheetsConnection
except ImportError:
    GSheetsConnection = None

# 1. 페이지 설정
st.set_page_config(
    page_title="재고 관리 시스템 (Cloud)", 
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
    .qty-text {
        font-size: 1.6rem;
        font-weight: bold;
        min-width: 80px;
        text-align: center;
        color: #1e293b;
    }
    /* 사이드바 숨기기 */
    [data-testid="stSidebar"], [data-testid="stSidebarNav"] { display: none; }
    section[data-testid="stSidebar"] { width: 0px !important; }
    </style>
    """, unsafe_allow_html=True)

# --- 표준 컬럼명 정의 (제공해주신 구글 시트 헤더와 100% 일치) ---
COL_SKU = 'SKU'
COL_NAME = '상품명'
COL_IMG = '이미지URL'
COL_QTY = '현재재고'
COL_DATE = '최근수정일'
REQUIRED_COLS = [COL_SKU, COL_NAME, COL_IMG, COL_QTY, COL_DATE]

# 세션 상태 초기화
if 'inventory' not in st.session_state:
    st.session_state.inventory = pd.DataFrame(columns=REQUIRED_COLS)

def get_connection():
    if not GSheetsConnection: return None
    try:
        return st.connection("gsheets", type=GSheetsConnection)
    except: return None

def fetch_data():
    """INPUT 시트에서 원본 데이터를 불러옵니다."""
    conn = get_connection()
    if conn:
        try:
            with st.spinner("구글 시트(INPUT)에서 데이터를 불러오는 중..."):
                # 시트의 'INPUT' 워크시트에서 데이터 읽기
                df = conn.read(worksheet="INPUT", ttl=0)
                if df is not None:
                    # 빈 행 제거
                    df = df.dropna(how='all')
                    
                    # 컬럼명 전처리: 앞뒤 공백 제거 및 문자열 변환
                    df.columns = [str(c).strip() for c in df.columns]
                    
                    # 헤더 이름이 미세하게 다를 경우를 위한 유연한 매핑
                    rename_map = {
                        '이미지 URL': COL_IMG, '이미지주소': COL_IMG,
                        '현재 재고': COL_QTY, '수량': COL_QTY, '재고': COL_QTY
                    }
                    df = df.rename(columns=rename_map)

                    # 필수 컬럼 존재 확인 및 부족한 컬럼 생성
                    for col in REQUIRED_COLS:
                        if col not in df.columns:
                            df[col] = 0 if col == COL_QTY else ""
                    
                    # 수량 데이터 숫자형 변환
                    df[COL_QTY] = pd.to_numeric(df[COL_QTY], errors='coerce').fillna(0).astype(int)
                    
                    # 세션 상태 업데이트
                    st.session_state.inventory = df[REQUIRED_COLS].copy()
                    st.toast("✅ INPUT 데이터를 성공적으로 가져왔습니다!")
                    return True
        except Exception as e:
            st.error(f"불러오기 실패: {e}")
            st.info("""
            **💡 체크리스트:**
            1. 구글 시트 하단 탭 이름이 **INPUT** 인지 확인해 주세요.
            2. 시트 첫 줄에 **SKU, 상품명, 이미지URL, 현재재고, 최근수정일** 헤더가 있는지 확인해 주세요.
            """)
    return False

def commit_data():
    """현재 상태를 구글 시트의 OUTPUT 탭에 저장합니다."""
    conn = get_connection()
    if conn:
        try:
            with st.spinner("구글 시트(OUTPUT)에 저장 중..."):
                # 현재 인벤토리 데이터를 'OUTPUT' 워크시트에 덮어쓰기
                conn.update(worksheet="OUTPUT", data=st.session_state.inventory)
                st.success("🚀 OUTPUT 탭에 최종 결과가 저장되었습니다!")
                time.sleep(1)
                st.rerun()
        except Exception as e:
            st.error(f"저장 실패: {e}")
            st.info("💡 구글 시트에 **OUTPUT** 탭을 미리 만들어 두셨는지 확인해 주세요.")

# --- 메인 화면 ---
st.title("🍎 스마트 재고 동기화 시스템")
st.caption("구글 시트의 INPUT 탭을 읽어 수정하고, 그 결과를 OUTPUT 탭에 기록합니다.")

# 상단 제어판
with st.container():
    st.markdown('<div class="sync-box">', unsafe_allow_html=True)
    c1, c2, c3 = st.columns([2, 1, 1])
    with c1:
        st.subheader("🔄 실시간 동기화")
        is_ready = "connections" in st.secrets and "gsheets" in st.secrets.connections
        status_color = "#dcfce7" if is_ready else "#fee2e2"
        status_text = "● 클라우드 서버 연결됨" if is_ready else "● 설정 확인 필요"
        st.markdown(f'<span class="status-badge" style="background:{status_color};">{status_text}</span>', unsafe_allow_html=True)
    with c2:
        if st.button("📥 INPUT 불러오기", use_container_width=True):
            if fetch_data(): st.rerun()
    with c3:
        if st.button("💾 OUTPUT 저장", type="primary", use_container_width=True):
            commit_data()
    st.markdown('</div>', unsafe_allow_html=True)

# 탭 구성
tab_output, tab_input = st.tabs(["📊 재고 현황 (OUTPUT 관리)", "➕ 신규 품목 추가"])

with tab_input:
    st.subheader("📦 신규 품목 추가")
    st.info("여기서 추가한 상품은 상단의 'OUTPUT 저장' 시 시트에 반영됩니다.")
    with st.form("add_form", clear_on_submit=True):
        f_sku = st.text_input("SKU (상품 코드)")
        f_name = st.text_input("상품명")
        f_img = st.text_input("이미지URL", placeholder="예: https://cf.shopee.sg/file/...")
        f_qty = st.number_input("현재 수량", min_value=0, step=1)
        if st.form_submit_button("임시 리스트에 추가"):
            if f_sku and f_name:
                new_row = pd.DataFrame([[f_sku, f_name, f_img, int(f_qty), datetime.now().strftime("%Y-%m-%d")]], 
                                      columns=REQUIRED_COLS)
                st.session_state.inventory = pd.concat([st.session_state.inventory, new_row], ignore_index=True).drop_duplicates(COL_SKU, keep='last')
                st.success(f"'{f_name}'이 목록에 추가되었습니다. 저장 버튼을 눌러야 클라우드에 반영됩니다.")

with tab_output:
    search = st.text_input("🔍 품명 또는 SKU 검색", "")
    df = st.session_state.inventory
    
    # 검색 필터링
    if not df.empty:
        view_df = df[
            df[COL_NAME].astype(str).str.contains(search, case=False, na=False) |
            df[COL_SKU].astype(str).str.contains(search, case=False, na=False)
        ].reset_index(drop=True)
    else:
        view_df = pd.DataFrame()

    if view_df.empty:
        st.info("표시할 데이터가 없습니다. 먼저 [INPUT 불러오기]를 실행해 주세요.")
    else:
        # 지표 요약
        m1, m2 = st.columns(2)
        m1.metric("총 품목 수", f"{len(view_df)}개")
        m2.metric("전체 재고 합계", f"{int(view_df[COL_QTY].sum()):,}개")
        st.divider()

        for idx, row in view_df.iterrows():
            try:
                real_idx = st.session_state.inventory.index[st.session_state.inventory[COL_SKU] == row[COL_SKU]][0]
                with st.container():
                    # 이미지(1) : 정보(3) : 조절(2.5) 비율
                    c_img, c_info, c_qty = st.columns([1, 3, 2.5])
                    
                    with c_img:
                        url = row[COL_IMG]
                        # Shopee 이미지 서버 주소 및 일반 URL 렌더링 지원
                        final_url = url if pd.notna(url) and str(url).startswith('http') else "https://via.placeholder.com/150?text=No+Image"
                        st.image(final_url, width=110)
                    
                    with c_info:
                        st.subheader(row[COL_NAME])
                        st.caption(f"SKU: {row[COL_SKU]} | 업데이트: {row[COL_DATE]}")
                    
                    with c_qty:
                        st.write("") # 수직 정렬용 여백
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
            except Exception:
                continue
