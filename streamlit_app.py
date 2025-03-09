import streamlit as st
from openai import OpenAI
import pandas as pd
import os
from supabase import create_client
import json
# CSV에서 데이터 로드
data = pd.read_csv("data.csv")

# Supabase 설정
supabase_url = os.getenv("SUPABASE_URL")
supabase_key = os.getenv("SUPABASE_KEY")
supabase = create_client(supabase_url, supabase_key)

# Supabase 로깅 함수
def log_to_supabase(question, answer, history):
    # JSON 직렬화 명시적 수행
    history_json = json.dumps(history, ensure_ascii=False)
    supabase.table("chat_logs").insert({
        "question": question,
        "answer": answer,
        "history": history_json
    }).execute()

# CSV 데이터를 프롬프트에 맞는 문자열로 변환하는 함수
def create_product_list(dataframe):
    products_info = "제품 리스트:\n"
    for idx, row in dataframe.iterrows():
        products_info += f"제품:{row['제품']}\n기능:{row['기능']}\n비고:{row.get('비고', '정보 없음')}\n링크:{row.get('링크', '정보 없음')}\n\n\n"
    return products_info

# Show title and description.
st.title("💬 Chatbot")

# Select language
language = st.selectbox("Choose your language:", ["English", "한국어", "Español", "中文", "日本語", "ภาษาไทย", "Tiếng Việt", "Bahasa Indonesia"])

# 제품 리스트를 시스템 프롬프트에 추가
product_list_str = create_product_list(data)

system_prompt = f"""You are an AI that recommends good products to users. 
The product information you have is provided in Korean, but please answer in the given language.
Recommend the appropriate product that fits the user's situation.
Explain in detail the reason for the recommendation and provide a link to purchase if available.

{product_list_str}

답변 언어 : {language}
"""

# Ask user for their OpenAI API key.
openai_api_key = os.getenv("OPENAI_API_KEY")
if not openai_api_key:
    st.info("Please add your OpenAI API key to continue.", icon="🗝️")
else:
    client = OpenAI(api_key=openai_api_key)

    if "messages" not in st.session_state:
        st.session_state.messages = [{"role": "system", "content": system_prompt}]

    # 언어 또는 데이터 변경 시 시스템 프롬프트 업데이트
    if st.session_state.messages[0]["content"] != system_prompt:
        st.session_state.messages = [{"role": "system", "content": system_prompt}]

    # Display existing chat messages.
    for message in st.session_state.messages[1:]:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    # Chat input field
    if prompt := st.chat_input("Enter your message:"):
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        stream = client.chat.completions.create(
            model="gpt-4o-2024-08-06",
            messages=st.session_state.messages,
            stream=True,
        )

        with st.chat_message("assistant"):
            response = st.write_stream(stream)
        st.session_state.messages.append({"role": "assistant", "content": response})

        # Supabase 로깅 실행
        log_to_supabase(prompt, response, st.session_state.messages)
