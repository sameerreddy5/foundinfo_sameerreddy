import os
import requests
from dotenv import load_dotenv

load_dotenv()

API_TOKEN = os.getenv("LEAKOSINT_API_TOKEN")
API_URL = os.getenv("LEAKOSINT_URL")

def test_api(query):
    print(f"\n--- Testing Query: {query} ---")
    data = {
        "token": API_TOKEN,
        "request": query,
        "limit": 100,
        "lang": "en"
    }
    
    try:
        response = requests.post(API_URL, json=data, timeout=10)
        print(f"Status Code: {response.status_code}")
        if response.status_code == 200:
            result = response.json()
            print(f"Full Result: {result}")
            if "Error code" in result:
                print(f"API Error Code: {result['Error code']}")
            else:
                print("No API error codes found.")
        else:
            print(f"Error: {response.text}")
    except Exception as e:
        print(f"Exception occurred: {e}")

if __name__ == "__main__":
    queries = ["vaibhavsharma0506", "vaibhavsharma0605", "test"]
    for q in queries:
        test_api(q)
