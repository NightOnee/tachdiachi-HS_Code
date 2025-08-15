import streamlit as st
import pandas as pd
import json
import re
import random
import google.generativeai as genai

# ==============================================================================
# PHẦN BACK-END: GỌI API CỦA GOOGLE GEMINI
# ==============================================================================

def call_gemini_api(prompt_template, user_input):
    """
    Hàm gọi API của Google Gemini và xử lý kết quả trả về.
    """
    try:
        # B1: Lấy tất cả các API key có trong file secrets và chọn ngẫu nhiên một key
        # Các key trong file secrets.toml phải có dạng GEMINI_API_KEY_1, GEMINI_API_KEY_2, ...
        api_keys = [value for key, value in st.secrets.items() if key.startswith("GEMINI_API_KEY_")]
        
        if not api_keys:
            st.error("Không tìm thấy API key nào có định dạng 'GEMINI_API_KEY_...' trong file secrets.toml.")
            return {"error": "Lỗi cấu hình API Key."}
            
        selected_api_key = random.choice(api_keys)
        genai.configure(api_key=selected_api_key)


        # B2: Khởi tạo mô hình
        # Sử dụng Gemma 3 27B cho các tác vụ xử lý văn bản phức tạp
        model = genai.GenerativeModel('gemma-3-27b-it')

        # B3: Tạo prompt hoàn chỉnh
        full_prompt = prompt_template.format(user_input=user_input)

        # B4: Gửi yêu cầu đến Gemini
        response = model.generate_content(full_prompt)
        
        # B5: Xử lý và bóc tách JSON từ kết quả trả về
        # Gemini thường trả về JSON trong một khối mã markdown, cần phải bóc tách nó ra.
        response_text = response.text
        
        # Cố gắng tìm khối JSON được bao bọc bởi ```json ... ```
        match = re.search(r"```json\n(.*?)\n```", response_text, re.DOTALL)
        if match:
            json_str = match.group(1)
        else:
            # Nếu không tìm thấy, giả định toàn bộ văn bản là một chuỗi JSON
            json_str = response_text

        # Chuyển chuỗi JSON thành đối tượng Python
        return json.loads(json_str)

    except Exception as e:
        # Bắt các lỗi có thể xảy ra (API key sai, lỗi mạng, v.v.)
        st.error(f"Đã xảy ra lỗi khi gọi API của Gemini: {e}")
        return {"error": str(e)}


# ==============================================================================
# GIAO DIỆN NGƯỜI DÙNG (FRONT-END SỬ DỤNG STREAMLIT)
# ==============================================================================

st.set_page_config(page_title="Trợ lý Xử lý Thông tin Xuất khẩu", layout="wide")

st.title("🚀 Trợ lý Xử lý Thông tin Xuất khẩu (với Gemini AI)")
st.markdown("Ứng dụng này hỗ trợ hai tác vụ: **chuẩn hóa địa chỉ quốc tế** và **hoàn thiện thông tin hàng hóa xuất khẩu**.")

# --- B1: NGƯỜI DÙNG CHỌN VẤN ĐỀ VÀ ĐIỀN YÊU CẦU ---
st.sidebar.title("Chọn chức năng")
app_mode = st.sidebar.selectbox(
    "Vui lòng chọn tác vụ bạn muốn thực hiện:",
    ["--Chọn--", "1. Chuẩn hóa Địa chỉ", "2. Hoàn thiện Thông tin Hàng hóa"]
)

# --- Xử lý chức năng 1: Chuẩn hóa Địa chỉ ---
if app_mode == "1. Chuẩn hóa Địa chỉ":
    st.header("1. Chuẩn hóa Địa chỉ Quốc tế")
    st.info("Dán địa chỉ đầy đủ vào ô bên dưới. Hệ thống sẽ tự động bóc tách, đối chiếu và trả về thông tin đã được chuẩn hóa.")

    address_input = st.text_area(
        "Nhập địa chỉ đầy đủ:",
        height=100,
        placeholder="Ví dụ: 221 - 310 STILLWATER DR SASKATOON SK S7J 4H7 CANADA"
    )

    if st.button("Xử lý Địa chỉ"):
        if address_input:
            with st.spinner("Hệ thống đang phân tích và xác thực địa chỉ..."):
                # Prompt được thiết kế để hướng dẫn LLM phân tích địa chỉ
                address_prompt = """
                You are an expert address parser. Your task is to parse the raw address string into specific fields: Country, UPU Code, Postal Code, City, and State/Province. Then, verify the information for accuracy using your knowledge.
                Present the final, verified result as a single JSON object. The JSON keys must be: "country", "country_code_upu", "postal_code", "city", "state".

                Input address: '{user_input}'
                """
                response_data = call_gemini_api(address_prompt, address_input)

                st.subheader("Kết quả phân tích địa chỉ:")
                if "error" not in response_data:
                    st.success("Phân tích thành công!")
                    col1, col2 = st.columns(2)
                    col1.markdown(f"**Quốc gia:** `{response_data.get('country', 'N/A')}`")
                    col1.markdown(f"**Tên viết tắt (UPU):** `{response_data.get('country_code_upu', 'N/A')}`")
                    col1.markdown(f"**Mã bưu chính:** `{response_data.get('postal_code', 'N/A')}`")
                    col2.markdown(f"**Thành phố:** `{response_data.get('city', 'N/A')}`")
                    col2.markdown(f"**Bang/Tỉnh:** `{response_data.get('state', 'N/A')}`")
                # Không cần hiển thị lỗi ở đây vì hàm call_gemini_api đã dùng st.error
        else:
            st.warning("Vui lòng nhập một địa chỉ để xử lý.")


# --- Xử lý chức năng 2: Hoàn thiện Thông tin Hàng hóa ---
elif app_mode == "2. Hoàn thiện Thông tin Hàng hóa":
    st.header("2. Hoàn thiện Thông tin Hàng hóa Xuất khẩu")
    st.info("Dán danh sách hàng hóa vào ô bên dưới. Hệ thống sẽ tìm kiếm và bổ sung các thông tin cần thiết cho nội dung hàng hoá như: **Tên Tiếng Anh của sản phẩm**, **HS Code**")

    products_input = st.text_area(
        "Nhập danh sách hàng hoá (mỗi hàng một dòng):",
        height=150,
        placeholder="Ví dụ:\nHẠT SEN SL:4 Bịch 1kg/bịch\nHÀNH TĂM SL:2 Bịch 1.5kg/bịch"
    )

    if st.button("Tìm kiếm thông tin tương ứng"):
        if products_input:
            with st.spinner("Hệ thống đang tìm kiếm và tổng hợp thông tin hàng hóa..."):
                # Prompt được thiết kế để yêu cầu LLM điền vào các trường thông tin cụ thể
                products_prompt = """
                You are an expert in international trade and customs data. For each product in the user's list, enrich it with details for export documents.
                Return a JSON list of objects. Each object must contain these exact keys: "TÊN HÀNG TIẾNG ANH", "TÊN HÀNG TIẾNG VIỆT", "NHÀ SẢN XUẤT (TIẾNG ANH)", "NƯỚC SẢN XUẤT", "HS CODE", "SỐ LƯỢNG", "QUY CÁCH SẢN PHẨM", "QUY CÁCH ĐÓNG GÓI".
                - HS CODE must be the most suitable 8 digit code, if not found try 6 digit code.
                - Assume 'NƯỚC SẢN XUẤT' is 'Vietnam'.
                - 'NHÀ SẢN XUẤT (TIẾNG ANH)' should be a plausible, fictional Vietnamese company name.
                - Extract quantity and packaging information from the user input.

                User's product list:
                {user_input}
                """
                response_data = call_gemini_api(products_prompt, products_input)

                st.subheader("Bảng thông tin hàng hóa chi tiết:")
                if "error" not in response_data and isinstance(response_data, list):
                    st.success("Hoàn thiện thông tin thành công!")
                    df = pd.DataFrame(response_data)
                    column_order = [
                        "TÊN HÀNG TIẾNG ANH", "TÊN HÀNG TIẾNG VIỆT",
                        "NHÀ SẢN XUẤT (TIẾNG ANH)", "NƯỚC SẢN XUẤT", "HS CODE",
                        "SỐ LƯỢNG", "QUY CÁCH SẢN PHẨM", "QUY CÁCH ĐÓNG GÓI"
                    ]
                    # Đảm bảo tất cả các cột đều tồn tại trước khi sắp xếp
                    df_cols = [col for col in column_order if col in df.columns]
                    df = df[df_cols]
                    df.insert(0, 'STT', range(1, 1 + len(df)))
                    st.dataframe(df, use_container_width=True)
                # Không cần hiển thị lỗi ở đây vì hàm call_gemini_api đã dùng st.error
        else:
            st.warning("Vui lòng nhập danh sách hàng hóa để xử lý.")

elif app_mode == "--Chọn--":
    st.markdown("### Vui lòng chọn một chức năng từ thanh công cụ bên trái để bắt đầu.")

