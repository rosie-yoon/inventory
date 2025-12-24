import streamlit as st
import pandas as pd
from datetime import datetime
import time

# 구글 시트 연결 라이브러리 (배포 시 requirements.txt에 streamlit-gsheets 추가 필요)
try:
    from streamlit_gsheets import GSheetsConnection
except ImportError:
    GSheetsConnection = None

# 1. 페이지 설정 (사이드바 제거)
st.set_page_config(
    page_title="재고 관리 시스템", 
    layout="wide"
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
    /* 사이드바 숨기기 */
    [data-testid="stSidebar"] {
        display: none;
    }
    </style>
    """, unsafe_allow_html=True)

# --- 데이터 관리 로직 ---

# 세션 상태 초기화
if 'inventory' not in st.session_state:
    st.session_state.inventory = pd.DataFrame(columns=['SKU', '상품명', '이미지URL', '현재재고', '최근수정일'])

# 구글 시트 연결 여부 확인 함수 (개선됨)
def is_gsheets_configured():
    # 1. Top-level 'gsheets' 키 확인
    if "gsheets" in st.secrets:
        return True
    # 2. [connections.gsheets] 계층 구조 확인
    if "connections" in st.secrets and "gsheets" in st.secrets.connections:
        return True
    return False

# 구글 시트 연결 시도
def get_connection():
    if not GSheetsConnection:
        st.error("❌ 'streamlit-gsheets' 라이브러리가 설치되지 않았습니다.")
        return None
    
    if is_gsheets_configured():
        try:
            # 스트림릿 연결 시도
            return st.connection("gsheets", type=GSheetsConnection)
        except Exception as e:
            st.error(f"연결 생성 중 오류 발생: {e}")
            return None
    return None

# 데이터 불러오기 (Fetch)
def fetch_data():
    conn = get_connection()
    if conn:
        with st.spinner("구글 시트에서 데이터를 불러오는 중..."):
            try:
                # 연결 설정에서 URL을 찾지 못할 경우를 대비해 명시적 확인 가능
                df = conn.read(ttl="0") 
                if df is not None:
                    # 데이터 전처리 (빈 행 제거 및 컬럼 확인)
                    df = df.dropna(how='all')
                    st.session_state.inventory = df.copy()
                    st.toast("✅ 구글 시트에서 최신 데이터를 가져왔습니다!")
                    return True
            except Exception as e:
                st.error(f"데이터를 읽어오는 데 실패했습니다: {e}")
                st.info("💡 구글 시트가 '링크가 있는 모든 사용자에게 편집자' 권한으로 공유되어 있는지 확인해주세요.")
    else:
        st.error("❌ 구글 시트 연결 설정을 찾을 수 없습니다.")
        st.markdown("""
        **해결 방법:**
        1. 배포된 앱의 **Settings > Secrets**에 아래 내용을 붙여넣으세요:
        ```toml
        [connections.gsheets]
        spreadsheet = "사용자님의_구글시트_URL"
        ```
        2. `public_gsheets_url` 대신 `spreadsheet` 키를 사용해 보세요.
        """)
    return False

# 데이터 저장하기 (Commit)
def commit_data():
    conn = get_connection()
    if conn:
        with st.spinner("구글 시트에 저장 중..."):
            try:
                # 현재 인벤토리 데이터를 구글 시트에 업데이트
                conn.update(data=st.session_state.inventory)
                st.toast("🚀 모든 변경사항이 저장되었습니다!")
                st.success("동기화 완료!")
            except Exception as e:
                st.error(f"데이터 저장 실패: {e}")
                st.info("💡 구글 시트에 쓰기 권한이 필요합니다. '편집자' 권한 공유를 확인하세요.")
    else:
        st.error("❌ 연결 정보가 없어 저장할 수 없습니다.")

# --- 메인 화면 ---
st.title("🍎 스마트 재고 동기화 시스템")
st.caption("구글 시트를 기반으로 모든 기기의 재고를 통합 관리합니다.")

# 상단 동기화 제어판
with st.container():
    st.markdown('<div class="sync-box">', unsafe_allow_html=True)
    c_sync1, c_sync2, c_sync3 = st.columns([2, 1, 1])
    
    with c_sync1:
        st.subheader("🔄 실시간 데이터 동기화")
        if is_gsheets_configured():
            st.markdown('<span class="status-badge" style="background:#dcfce7; color:#166534;">● 클라우드 연결됨 (Google Sheets)</span>', unsafe_allow_html=True)
        else:
            st.markdown('<span class="status-badge" style="background:#fee2e2; color:#991b1b;">● 오프라인 모드 (설정 확인 필요)</span>', unsafe_allow_html=True)
    
    with c_sync2:
        if st.button("📥 시트 데이터 불러오기", use_container_width=True):
            if fetch_data():
                time.sleep(1)
                st.rerun()
            
    with c_sync3:
        if st.button("💾 변경사항 시트 저장", type="primary", use_container_width=True):
            commit_data()
    st.markdown('</div>', unsafe_allow_html=True)

# 탭 메뉴
tab_list, tab_add = st.tabs(["📊 재고 현황 및 관리", "➕ 신규 상품 등록"])

with tab_add:
    st.subheader("📦 신규 상품 추가")
    with st.form("add_form", clear_on_submit=True):
        col_f1, col_f2 = st.columns(2)
        new_sku = col_f1.text_input("SKU (상품 코드)")
        new_name = col_f2.text_input("상품명")
        new_img = st.text_input("이미지 URL")
        new_qty = st.number_input("현재 재고 수량", min_value=0, step=1)
        
        if st.form_submit_button("목록에 임시 추가"):
            if new_sku and new_name:
                new_row = pd.DataFrame([[new_sku, new_name, new_img, new_qty, datetime.now().strftime("%Y-%m-%d")]], 
                                      columns=['SKU', '상품명', '이미지URL', '현재재고', '최근수정일'])
                st.session_state.inventory = pd.concat([st.session_state.inventory, new_row], ignore_index=True).drop_duplicates('SKU', keep='last')
                st.success(f"'{new_name}'이 목록에 추가되었습니다. 상단의 [변경사항 시트 저장]을 눌러야 반영됩니다.")
            else:
                st.warning("SKU와 상품명은 필수 입력 사항입니다.")

with tab_list:
    search = st.text_input("🔍 검색 (명칭 또는 SKU)", "")
    
    view_df = st.session_state.inventory[
        st.session_state.inventory['상품명'].astype(str).str.contains(search, case=False, na=False) |
        st.session_state.inventory['SKU'].astype(str).str.contains(search, case=False, na=False)
    ].reset_index(drop=True)

    if view_df.empty:
        st.info("표시할 데이터가 없습니다. 상단의 [불러오기] 버튼을 누르거나 상품을 등록하세요.")
    else:
        m1, m2, m3 = st.columns(3)
        m1.metric("총 품목 수", f"{len(view_df)}개")
        m2.metric("전체 재고 합계", f"{int(view_df['현재재고'].sum()):,}개")
        m3.metric("재고 부족 알림", f"{len(view_df[view_df['현재재고'] < 5])}건", delta_color="inverse")
        
        st.divider()

        for idx, row in view_df.iterrows():
            real_idx = st.session_state.inventory.index[st.session_state.inventory['SKU'] == row['SKU']][0]
            with st.container():
                c_img, c_info, c_qty, c_btn = st.columns([1, 3, 2, 1])
                with c_img:
                    img_url = row['이미지URL'] if pd.notna(row['이미지URL']) and row['이미지URL'] != "" else "https://via.placeholder.com/100?text=No+Image"
                    st.image(img_url, width=100)
                with c_info:
                    st.subheader(row['상품명'])
                    st.caption(f"SKU: {row['SKU']} | 수정일: {row['최근수정일']}")
                with c_qty:
                    st.markdown(f"### {int(row['현재재고'])} 개")
                    sub_c1, sub_c2 = st.columns(2)
                    if sub_c1.button("➕", key=f"up_{row['SKU']}"):
                        st.session_state.inventory.at[real_idx, '현재재고'] += 1
                        st.session_state.inventory.at[real_idx, '최근수정일'] = datetime.now().strftime("%Y-%m-%d")
                        st.rerun()
                    if sub_c2.button("➖", key=f"down_{row['SKU']}"):
                        if row['현재재고'] > 0:
                            st.session_state.inventory.at[real_idx, '현재재고'] -= 1
                            st.session_state.inventory.at[real_idx, '최근수정일'] = datetime.now().strftime("%Y-%m-%d")
                            st.rerun()
                with c_btn:
                    st.write("")
                    if st.button("🗑️ 삭제", key=f"del_{row['SKU']}"):
                        st.session_state.inventory = st.session_state.inventory.drop(real_idx)
                        st.rerun()
                st.divider()

    if not st.session_state.inventory.empty:
        st.write("---")
        csv_data = st.session_state.inventory.to_csv(index=False).encode('utf-8-sig')
        st.download_button("현재 목록 CSV 다운로드", data=csv_data, file_name=f"inventory_backup.csv", mime="text/csv")
