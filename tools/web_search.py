import requests
import urllib.parse
from ddgs import DDGS

JINA_API_KEY = ""

def perform_web_search_jina(query):
    print(f"\n[WEB SEARCH] Querying Jina AI for: '{query}'...")
    
    encoded_query = urllib.parse.quote(query)
    url = f"https://s.jina.ai/{encoded_query}"
    
    headers = {
        "Authorization": f"Bearer {JINA_API_KEY}",
        "Accept": "application/json" 
    }
    
    try:
        response = requests.get(url, headers=headers, timeout=15)
        
        if response.status_code == 200:
            data = response.json()
            results = data.get("data", [])[:3] 
            
            if not results:
                return "No relevant information found on the web."
                
            formatted_result = f"--- WEB SEARCH RESULTS FOR '{query}' ---\n\n"
            for item in results:
                title = item.get('title', 'No Title')
                content = item.get('content') or item.get('description', '')
                formatted_result += f"### {title}\n{content}\n\n"
                
            return formatted_result.strip()
            
        else:
            return f"Search failed. API returned status code: {response.status_code}"
            
    except requests.exceptions.Timeout:
        return "Web search timed out."
    except Exception as e:
        return f"Web search encountered an error: {str(e)}"

def perform_web_search_ddgs(query):
    print(f"\n[WEB SEARCH] Querying DuckDuckGo for: '{query}'...")
    
    try:
        # Lấy top 3 kết quả từ DuckDuckGo
        results = DDGS().text(query, max_results=3)
        
        if not results:
            return "No relevant information found on the web."
            
        formatted_result = f"--- WEB SEARCH RESULTS FOR '{query}' ---\n\n"
        
        for item in results:
            title = item.get('title', 'No Title')
            body = item.get('body', '')
            formatted_result += f"### {title}\n{body}\n\n"
            
        return formatted_result.strip()
        
    except Exception as e:
        return f"Web search encountered an error: {str(e)}"

if __name__ == "__main__":
    test_query = "current CEO of NVIDIA ?"
    print(perform_web_search_ddgs(test_query))

