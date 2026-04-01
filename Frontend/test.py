
# 本地测试一下deepseek是否正常

from openai import OpenAI

llm = OpenAI(
    api_key = "sk-ab43c52cb812447d8243b1966397936c",
    base_url = "https://api.deepseek.com/v1",
)

response = llm.chat.completions.create(
    model="deepseek-chat",
    messages=[
        {"role": "system", "content": "You are a helpful assistant."},
        {"role": "user", "content": "Hello, how are you?"},
    ],
)
print(response.choices[0].message.content)