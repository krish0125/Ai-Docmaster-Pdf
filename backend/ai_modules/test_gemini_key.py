import os
from dotenv import load_dotenv
from google import genai

load_dotenv('../../.env')

def test_key():
    api_key = os.environ.get('GEMINI_API_KEY')
    print(f'Testing with key: {api_key[:10]}...')
    client = genai.Client(api_key=api_key)
    try:
        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents='say hello',
        )
        print('SUCCESS! Response:', response.text)
    except Exception as e:
        print('FAILED:', str(e))

if __name__ == '__main__':
    test_key()
