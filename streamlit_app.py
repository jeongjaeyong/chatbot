import streamlit as st
from openai import OpenAI
import pandas as pd
import os
from supabase import create_client
from datetime import datetime
import json
import copy
# CSV에서 데이터 로드

first_prompt = """
너는 유저의 질문을 분석하는 AI야! 유저의 질문을 바탕으로 주어진 조건에 맞도록 질문을 분석해줘!

조건 1. 아래 Task 리스트 중 1개의 작업 선택!
Task : ["ReAsk", "FindProduct", "Recommandation", "Etc"]
조건 2. 만약, Task가 "FindProduct"라면, 원하는 "Product"를 "Option"으로 정의를 해줘!
조건 3. 만약, Task가 "Recommandation"라면, 유저의 조건을 "Condition"이라고 "Option"에 제공해줘!
조건 4. 만약, Task가 "ReAsk"라면, 유저의 질문에서 추가적으로 요구되는 조건을 "Condition"이라고 "Option"에 제공해줘!
** 조건 5. 화장품 관련 이야기를 제외한 다른 이야기는 답할 수 없다는 내용으로 답변을 해줘! **

OUTPUT 포맷
```json
{
    "Task":"...",
    "Option":{"...":"...",  ..., key:val}
}
```
"""


# Supabase 설정
supabase_url = os.getenv("SUPABASE_URL")
supabase_key = os.getenv("SUPABASE_KEY")
supabase = create_client(supabase_url, supabase_key)

# Supabase 로깅 함수
def log_to_supabase(question, answer, history):
    try:
        timestamp = datetime.now().isoformat()
        supabase.table("chat_log").insert({
            "question": question,
            "answer": answer,
            "history": json.dumps(history, ensure_ascii=False),
            "timestamp": timestamp
        }).execute()
    except:
        pass
def local_RAG(model, messages, client, vector_id):
    response = client.responses.create(
        model=model,
        input=messages[-1]['content'],
        tools=[{
                "type": "file_search",
                "vector_store_ids": [vector_id],
                "max_num_results": 5
        }]
        )
    if response.output[0].results == None:
        return ""
    return response.output[1].content[0].text

def generate(model, messages, client):
    response = client.chat.completions.create(
        model=model,
        messages=messages,
    )
    return response.choices[0].message.content

def routing(prompt, user_input, client):
    messages = [
        {"role": "system", "content": prompt},
        {"role": "user", "content": user_input}
    ]

    response = client.chat.completions.create(
        model="gpt-4o",
        messages=messages,
        response_format={"type": "json_object"}
    )
    query_parsing = json.loads(response.choices[0].message.content)
    return query_parsing

def generate_response(query_parsing, client, vector_id, messages):
    response = ""
    if "Task" not in query_parsing.keys():
        response = "죄송합니다. 원하시는 내용을 제대로 이해하지 못했어요. 조금 더 구체적으로 알려주시면 감사하겠습니다."

    if query_parsing["Task"] == "ReAsk":
        response = "관심 있는 제품에 대해서 자세히(ex. 이름, 브랜드, 메이커) 알려주세요. 또는 원하시는 조건에 대해서 자세히(ex. 건성 피부용) 알려주세요"


    if query_parsing["Task"] == "FindProduct":
        if "Option" not in query_parsing.keys():
            response = "죄송합니다. 원하시는 내용을 찾지 못했어요. 찾으시는 제품에 대해서서 명확하게 다시 알려주세요"

        product = query_parsing['Option']["Product"]
        product_list = supabase.table("cosmetics").select("*").execute().data

        find_data = ""
        for item in product_list:
            if product in item["title"]:
                find_data += f"item : {item['title']}\tbrand : {item['brand']}\tmake : {item['maker']}\tsummary : {item['summary']}\n\n"

        messages[0]['content'] = response_prompt

        if len(find_data)>2:
            messages[-1]['content'] = messages[-1]['content'] +"\n\n<데이터>\n\n" + find_data +"\n\n</데이터>\n\n" + messages[-1]['content']
            response = generate("gpt-4o", messages, client)

        else:
            if "brand" in query_parsing['Option'].keys() or "maker" in query_parsing['Option'].keys():
                response = local_RAG("gpt-4o", messages, client, vector_id)
                if response == "":
                    response = generate("gpt-4o-search-preview", messages, client)
            else:
                response = generate("gpt-4o-search-preview", messages, client)

    if query_parsing["Task"] == "Recommandation":
        response = local_RAG("gpt-4o", messages, client, vector_id)
        if response == "":
            response = generate("gpt-4o-search-preview", messages, client)

    return response
# CSV 데이터를 프롬프트에 맞는 문자열로 변환하는 함수


# Show title and description.
st.title("💬 Chatbot")

# Select language
language = st.selectbox("Choose your language:", ["English", "한국어", "Español", "中文", "日本語", "ภาษาไทย", "Tiếng Việt", "Bahasa Indonesia"])

response_prompt = f"""
너는 화장품을 상담해 주는 AI야!
유저의 화장품 관련된 질문에 가장 적절한 답변을 해줘!

조건1 : 화장품과 관련되지 않은 질문에 대해서 대답을 하지 않도록 해줘
조건2 : 주어진 language에 맞는 언어로 답변을 해줘!
조건3 : 유저가 별도의 데이터를 제공하면(<데이터>...</데이터>로 제공), 제공된 데이터에서만 답변 해줘

language:{language}
"""

# Ask user for their OpenAI API key.
openai_api_key = os.getenv("OPENAI_API_KEY")
vector_id = os.getenv("vector_id")

if not openai_api_key:
    st.info("Please add your OpenAI API key to continue.", icon="🗝️")
else:
    client = OpenAI(api_key=openai_api_key)

    if "messages" not in st.session_state:
        st.session_state.messages = [{"role": "system", "content": response_prompt}]

    # 언어 또는 데이터 변경 시 시스템 프롬프트 업데이트
    if st.session_state.messages[0]["content"] != system_prompt:
        st.session_state.messages = [{"role": "system", "content": response_prompt}]

    # Display existing chat messages.
    for message in st.session_state.messages[1:]:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    # Chat input field
    if user_prompt := st.chat_input("Enter your message:"):
        st.session_state.messages.append({"role": "user", "content": user_prompt})
        with st.chat_message("user"):
            st.markdown(prompt)
        query_parsing = routing(first_prompt, user_prompt, client)
        response = generate_response(query_parsing, client, vector_id, copy.deepcopy(messages))

        
        with st.chat_message("assistant"):
            response = st.markdown(stream)
        st.session_state.messages.append({"role": "assistant", "content": response})

        # Supabase 로깅 실행
        log_to_supabase(prompt, response, st.session_state.messages)
