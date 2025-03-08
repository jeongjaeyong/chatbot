import streamlit as st
from openai import OpenAI
import os

# Show title and description.
st.title("💬 Chatbot")


# Select language
language = st.selectbox("Choose your language:", ["English", "한국어", "Español", "中文", "日本語", "ภาษาไทย", "Tiếng Việt", "Bahasa Indonesia"])

system_prompt = f"""You are an AI that recommends good products to users. 
The product information you have is provided in Korean, but please answer in the given language. 
And recommend the appropriate product that fits the user's situation.


제품 리스트 :
Title    / detail    /price
올인원 스킨    / 귀찮음이 많은 남자를 위한 제품    / 20,000 (Korean won)
촉촉 스킨    / 건조한 피부를 위한 보습 스킨    / 30,000 (Korean won)
상쾌 스킨    / 지성 피부를 위한 스킨    / 10,000 (Korean won)
베이비 스킨    / 예민한 피부를 위한 보습 스킨    / 40,000 (Korean won)


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
    
    # 언어가 변경되었을 때 시스템 프롬프트 업데이트
    if st.session_state.messages[0]["content"] != system_prompt:
        st.session_state.messages = [{"role": "system", "content": system_prompt}]
    
    # Display the existing chat messages.
    for message in st.session_state.messages[1:]:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    # Chat input field
    if prompt := st.chat_input("Enter your message:"):
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        stream = client.chat.completions.create(
            model="gpt-4-o",
            messages=st.session_state.messages,
            stream=True,
        )

        with st.chat_message("assistant"):
            response = st.write_stream(stream)
        st.session_state.messages.append({"role": "assistant", "content": response})
