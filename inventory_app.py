import streamlit as st
import pandas as pd
from datetime import datetime
import time

# 구글 시트 연결 라이브러리 (배포 시 requirements.txt에 st-gsheets-connection 추가 필요)
try:
    from streamlit_gsheets import GSheetsConnection
except ImportError:
    GSheetsConnection = None

# 1. 페이지 설정 (사이드바 제거 및 레이아웃 설정)
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
    /* 사이드바 및 관련 UI 강제 숨기기 */
    [data-testid="stSidebar"], [data-testid="stSidebarNav"] {
        display: none;
    }
    section[data-testid="stSidebar"] {
        width: 0px !important;
    }
    </style>
    """, unsafe_allow_html=True)

# --- 데이터 관리 로직 ---

# 세션 상태 초기화
if 'inventory' not in st.session_state:
    st.session_state.inventory = pd.DataFrame(columns=['SKU', '상품명', '이미지URL', '현재재고', '최근수정일'])

# 구글 시트 연결 설정 확인
def get_gsheets_config():
    """Secrets에서 설정값 확인 및 반환"""
    # 1. [connections.gsheets] 구조 확인
    if "connections" in st.secrets and "gsheets" in st.secrets.connections:
        return st.secrets.connections.gsheets
    # 2. 최상위 gsheets 확인
    if "gsheets" in st.secrets:
        return st.secrets.gsheets
    return None

def is_gsheets_configured():
    config = get_gsheets_config()
    if config:
        # st-gsheets-connection 라이브러리가 인식하는 주요 키값들 확인
        return "public_gsheets_url" in config or "spreadsheet" in config or "url" in config
    return False

# 구글 시트 연결 시도
def get_connection():
    if not GSheetsConnection:
        return None
    
    if is_gsheets_configured():
        try:
            # 팁: st.connection은 기본적으로 [connections.gsheets] 섹션을 찾습니다.
            return st.connection("gsheets", type=GSheetsConnection)
        except Exception as e:
            st.error(f"연결 시도 중 오류 발생: {e}")
            return None
    return None

# 데이터 불러오기 (Fetch)
def fetch_data():
    conn = get_connection()
    if conn:
        try:
            with st.spinner("구글 시트에서 최신 데이터를 가져오는 중..."):
                # 최신 라이브러리에서는 read()가 시트의 내용을 바로 가져옵니다.
                df = conn.read(ttl=0) 
                if df is not None:
                    df = df.dropna(how='all')
                    
                    # --- 컬럼명 표준화 (KeyError 방지) ---
                    rename_map = {
                        '이미지 URL': '이미지URL',
                        '이미지 주소': '이미지URL',
                        '초기 수량': '현재재고',
                        '수량': '현재재고',
                        '수정일': '최근수정일'
                    }
                    df = df.rename(columns=rename_map)
                    
                    # 필수 컬럼 존재 확인 및 수치 보정
                    required_cols = ['SKU', '상품명', '이미지URL', '현재재고', '최근수정일']
                    for col in required_cols:
                        if col not in df.columns:
                            df[col] = 0 if col == '현재재고' else ""
                    
                    if '현재재고' in df.columns:
                        df['현재재고'] = pd.to_numeric(df['현재재고'], errors='coerce').fillna(0).astype(int)
                    
                    st.session_state.inventory = df[required_cols].copy()
                    st.toast("✅ 동기화 완료!")
                    return True
                else:
                    st.warning("시트에 읽어올 데이터가 없습니다.")
        except Exception as e:
            st.error(f"데이터 읽기 실패: {e}")
            st.info("💡 구글 시트의 공유 설정이 '편집자' 권한으로 되어 있는지 다시 확인해주세요.")
    else:
        if not GSheetsConnection:
            st.error("❌ 라이브러리 설치 오류: requirements.txt에 'st-gsheets-connection'을 추가해야 합니다.")
        else:
            st.error("❌ 설정 오류: 구글 시트 주소를 찾을 수 없습니다. (Secrets 설정을 확인하세요)")
    return False

# 데이터 저장하기 (Commit)
def commit_data():
    conn = get_connection()
    if conn:
        try:
            with st.spinner("클라우드에 저장 중..."):
                # 데이터 업데이트
                conn.update(data=st.session_state.inventory)
                st.success("🚀 구글 시트 저장이 완료되었습니다!")
        except Exception as e:
            st.error(f"저장 실패: {e}")
    else:
        st.error("❌ 저장 불가: 연결 설정이 되어 있지 않습니다.")

# --- 메인 화면 ---
st.title("🍎 스마트 재고 동기화 시스템")
st.caption("맥북과 아이폰에서 실시간으로 공유되는 클라우드 재고 관리")

# 상단 제어판
with st.container():
    st.markdown('<div class="sync-box">', unsafe_allow_html=True)
    c_sync1, c_sync2, c_sync3 = st.columns([2, 1, 1])
    
    with c_sync1:
        st.subheader("🔄 데이터 동기화 제어")
        if is_gsheets_configured() and GSheetsConnection:
            st.markdown('<span class="status-badge" style="background:#dcfce7; color:#166534;">● 클라우드 서버 연결됨</span>', unsafe_allow_html=True)
        else:
            st.markdown('<span class="status-badge" style="background:#fee2e2; color:#991b1b;">● 로컬 모드 (연결 설정 필요)</span>', unsafe_allow_html=True)
    
    with c_sync2:
        if st.button("📥 시트에서 불러오기", use_container_width=True):
            if fetch_data():
                time.sleep(0.5)
                st.rerun()
            
    with c_sync3:
        if st.button("💾 시트에 최종 저장", type="primary", use_container_width=True):
            commit_data()
    st.markdown('</div>', unsafe_allow_html=True)

# 메인 탭
tab_list, tab_add = st.tabs(["📊 재고 현황 및 관리", "➕ 신규 상품 등록"])

with tab_add:
    st.subheader("📦 신규 품목 추가")
    with st.form("add_form", clear_on_submit=True):
        col_f1, col_f2 = st.columns(2)
        new_sku = col_f1.text_input("SKU (코드)")
        new_name = col_f2.text_input("상품명")
        new_img = st.text_input("이미지 URL")
        new_qty = st.number_input("현재 재고 수량", min_value=0, step=1)
        
        if st.form_submit_button("목록에 임시 추가"):
            if new_sku and new_name:
                new_row = pd.DataFrame([[new_sku, new_name, new_img, int(new_qty), datetime.now().strftime("%Y-%m-%d")]], 
                                      columns=['SKU', '상품명', '이미지URL', '현재재고', '최근수정일'])
                st.session_state.inventory = pd.concat([st.session_state.inventory, new_row], ignore_index=True).drop_duplicates('SKU', keep='last')
                st.success(f"'{new_name}' 추가됨. 저장 버튼을 눌러야 클라우드에 반영됩니다.")
            else:
                st.warning("SKU와 상품명은 필수입니다.")

with tab_list:
    search = st.text_input("🔍 검색창", "")
    view_df = st.session_state.inventory[
        st.session_state.inventory['상품명'].astype(str).str.contains(search, case=False, na=False) |
        st.session_state.inventory['SKU'].astype(str).str.contains(search, case=False, na=False)
    ].reset_index(drop=True)

    if view_df.empty:
        st.info("데이터가 없습니다. 불러오기 버튼을 누르거나 상품을 등록하세요.")
    else:
        m1, m2, m3 = st.columns(3)
        m1.metric("총 품목", f"{len(view_df)}개")
        m2.metric("총 수량", f"{int(view_df['현재재고'].sum()):,}개")
        m3.metric("재고 부족", f"{len(view_df[view_df['현재재고'] < 5])}건")
        
        st.divider()

        for idx, row in view_df.iterrows():
            real_idx = st.session_state.inventory.index[st.session_state.inventory['SKU'] == row['SKU']][0]
            with st.container():
                c_img, c_info, c_qty, c_btn = st.columns([1, 3, 2, 1])
                with c_img:
                    # 이미지URL 컬럼 안전하게 접근
                    img_url = row['이미지URL'] if pd.notna(row['이미지URL']) and row['이미지URL'] != "" else "https://via.placeholder.com/100?text=No+Image"
                    st.image(img_url, width=100)
                with c_info:
                    st.subheader(row['상품명'])
                    st.caption(f"SKU: {row['SKU']} | 수정일: {row['최근수정일']}")
                with c_qty:
                    st.markdown(f"### {int(row['현재재고'])} 개")
                    sc1, sc2 = st.columns(2)
                    if sc1.button("➕", key=f"up_{row['SKU']}"):
                        st.session_state.inventory.at[real_idx, '현재재고'] += 1
                        st.rerun()
                    if sc2.button("➖", key=f"down_{row['SKU']}"):
                        if row['현재재고'] > 0:
                            st.session_state.inventory.at[real_idx, '현재재고'] -= 1
                            st.rerun()
                with c_btn:
                    if st.button("🗑️", key=f"del_{row['SKU']}"):
                        st.session_state.inventory = st.session_state.inventory.drop(real_idx)
                        st.rerun()
                st.divider()
